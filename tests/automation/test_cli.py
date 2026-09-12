import contextlib
import importlib.util
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))


class CLITests(unittest.TestCase):
    def test_sync_fast_forwards_clean_main_and_preserves_dirty_work(self):
        import autonomy as a
        self.assertTrue(hasattr(a, 'sync_main'), 'clean main synchronization missing')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'repo'; origin = Path(tmp) / 'origin'; other = Path(tmp) / 'other'
            subprocess.run(['git', 'init', '-q', '-b', 'main', str(root)], check=True)
            subprocess.run(['git', 'init', '-q', '--bare', str(origin)], check=True)
            def git(where, *args): return subprocess.run(['git', *args], cwd=where, check=True, capture_output=True, text=True).stdout.strip()
            (root / 'lesson').write_text('old')
            git(root, 'add', 'lesson'); git(root, '-c','user.name=Test','-c','user.email=test@example.invalid','commit','-qm','fixture')
            git(root, 'remote','add','origin',str(origin)); git(root,'push','-q','origin','main')
            subprocess.run(['git','clone','-q','-b','main',str(origin),str(other)],check=True)
            (other / 'lesson').write_text('new')
            git(other,'add','lesson'); git(other,'-c','user.name=Test','-c','user.email=test@example.invalid','commit','-qm','new fixture')
            git(other,'push','-q','origin','main')
            a.sync_main(root)
            self.assertEqual((root / 'lesson').read_text(), 'new')
            (root / 'lesson').write_text('human draft')
            with self.assertRaises(a.Blocked): a.sync_main(root)
            self.assertEqual((root / 'lesson').read_text(), 'human draft')

    def test_recover_merged_requires_trusted_matching_item_and_live_deploy(self):
        import autonomy as a
        self.assertTrue(hasattr(a, 'merged_receipt'), 'merge recovery missing')
        sha = 'a'*40
        pr = {'number': 42, 'state': 'closed', 'merged': True, 'merge_commit_sha': sha,
              'head': {'ref': 'auto/request-42', 'repo': {'full_name': a.REPO}},
              'base': {'ref': 'main', 'repo': {'full_name': a.REPO}}, 'body': '<!-- lwl:item:request-42 -->'}
        self.assertEqual(a.merged_receipt(pr, 'request-42')['merge_sha'], sha)
        with self.assertRaises(a.Blocked): a.merged_receipt(pr, 'request-43')
        with self.assertRaises(a.Blocked): a.merged_receipt({**pr, 'merged': False}, 'request-42')
        def api(url):
            return {'workflow_runs': [{'id': 1, 'head_sha': sha, 'head_branch': 'main', 'event': 'workflow_run',
                                      'status': 'completed', 'conclusion': 'success'}]}
        self.assertTrue(a.deployed(api, sha))
        self.assertFalse(a.deployed(api, 'b'*40))

    def test_local_guard_blocks_untracked_protected_files(self):
        import autonomy as a
        self.assertTrue(hasattr(a, 'check_local'), 'local change guard missing')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(['git', 'init', '-q', '-b', 'auto/request-1', str(root)], check=True)
            def git(*args): return subprocess.run(['git', *args], cwd=root, check=True, capture_output=True, text=True).stdout.strip()
            (root / 'src/data').mkdir(parents=True)
            lesson = root / 'src/data/lessons.json'
            lesson.write_text('[{"id":"one","idea":"a"}]')
            git('add', 'src'); git('-c','user.name=Test','-c','user.email=test@example.invalid','commit','-qm','fixture')
            base = git('rev-parse', 'HEAD')
            lesson.write_text('[{"id":"one","idea":"b"}]')
            a.check_local(root, base)
            (root / 'src/new.js').write_text('untracked code must be staged before guard')
            with self.assertRaises(a.Blocked): a.check_local(root, base)
            git('add', 'src/new.js')
            a.check_local(root, base)
            (root / 'AGENTS.md').write_text('untrusted instructions')
            with self.assertRaises(a.Blocked): a.check_local(root, base)

    def test_prepare_reuses_item_worktree_without_touching_operator_tree(self):
        import autonomy as a
        self.assertTrue(hasattr(a, 'prepare'), 'worktree preparation missing')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'repo'; origin = Path(tmp) / 'origin'
            subprocess.run(['git', 'init', '-q', '-b', 'main', str(root)], check=True)
            subprocess.run(['git', 'init', '-q', '--bare', str(origin)], check=True)
            def git(*args): return subprocess.run(['git', *args], cwd=root, check=True, capture_output=True, text=True).stdout.strip()
            (root / '.gitignore').write_text('/.autonomy-worktrees/\n')
            (root / 'src/data').mkdir(parents=True)
            (root / 'src/data/lessons.json').write_text('[{"id":"one","idea":"a"}]')
            git('add', '.')
            git('-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', 'commit', '-qm', 'fixture')
            git('remote', 'add', 'origin', str(origin)); git('push', '-q', '-u', 'origin', 'main')
            first = a.prepare(root, 'request-42')
            second = a.prepare(root, 'request-42')
            self.assertEqual(first, second)
            worktree = Path(first['worktree'])
            self.assertEqual(worktree, root.resolve() / '.autonomy-worktrees/request-42')
            self.assertEqual(a.prepare(worktree, 'request-42'), first)
            (worktree / 'src/data/lessons.json').write_text('[{"id":"one","idea":"b"}]')
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                a.main(['check-local', '--item', 'request-42', '--base', first['base']], root=worktree)
            self.assertTrue(json.loads(output.getvalue())['passed'])
            self.assertTrue(Path(first['worktree']).is_dir())
            self.assertEqual(git('branch', '--show-current'), 'main')
            self.assertEqual(git('status', '--porcelain'), '')

    def test_supervisor_enforces_budget_after_failed_runs(self):
        import autonomy as a
        self.assertTrue(hasattr(a, 'supervise'), 'supervisor missing')
        calls = []
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(['git', 'init', '-q', str(root)], check=True)
            def runner(command, cwd, env, log, fd, seconds):
                calls.append(env['LWL_ATTEMPT'])
                self.assertEqual(env['TERMINAL_CWD'], str(root))
                self.assertEqual(seconds, 2400)
                return 1
            for _ in range(2):
                with self.assertRaises(a.Blocked):
                    a.supervise(root, runner=runner, preflight=lambda _: None)
            self.assertFalse(a.supervise(root, runner=runner, preflight=lambda _: None)['wakeAgent'])
            self.assertEqual(len(calls), 2)

    def test_supervisor_pins_lead_deadline_in_real_child_environment(self):
        import autonomy as a
        import time
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(['git','init','-q',str(root)], check=True)
            observed = []
            before = time.time()
            def runner(command, cwd, env, log, fd, seconds):
                raw = subprocess.check_output([sys.executable,'-c',
                    "import os,json; print(json.dumps(dict(os.environ)))"], cwd=cwd, env=env)
                child_env = json.loads(raw)
                self.assertTrue('LWL_LEAD_DEADLINE' in child_env, 'supervisor must pin the lead deadline')
                deadline = float(child_env['LWL_LEAD_DEADLINE'])
                self.assertGreaterEqual(deadline, before+2100)
                self.assertLessEqual(deadline, time.time()+2100)
                observed.append(deadline)
                return 1  # No model, release or production state: isolated failed fixture.
            with self.assertRaises(a.Blocked):
                a.supervise(root, runner=runner, preflight=lambda _: None)
            self.assertEqual(len(observed),1)

    def test_supervisor_cleans_only_after_verified_success_under_lock(self):
        import autonomy as a
        from unittest.mock import patch
        calls = []
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(['git', 'init', '-q', str(root)], check=True)
            def runner(command, cwd, env, log, fd, seconds):
                store = a.Store(a.state_dir(root) / 'state.sqlite3')
                attempt = int(env['LWL_ATTEMPT'])
                store.checkpoint(attempt, {'stage': 'live', 'item': 'test-fixture'})
                store.finish(attempt, 'success', day=a.today())
                store.close()
                return 0
            def cleanup(where, store):
                self.assertEqual(where, root)
                self.assertFalse(store.pending())
                with self.assertRaises(a.Blocked):
                    with a.run_lock(a.state_dir(root) / 'run.lock'):
                        self.fail('supervisor released its lock before cleanup')
                calls.append('cleaned')
                return {'cleaned': ['test-fixture'], 'retained': []}
            with patch.object(a, 'cleanup_successful_worktrees', cleanup, create=True):
                result = a.supervise(root, runner=runner, preflight=lambda _: None)
            self.assertEqual(calls, ['cleaned'])
            self.assertEqual(result['cleanup']['cleaned'], ['test-fixture'])

    def test_gate_and_checkpoint_require_supervised_attempt(self):
        self.assertTrue((ROOT / 'scripts/autonomy.py').exists(), 'CLI missing')
        import autonomy as a
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(['git', 'init', '-q', str(root)], check=True)
            output = io.StringIO()
            with contextlib.redirect_stdout(output): a.main(['gate'], root=root)
            self.assertTrue(json.loads(output.getvalue())['wakeAgent'])
            with self.assertRaises(a.Blocked): a.main(['checkpoint', '--file', str(root / 'missing.json')], root=root)
            command = a.lead_command(root)
            self.assertIn('--run-budget', command)
            self.assertEqual(command[command.index('--run-budget') + 1], '2100')
            self.assertNotIn('--yolo', command)

    def test_stamp_build_writes_real_lesson_manifest(self):
        self.assertTrue((ROOT / 'scripts/autonomy.py').exists(), 'CLI missing')
        import autonomy as a
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); (root / 'dist').mkdir(); (root / 'src/data').mkdir(parents=True)
            (root / 'src/data/lessons.json').write_text(json.dumps([{'id': 'one', 'title': 'One'}]))
            a.stamp(root, 'a'*40)
            self.assertEqual(json.loads((root / 'dist/release.json').read_text()), {'sha': 'a'*40, 'lessons': [{'id': 'one', 'title': 'One'}]})
            with self.assertRaises(a.Blocked): a.stamp(root, 'malformed')


if __name__ == '__main__': unittest.main()
