#!/usr/bin/env python3
"""Little Wonder Lab bounded lead entrypoint. See docs/AUTONOMY.md."""
import argparse
import json
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from autonomy_state import Blocked, Store
from autonomy_runtime import run_lock, bounded_run, unresolved_guard, clear_after_success
from autonomy_cleanup import cleanup_successful_worktrees, owned_worktree_root
from autonomy_release import Git, GitHub, command, release
from autonomy_policy import REPO, allowed_path, item_id, pages, scan_requests, sha40, validate_changes, validate_release

ROOT = Path(__file__).resolve().parents[1]


def today():
    return datetime.now(ZoneInfo('America/Denver')).date().isoformat()


def state_dir(root):
    gitdir = Path(command(['git', 'rev-parse', '--path-format=absolute', '--git-common-dir'], root))
    return gitdir / 'autonomy'


def lead_command(root):
    return ['hermes', '--profile', 'default', 'chat', '--oneshot', '-Q', '--pass-session-id',
            '--provider', 'openai-codex', '--model', 'gpt-6-astra', '--max-turns', '90',
            '--run-budget', '2100', '--in', str(root), '--toolsets', 'terminal,file,web,skills,vision',
            '--query-file', str(root / 'automation/roles/lead.md')]


def stamp(root, sha):
    sha40(sha)
    lessons = json.loads((root / 'src/data/lessons.json').read_text())
    payload = {'sha': sha, 'lessons': [{'id': x['id'], 'title': x['title']} for x in lessons]}
    (root / 'dist/release.json').write_text(json.dumps(payload, sort_keys=True) + '\n')


def active(store):
    try:
        attempt = int(os.environ['LWL_ATTEMPT'])
    except (KeyError, ValueError) as exc:
        raise Blocked('state mutation requires the supervised lead environment') from exc
    row = store.db.execute("SELECT 1 FROM attempts WHERE id=? AND status='running'", (attempt,)).fetchone()
    if not row:
        raise Blocked('attempt is not active')
    return attempt


def sync_main(root):
    if command(['git', 'branch', '--show-current'], root) != 'main' or command(['git', 'status', '--porcelain'], root):
        raise Blocked('operator checkout must be clean main; never stash/reset user work')
    command(['git', 'fetch', 'origin', 'main'], root)
    command(['git', 'merge', '--ff-only', 'origin/main'], root)


def check_repo(root):
    if command(['git', 'remote', 'get-url', 'origin'], root) not in {
            f'https://github.com/{REPO}.git', f'git@github.com:{REPO}.git'}:
        raise Blocked('unexpected origin')
    sync_main(root)
    command(['gh', 'auth', 'status'], root, timeout=30)


def supervise(root, runner=bounded_run, preflight=check_repo):
    location = state_dir(root)
    with run_lock(location / 'run.lock') as fd:
        store = Store(location / 'state.sqlite3')
        try:
            decision = unresolved_guard(location) or store.gate(today())
            if not decision['wakeAgent']:
                return decision
            attempt = store.begin(today())
            try:
                preflight(root)
                env = dict(os.environ, TERMINAL_CWD=str(root), LWL_ATTEMPT=str(attempt),
                           LWL_ROOT=str(root), LWL_STATE=str(location))
                code = runner(lead_command(root), root, env, location / f'attempt-{attempt}.log', fd, seconds=2400)
                row = store.db.execute('SELECT status FROM attempts WHERE id=?', (attempt,)).fetchone()
                if code != 0 or row[0] != 'success':
                    raise Blocked(f'attempt {attempt} stopped without verified live success; see {location}/attempt-{attempt}.log')
                clear_after_success(location, attempt, returncode=code, verified_success=row[0] == 'success')
                cleanup = cleanup_successful_worktrees(root, store)
                return {'wakeAgent': True, 'status': 'verified live', 'attempt': attempt, 'cleanup': cleanup}
            except BaseException:
                row = store.db.execute('SELECT status FROM attempts WHERE id=?', (attempt,)).fetchone()
                if row and row[0] == 'running':
                    store.finish(attempt, 'blocked')
                raise
        finally:
            store.close()


