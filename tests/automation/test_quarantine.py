import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import autonomy as a
import autonomy_runtime as r


class QuarantineIntegrationTests(unittest.TestCase):
    def test_all_entry_gates_block_marker_without_reserving_attempt(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(['git', 'init', '-q', str(root)], check=True)
            location = a.state_dir(root)
            location.mkdir(parents=True)
            # Corruption and a dangling symlink must block just like a valid receipt.
            marker = location / 'unresolved-process.json'
            for kind in ('malformed', 'symlink'):
                if kind == 'malformed':
                    marker.write_text('{broken')
                else:
                    marker.symlink_to(location / 'nonexistent')
                for day in ('2026-09-06', '2026-09-07'):
                    with patch.object(a, 'today', return_value=day):
                        for action in ('gate', 'status'):
                            output = io.StringIO()
                            with contextlib.redirect_stdout(output):
                                a.main([action], root=root)
                            result = json.loads(output.getvalue())
                            gate = result['gate'] if action == 'status' else result
                            self.assertFalse(gate['wakeAgent'])
                            self.assertIn('unresolved', gate['reason'])
                        def forbidden(*args, **kwargs):
                            self.fail('quarantine reached preflight or launch')
                        self.assertFalse(a.supervise(root, runner=forbidden, preflight=forbidden)['wakeAgent'])
                        store = a.Store(location / 'state.sqlite3')
                        self.assertEqual(store.attempts(day), 0)
                        store.close()
                marker.unlink()

    def test_only_same_supervisor_verified_success_zero_exit_clears(self):
        self.assertTrue(hasattr(r, 'clear_after_success'), 'verified-success clearing missing')
        with tempfile.TemporaryDirectory() as tmp:
            location = Path(tmp)
            with r.run_lock(location / 'run.lock') as fd:
                code = r.bounded_run([sys.executable, '-c', 'print("clean child")'], location,
                                     dict(os.environ, LWL_ATTEMPT='7'), location / 'log', fd, seconds=5)
                self.assertEqual(code, 0)
                for returncode, verified, attempt in ((1, True, 7), (0, False, 7), (0, True, 8)):
                    with self.assertRaises(r.Blocked):
                        r.clear_after_success(location, attempt, returncode=returncode, verified_success=verified)
                    self.assertIsNotNone(r.unresolved_guard(location))
                r.clear_after_success(location, 7, returncode=0, verified_success=True)
                self.assertIsNone(r.unresolved_guard(location))

    def test_real_runner_unverified_zero_exit_blocks_next_supervision(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(['git', 'init', '-q', str(root)], check=True)
            with patch.object(a, 'lead_command', return_value=[sys.executable, '-c', 'pass']):
                with self.assertRaises(a.Blocked):
                    a.supervise(root, preflight=lambda _: None)
                result = a.supervise(root, preflight=lambda _: self.fail('reentered preflight'))
                self.assertFalse(result['wakeAgent'])

    def test_real_success_clears_before_cleanup(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(['git', 'init', '-q', str(root)], check=True)
            code = (f"import sys,os,pathlib; sys.path.insert(0,{str(ROOT / 'scripts')!r}); "
                    "from autonomy_state import Store; from autonomy import today; "
                    "s=Store(pathlib.Path(os.environ['LWL_STATE'])/'state.sqlite3'); "
                    "n=int(os.environ['LWL_ATTEMPT']); s.checkpoint(n,{'stage':'live'}); "
                    "s.finish(n,'success',day=today()); s.close()")
            def cleanup(where, store):
                self.assertIsNone(r.unresolved_guard(a.state_dir(root)))
                with self.assertRaises(r.Blocked):
                    with r.run_lock(a.state_dir(root) / 'run.lock'):
                        pass
                return {'cleaned': [], 'retained': []}
            with patch.object(a, 'lead_command', return_value=[sys.executable, '-c', code]), patch.object(a, 'cleanup_successful_worktrees', cleanup):
                result = a.supervise(root, preflight=lambda _: None)
            self.assertEqual(result['status'], 'verified live')


if __name__ == '__main__':
    unittest.main()
