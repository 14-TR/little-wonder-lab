"""Conservative local retention maintenance; caller MUST hold the run lock."""
import json
import sqlite3
import subprocess
from collections import Counter
from pathlib import Path
from autonomy_policy import item_id, sha40
from autonomy_state import Blocked


def _git(root, *args):
    return subprocess.run(['git', *args], cwd=root, text=True, capture_output=True,
                          check=True, timeout=60).stdout


def cleanup_successful_worktrees(root, store):
    """Remove only proven successful worktrees; never delete receipts or branches."""
    result = {'cleaned': [], 'retained': []}
    try:
        common = Path(_git(root, 'rev-parse', '--path-format=absolute', '--git-common-dir').strip()).resolve()
        rows = [(day, attempt, json.loads(raw)) for day, attempt, raw in
                store.db.execute('SELECT day, attempt, receipt FROM releases')]
        counts = Counter(item_id(receipt['item']) for _, _, receipt in rows)
    except (Blocked, KeyError, TypeError, ValueError, OSError, sqlite3.Error,
            subprocess.SubprocessError) as exc:
        return {'cleaned': [], 'retained': [{'item': None, 'worktree': None, 'reason': str(exc)}]}
    owned = common / 'autonomy' / 'worktrees'
    for day, attempt, receipt in rows:
        entry = {'day': day, 'item': None, 'worktree': None}
        try:
            entry.update(item=receipt['item'], worktree=receipt['worktree'])
            if counts[receipt['item']] != 1:
                raise ValueError('multiple receipts for one item are ambiguous')
            if (store.db.execute("SELECT 1 FROM attempts WHERE status='running'").fetchone() or
                    store.db.execute('SELECT 1 FROM checkpoint').fetchone()):
                raise ValueError('active or pending work exists; retain all worktrees')
            item_id(receipt['item'])
            sha40(receipt.get('sha'))
            sha40(receipt.get('merge_sha'))
            if (receipt.get('stage') != 'live' or
                    receipt.get('branch') != 'auto/' + receipt['item'] or
                    receipt.get('live', {}).get('passed') is not True or
                    receipt.get('live', {}).get('sha') != receipt['merge_sha'] or
                    not store.db.execute("SELECT 1 FROM attempts WHERE id=? AND status='success'",
                                         (attempt,)).fetchone()):
                raise ValueError('successful matching live receipt required')
            target = owned / receipt['item']
            if (target.parent != owned or target.resolve() != target or
                    receipt['worktree'] != str(target)):
                raise ValueError('worktree path is not the exact confined owned path')
            records = []
            for block in _git(root, 'worktree', 'list', '--porcelain', '-z').split('\0\0'):
                fields = dict(field.split(' ', 1) if ' ' in field else (field, '')
                              for field in block.split('\0') if field)
                if fields.get('worktree') == str(target):
                    records.append(fields)
            if not records and not target.exists():
                continue
            if (len(records) != 1 or records[0].get('branch') != 'refs/heads/' + receipt['branch'] or
                    records[0].get('HEAD') != receipt['sha'] or
                    any(flag in records[0] for flag in ('locked', 'prunable', 'bare', 'detached'))):
                raise ValueError('registered worktree branch/head is missing or changed')
            if _git(target, 'status', '--porcelain=v1', '-z', '--untracked-files=all',
                    '--ignore-submodules=none'):
                raise ValueError('dirty worktree retained')
            _git(root, 'worktree', 'remove', '--', str(target))
            result['cleaned'].append(entry)
        except (Blocked, KeyError, TypeError, AttributeError, ValueError, OSError,
                sqlite3.Error, subprocess.SubprocessError) as exc:
            result['retained'].append({**entry, 'reason': str(exc)})
    return result