def prepare(root, item):
    item_id(item)
    location = owned_worktree_root(root) / item
    if location.resolve() != location:
        raise Blocked('worktree path must not be a symlink')
    branch = 'auto/' + item
    command(['git', 'fetch', 'origin', 'main'], root)
    if location.exists():
        if command(['git', 'branch', '--show-current'], location) != branch:
            raise Blocked('worktree branch mismatch')
    else:
        refs = command(['git', 'for-each-ref', '--format=%(refname)', 'refs/heads/' + branch, 'refs/remotes/origin/' + branch], root).splitlines()
        if 'refs/heads/' + branch in refs:
            command(['git', 'worktree', 'add', str(location), branch], root)
        elif 'refs/remotes/origin/' + branch in refs:
            command(['git', 'worktree', 'add', '-b', branch, str(location), 'origin/' + branch], root)
        else:
            command(['git', 'worktree', 'add', '-b', branch, str(location), 'origin/main'], root)
    return {'item': item, 'worktree': str(location), 'branch': branch,
            'base': command(['git', 'rev-parse', 'origin/main'], root)}


def check_local(worktree, base):
    sha40(base)
    for entry in command(['git', 'status', '--porcelain=v1', '-z', '--untracked-files=all'], worktree).split('\0'):
        if entry and (entry[:2].strip() in {'R', 'C', '??'} or not allowed_path(entry[3:])):
            raise Blocked('protected/untracked path or rename in worktree')
    files = []
    for entry in command(['git', 'diff', '--numstat', '-z', '--no-renames', base, '--'], worktree).split('\0'):
        if not entry: continue
        added, removed, path = entry.split('\t', 2)
        if not added.isdecimal() or not removed.isdecimal():
            raise Blocked('binary change requires human review')
        target = worktree / path
        files.append({'filename': path, 'status': 'modified' if target.exists() else 'removed',
                      'changes': int(added) + int(removed), 'mode': '120000' if target.is_symlink() else '100644'})
    before = json.loads(command(['git', 'show', base + ':src/data/lessons.json'], worktree))
    after = json.loads((worktree / 'src/data/lessons.json').read_text())
    validate_changes(files, before, after)
    return {'passed': True, 'files': [f['filename'] for f in files]}


def merged_receipt(pr, item):
    item_id(item)
    if (pr.get('merged') is not True or pr.get('state') != 'closed' or
            pr['head']['repo']['full_name'] != REPO or pr['base']['repo']['full_name'] != REPO or
            pr['head']['ref'] != 'auto/' + item or pr['base']['ref'] != 'main' or
            f'<!-- lwl:item:{item} -->' not in (pr.get('body') or '')):
        raise Blocked('cannot recover an unmerged, mismatched, or untrusted PR')
    return {'item': item, 'pr': pr['number'], 'merge_sha': sha40(pr['merge_commit_sha']), 'stage': 'merged'}


def deployed(api, sha):
    sha40(sha)
    runs = pages(lambda u: api(u)['workflow_runs'], f'repos/{REPO}/actions/workflows/deploy.yml/runs?head_sha={sha}&branch=main')
    candidates = [r for r in runs if r['head_sha'] == sha and r['head_branch'] == 'main' and r['event'] == 'workflow_run']
    if not candidates: return False
    latest = max(candidates, key=lambda r: r['id'])
    return latest['status'] == 'completed' and latest['conclusion'] == 'success'


def autonomous_recovery_receipt(location, old, pr):
    """Require canonical evidence saved AFTER the protected merge read-back.

    A checkpoint or public marker alone is not autonomous publication provenance.
    This trusts the private operator state directory, not caller evidence_file paths.
    """
    try:
        receipt = merged_receipt(pr, old['item'])
        sha, base = sha40(pr['head']['sha']), sha40(pr['base']['sha'])
        if (old.get('pr') != pr['number'] or old.get('sha') != sha or old.get('base') != base or
                old.get('reviewed_sha', sha) != sha or
                old.get('merge_sha', receipt['merge_sha']) != receipt['merge_sha']):
            raise Blocked('checkpoint differs from the saved release')
        proof = location / ('evidence-' + sha + '.json')
        if proof.is_symlink() or not proof.is_file():
            raise Blocked('canonical supervised merge evidence missing')
        evidence = json.loads(proof.read_text())
        # Reuse the strict historical identity/review schema, not an assertion
        # that the closed PR is currently open or that current CI is successful.
        validate_release({**pr, 'state': 'open', 'draft': False}, evidence, base, quality=True)
        return {**receipt, 'reviewed_sha': sha}
    except (Blocked, OSError, ValueError, KeyError, TypeError) as exc:
        raise Blocked('autonomous release provenance missing or ambiguous; STOP for owner-only reconciliation') from exc


