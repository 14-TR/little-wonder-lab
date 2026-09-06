"""Offline integration tests: every Git write is inside TemporaryDirectory."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
from autonomy_state import Store
from autonomy_runtime import run_lock


class CleanupTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve() / 'repo'
        self.root.mkdir()
        self.env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
        self.env.update(GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull,
                        GIT_AUTHOR_NAME='Fixture', GIT_AUTHOR_EMAIL='fixture@example.invalid',
                        GIT_COMMITTER_NAME='Fixture', GIT_COMMITTER_EMAIL='fixture@example.invalid')
        self.environment = patch.dict(os.environ, self.env, clear=True)
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.git('init', '-b', 'main')
        (self.root / '.gitignore').write_text('node_modules/\n')
        (self.root / 'lesson.txt').write_text('committed lesson\n')
        self.git('add', '.')
        self.git('commit', '-m', 'fixture')
        self.sha = self.git('rev-parse', 'HEAD').strip()
        self.location = self.root / '.git' / 'autonomy'
        self.store = Store(self.location / 'state.sqlite3')
        self.addCleanup(self.store.close)
        self.item = 'request-1'
        self.worktree = self.location / 'worktrees' / self.item
        self.git('worktree', 'add', '-b', 'auto/' + self.item, str(self.worktree))
        self.receipt = {'item': self.item, 'worktree': str(self.worktree),
                        'branch': 'auto/' + self.item, 'sha': self.sha,
                        'merge_sha': self.sha, 'stage': 'live',
                        'live': {'passed': True, 'sha': self.sha}}
        self.attempt = self.store.begin('2026-09-01')
        self.store.checkpoint(self.attempt, self.receipt)
        self.store.finish(self.attempt, 'success', day='2026-09-01')

    def git(self, *args, cwd=None):
        return subprocess.run(['git', *args], cwd=cwd or self.root, env=self.env,
                              text=True, capture_output=True, check=True, timeout=10).stdout

    def cleanup(self):
        self.assertIsNotNone(importlib.util.find_spec('autonomy_cleanup'),
                             'successful-worktree cleanup helper must exist')
        from autonomy_cleanup import cleanup_successful_worktrees
        with run_lock(self.location / 'run.lock'):
            return cleanup_successful_worktrees(self.root, self.store)

    def save_receipt(self):
        with self.store.db:
            self.store.db.execute('UPDATE releases SET receipt=?', (json.dumps(self.receipt),))

    def test_rejects_registered_worktree_outside_owned_root(self):
        outside = self.root.parent / 'unrelated'
        self.git('worktree', 'move', str(self.worktree), str(outside))
        self.receipt['worktree'] = str(outside)
        self.save_receipt()
        result = self.cleanup()
        self.assertTrue(outside.exists(), 'must not remove outside worktree')
        self.assertEqual(len(result['retained']), 1)
        self.assertEqual(result['cleaned'], [])

    def test_requires_verified_live_receipt_and_successful_attempt(self):
        original = dict(self.receipt)
        cases = [dict(stage='merged'), dict(live={'passed': False, 'sha': self.sha}),
                 dict(live={'passed': True, 'sha': '0' * 40}), dict(merge_sha='bad'),
                 dict(branch='main'), dict(item='../request-1'), dict(sha=None)]
        for changes in cases:
            with self.subTest(changes=changes):
                self.receipt = {**original, **changes}
                self.save_receipt()
                result = self.cleanup()
                self.assertEqual(result['cleaned'], [])
                self.assertTrue(self.worktree.exists())
        self.receipt = original
        self.save_receipt()
        with self.store.db:
            self.store.db.execute("UPDATE attempts SET status='blocked'")
        self.assertEqual(self.cleanup()['cleaned'], [])
        self.assertTrue(self.worktree.exists())

    def test_preserves_everything_when_running_or_pending(self):
        attempt = self.store.begin('2026-09-02')
        self.assertEqual(self.cleanup()['cleaned'], [])
        self.assertTrue(self.worktree.exists())
        self.store.checkpoint(attempt, {'item': self.item, 'stage': 'planned'})
        self.store.finish(attempt, 'blocked')
        self.assertEqual(self.cleanup()['cleaned'], [])
        self.assertTrue(self.worktree.exists())

    def test_requires_matching_registered_branch_and_recorded_head(self):
        self.git('switch', '-c', 'unrelated', cwd=self.worktree)
        self.assertEqual(self.cleanup()['cleaned'], [])
        self.assertTrue(self.worktree.exists())
        self.git('switch', 'auto/' + self.item, cwd=self.worktree)
        (self.worktree / 'lesson.txt').write_text('new unreleased work\n')
        self.git('add', 'lesson.txt', cwd=self.worktree)
        self.git('commit', '-m', 'unreleased', cwd=self.worktree)
        self.assertEqual(self.cleanup()['cleaned'], [])
        self.assertTrue(self.worktree.exists())

    def test_dirty_tracked_and_untracked_files_never_reach_remove(self):
        from autonomy_cleanup import _git
        for name in ('lesson.txt', 'untracked.txt'):
            with self.subTest(name=name):
                path = self.worktree / name
                path.write_text('precious work\n')
                with patch('autonomy_cleanup._git', wraps=_git) as calls:
                    result = self.cleanup()
                self.assertEqual(result['cleaned'], [])
                self.assertEqual(path.read_text(), 'precious work\n')
                self.assertFalse(any(call.args[1:3] == ('worktree', 'remove')
                                     for call in calls.call_args_list))
                if name == 'lesson.txt':
                    path.write_text('committed lesson\n')

    def test_malformed_receipts_are_retained_not_raised(self):
        for raw in ('{', '[]', '{}', json.dumps({**self.receipt, 'live': None})):
            with self.subTest(raw=raw):
                with self.store.db:
                    self.store.db.execute('UPDATE releases SET receipt=?', (raw,))
                try:
                    result = self.cleanup()
                except Exception as exc:
                    self.fail(f'cleanup must report retained for corrupt evidence: {exc}')
                self.assertEqual(result['cleaned'], [])
                self.assertTrue(result['retained'])
                self.assertTrue(self.worktree.exists())

    def test_duplicate_item_receipts_are_ambiguous(self):
        with self.store.db:
            self.store.db.execute('INSERT INTO releases VALUES (?,?,?)',
                                  ('2026-09-02', self.attempt, json.dumps(self.receipt)))
        self.assertEqual(self.cleanup()['cleaned'], [])
        self.assertTrue(self.worktree.exists())

    def test_symlinked_owned_root_cannot_escape(self):
        owned = self.worktree.parent
        moved = self.root.parent / 'moved-worktrees'
        owned.rename(moved)
        owned.symlink_to(moved, target_is_directory=True)
        self.assertEqual(self.cleanup()['cleaned'], [])
        self.assertTrue((moved / self.item / 'lesson.txt').exists())

    def test_remove_failure_has_no_force_or_weaker_retry(self):
        from autonomy_cleanup import _git
        def lock_before_remove(root, *args):
            if args[:2] == ('worktree', 'remove'):
                self.git('worktree', 'lock', str(self.worktree))
            return _git(root, *args)
        with patch('autonomy_cleanup._git', side_effect=lock_before_remove) as calls:
            result = self.cleanup()
        self.assertEqual(result['cleaned'], [])
        self.assertEqual(len(result['retained']), 1)
        self.assertTrue(self.worktree.exists())
        removes = [c.args for c in calls.call_args_list if c.args[1:3] == ('worktree', 'remove')]
        self.assertEqual(removes, [(self.root, 'worktree', 'remove', '--', str(self.worktree))])
        self.assertFalse(any('--force' in c.args or '-f' in c.args for c in calls.call_args_list))

    def test_unreceipted_unrelated_worktree_is_untouched(self):
        unrelated = self.root.parent / 'operator-worktree'
        self.git('worktree', 'add', '-b', 'operator', str(unrelated))
        self.cleanup()
        self.assertTrue(unrelated.exists())
        self.assertIn(str(unrelated), self.git('worktree', 'list', '--porcelain'))

    def test_already_removed_success_is_quiet(self):
        self.git('worktree', 'remove', str(self.worktree))
        self.assertEqual(self.cleanup(), {'cleaned': [], 'retained': []})

    def test_removes_clean_success_with_ignored_dependencies_preserves_receipt(self):
        dependencies = self.worktree / 'node_modules' / 'fixture'
        dependencies.mkdir(parents=True)
        (dependencies / 'package.js').write_text('ignored cache\n')
        log = self.location / 'attempt-1.log'
        log.write_text('retained evidence\n')
        before = self.store.db.execute('SELECT * FROM releases').fetchall()
        result = self.cleanup()
        self.assertEqual([x['item'] for x in result['cleaned']], [self.item])
        self.assertEqual(result['retained'], [])
        self.assertFalse(self.worktree.exists())
        self.assertNotIn(str(self.worktree), self.git('worktree', 'list', '--porcelain'))
        self.assertEqual(self.store.db.execute('SELECT * FROM releases').fetchall(), before)
        self.assertEqual(log.read_text(), 'retained evidence\n')
        self.assertEqual(self.git('rev-parse', 'auto/' + self.item).strip(), self.sha)


if __name__ == '__main__':
    unittest.main()
