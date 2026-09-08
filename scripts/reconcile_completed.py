#!/usr/bin/env python3
"""Owner-only reconciliation of an already-reviewed, merged and live publication.

This is not a supervised attempt, a new release, a quota reset or orphan cleanup.
It preserves the full old checkpoint and SQLite backup, then clears only the
completed pending item. Routine leads must not invoke this operator command.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sqlite3

from autonomy import ROOT, deployed, merged_receipt, state_dir
from autonomy_cleanup import owned_worktree_root
from autonomy_policy import REPO, item_id, sha40
from autonomy_release import GitHub, command, quality_green
from autonomy_runtime import run_lock, unresolved_guard
from autonomy_state import Blocked, Store


def verify_browser(root, sha, lesson):
    return json.loads(command(['node', str(root / 'scripts/verify-live.mjs'), sha, lesson], root, timeout=120))


def reconcile_completed(root, intent, *, api=None, verify=None):
    """Caller explicitly authorizes the exact existing publication, never new work."""
    if os.environ.get('LWL_ATTEMPT'):
        raise Blocked('operator reconciliation is forbidden inside a supervised attempt')
    item = item_id(intent['item'])
    number = intent['pr']
    if type(number) is not int or number < 1 or not isinstance(intent.get('authorization'), str) or not intent['authorization'].strip():
        raise Blocked('exact PR and explicit owner authorization required')
    for key in ('sha', 'base', 'merge_sha'):
        sha40(intent[key])
    location = state_dir(root)
    with run_lock(location / 'run.lock'):
        if unresolved_guard(location):
            raise Blocked('reconcile prior processes before completed-publication bookkeeping')
        store = Store(location / 'state.sqlite3')
        try:
            if store.db.execute("SELECT 1 FROM attempts WHERE status='running'").fetchone():
                raise Blocked('active attempt must finish before operator reconciliation')
            old = store.pending()
            if (old.get('item') != item or old.get('branch') != 'auto/' + item or
                    not intent.get('lesson_id') or old.get('lesson_id') != intent['lesson_id'] or
                    old.get('pr', number) != number or
                    any(key in old and old[key] != intent[key] for key in ('sha', 'base', 'merge_sha'))):
                raise Blocked('intent does not match the pending item, branch, lesson or PR')
            target = owned_worktree_root(root) / item
            def check_worktree():
                if (old.get('worktree') != str(target) or target.resolve() != target or
                        not target.is_dir() or
                        state_dir(target) != location or
                        command(['git', 'branch', '--show-current'], target) != 'auto/' + item or
                        command(['git', 'rev-parse', 'HEAD'], target) != intent['sha'] or
                        command(['git', 'status', '--porcelain=v1', '--untracked-files=all'], target)):
                    raise Blocked('pending worktree is dirty, changed, missing or outside the owned item')
            check_worktree()
            api = api or GitHub(root)
            verify = verify or verify_browser
            endpoint = f'repos/{REPO}/pulls/{number}'
            def check_pr():
                pr = api(endpoint)
                receipt = merged_receipt(pr, item)
                if (pr['number'] != number or pr['head']['sha'] != intent['sha'] or
                        pr['base']['sha'] != intent['base'] or receipt['merge_sha'] != intent['merge_sha']):
                    raise Blocked('existing publication does not match exact authorized SHAs')
                return pr
            pr = check_pr()
            if not quality_green(api, intent['sha'], pr['head']['ref']):
                raise Blocked('original exact-SHA quality workflow/job must be successful')
            status = api(f"repos/{REPO}/commits/{intent['sha']}/status")
            reviews = [s for s in status['statuses'] if s['context'] == 'independent-review']
            if (status.get('sha') != intent['sha'] or not reviews or
                    max(reviews, key=lambda s: s['id'])['state'] != 'success'):
                raise Blocked('original exact-SHA independent-review status must be successful')
            if not deployed(api, intent['merge_sha']):
                raise Blocked('matching Pages deployment is not successful')
            live = verify(root, intent['merge_sha'], intent['lesson_id'])
            if live.get('passed') is not True or live.get('sha') != intent['merge_sha']:
                raise Blocked('matching live browser verification required')
            check_pr()
            check_worktree()
            stamp = datetime.now(timezone.utc).isoformat()
            prefix = location / f"owner-completed-{item}-{intent['merge_sha']}"
            backup = Path(str(prefix) + '.sqlite3')
            receipt_file = Path(str(prefix) + '.json')
            if backup.exists() or receipt_file.exists():
                raise Blocked('prior reconciliation artifacts exist; inspect instead of overwriting')
            # Back up via SQLite, including WAL, before changing canonical pending state.
            fd = os.open(backup, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            os.close(fd)
            saved = sqlite3.connect(backup)
            try:
                store.db.backup(saved)
            finally:
                saved.close()
            receipt = {'kind': 'owner-completed-publication', 'recorded_at': stamp,
                       'intent': intent, 'prior_checkpoint': old, 'live': live,
                       'quality': True, 'independent_review': True,
                       'counts_as_new_daily_contribution': False, 'backup': str(backup)}
            fd = os.open(receipt_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            with os.fdopen(fd, 'w') as output:
                json.dump(receipt, output, sort_keys=True, indent=2)
                output.write('\n')
                output.flush()
                os.fsync(output.fileno())
            fd = os.open(location, os.O_RDONLY)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
            with store.db:
                store.db.execute('BEGIN IMMEDIATE')
                if (store.pending() != old or
                        store.db.execute("SELECT 1 FROM attempts WHERE status='running'").fetchone()):
                    raise Blocked('pending state changed during verification; archive retained, nothing cleared')
                store.db.execute('DELETE FROM checkpoint WHERE singleton=1')
            if store.pending():
                raise Blocked('completed checkpoint clearing did not read back')
            return {'status': 'owner publication reconciled', 'receipt': str(receipt_file),
                    'backup': str(backup), 'counts_as_new_daily_contribution': False}
        finally:
            store.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--file', type=Path, required=True, help='trusted owner intent JSON, never issue text')
    parser.add_argument('--authorize-existing-publication', action='store_true', required=True)
    args = parser.parse_args()
    print(json.dumps(reconcile_completed(ROOT, json.loads(args.file.read_text()))))


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(json.dumps({'error': str(exc)}))
        raise SystemExit(2)