def main(argv=None, root=ROOT):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['run', 'gate', 'status', 'checkpoint', 'stamp', 'scan', 'prepare', 'check-local', 'merge', 'recover-merged', 'verify-live'])
    parser.add_argument('--file', type=Path)
    parser.add_argument('--sha')
    parser.add_argument('--item')
    parser.add_argument('--base')
    parser.add_argument('--pr', type=int)
    parser.add_argument('--lesson')
    args = parser.parse_args(argv)
    if args.action == 'run':
        print(json.dumps(supervise(root)))
        return
    if args.action == 'stamp':
        stamp(root, sha40(args.sha))
        return
    location = state_dir(root)
    store = Store(location / 'state.sqlite3')
    try:
        if args.action == 'gate':
            try:
                with run_lock(location / 'run.lock'):
                    result = unresolved_guard(location) or store.gate(today())
            except Blocked as exc:
                result = {'wakeAgent': False, 'reason': str(exc)}
            print(json.dumps(result))
        elif args.action == 'status':
            print(json.dumps({'gate': unresolved_guard(location) or store.gate(today()), 'checkpoint': store.pending(), 'attempts_today': store.attempts(today())}))
        elif args.action == 'scan':
            result = scan_requests(GitHub(root))
            target = location / 'requests.json'
            target.write_text(json.dumps(result, indent=2) + '\n')
            print(json.dumps({'file': str(target), 'requests': len(result['requests']), 'existing_prs': len(result['existing_prs'])}))
        elif args.action == 'prepare':
            attempt = active(store)
            item = item_id(args.item)
            old = store.pending()
            if old and old.get('item') != item:
                raise Blocked('recover pending item first')
            result = prepare(root, item)
            store.checkpoint(attempt, {**result, **old, 'stage': old.get('stage', 'planned')})
            print(json.dumps(store.pending()))
        elif args.action == 'check-local':
            item = item_id(args.item)
            print(json.dumps(check_local(owned_worktree_root(root) / item, sha40(args.base))))
        elif args.action in {'merge', 'recover-merged'}:
            attempt = active(store)
            old = store.pending()
            item = item_id(old.get('item'))
            if type(args.pr) is not int or args.pr < 1 or old.get('pr') != args.pr:
                raise Blocked('checkpoint the exact PR number before releasing')
            api = GitHub(root)
            if args.action == 'recover-merged':
                receipt = autonomous_recovery_receipt(location, old, api(f'repos/{REPO}/pulls/{args.pr}'))
            else:
                evidence = json.loads(args.file.read_text())
                receipt_file = location / ('evidence-' + sha40(evidence['sha']) + '.json')
                receipt = release(api, Git(root), args.pr, evidence, item)
                receipt_file.write_text(json.dumps(evidence, sort_keys=True) + '\n')
            store.checkpoint(attempt, {**old, **receipt})
            print(json.dumps(store.pending()))
        elif args.action == 'verify-live':
            attempt = active(store)
            old = store.pending()
            if old.get('stage') != 'merged' or not args.lesson or old.get('lesson_id') != args.lesson:
                raise Blocked('matching merged checkpoint and planned lesson ID required')
            api = GitHub(root)
            receipt = autonomous_recovery_receipt(location, old, api(f"repos/{REPO}/pulls/{old['pr']}"))
            if receipt['merge_sha'] != old.get('merge_sha') or not deployed(api, receipt['merge_sha']):
                raise Blocked('matching Pages deployment is not successful yet')
            live = json.loads(command(['node', str(root / 'scripts/verify-live.mjs'), receipt['merge_sha'], args.lesson], root, timeout=120))
            if live.get('passed') is not True or live.get('sha') != receipt['merge_sha']:
                raise Blocked('live browser verification failed')
            store.checkpoint(attempt, {**old, 'stage': 'live', 'live': live})
            store.finish(attempt, 'success', day=today())
            print(json.dumps({'status': 'verified live', **live}))
        elif args.action == 'checkpoint':
            attempt = active(store)
            data = json.loads(args.file.read_text())
            item_id(data['item'])
            if data.get('stage') not in {'planned', 'engineered', 'reviewed'}:
                raise Blocked('only release/live helpers may record merged or live')
            previous = store.pending()
            if previous and (previous.get('item') != data['item'] or previous.get('stage') in {'merged', 'live'}):
                raise Blocked('recover the existing item; never overwrite a pending release')
            store.checkpoint(attempt, data)
            print(json.dumps(store.pending()))
    finally:
        store.close()


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(json.dumps({'error': str(exc), 'wakeAgent': False}))
        raise SystemExit(2)
