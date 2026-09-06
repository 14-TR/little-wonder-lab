import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))


class RuntimeTests(unittest.TestCase):
    def test_os_lock_rejects_overlap_and_timeout_kills_process(self):
        self.assertTrue((ROOT / 'scripts/autonomy_runtime.py').exists(), 'bounded runtime is missing')
        import autonomy_runtime as r
        with tempfile.TemporaryDirectory() as tmp:
            lock = Path(tmp) / 'run.lock'
            with r.run_lock(lock) as fd:
                with self.assertRaises(r.Blocked):
                    with r.run_lock(lock): pass
                start = time.monotonic()
                with self.assertRaises(r.Blocked):
                    r.bounded_run([sys.executable, '-c', 'import time; time.sleep(30)'],
                                  Path(tmp), os.environ.copy(), Path(tmp) / 'log', fd, seconds=0.2)
                self.assertLess(time.monotonic() - start, 5)
            with r.run_lock(lock) as fd:
                with self.assertRaisesRegex(r.Blocked, 'unresolved'):
                    r.bounded_run([sys.executable, '-c', 'print("must not launch")'],
                                  Path(tmp), os.environ.copy(), Path(tmp) / 'log', fd, seconds=5)
            self.assertNotIn('must not launch', (Path(tmp) / 'log').read_text())


class QuarantineTests(unittest.TestCase):
    def wait_file(self, path):
        deadline = time.monotonic() + 5
        while not path.exists() and time.monotonic() < deadline:
            time.sleep(0.01)
        self.assertTrue(path.exists(), f'child did not create {path}')
        return int(path.read_text())

    def orphan_command(self, tmp):
        # Portable equivalent of ordinary LocalEnvironment: new session, close_fds.
        tool = "import os,time,pathlib; pathlib.Path('tool.pid').write_text(str(os.getpid())); time.sleep(30)"
        return [sys.executable, '-c',
                "import subprocess,sys,time,os,pathlib; "
                "pathlib.Path('lead.pid').write_text(str(os.getpid())); "
                f"subprocess.Popen([sys.executable,'-c',{tool!r}], start_new_session=True, close_fds=True); "
                "exec(\"while not pathlib.Path('release').exists(): time.sleep(0.01)\")"]

    def kill_owned(self, pid):
        import signal
        try:
            os.killpg(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass

    def assert_future_blocked(self, r, location):
        self.assertTrue(hasattr(r, 'unresolved_guard'), 'persistent unresolved-process gate is missing')
        from autonomy_state import Store
        store = Store(location / 'state.sqlite3')
        try:
            for day in ('2026-09-06', '2026-09-07', '2030-01-01'):
                self.assertTrue(store.gate(day)['wakeAgent'])
                decision = r.unresolved_guard(location) or store.gate(day)
                self.assertFalse(decision['wakeAgent'])
                self.assertIn('unresolved', decision['reason'])
        finally:
            store.close()

    def test_timeout_new_session_tool_survives_but_future_gate_is_quarantined(self):
        import autonomy_runtime as r
        with tempfile.TemporaryDirectory() as tmp:
            location = Path(tmp)
            try:
                with r.run_lock(location / 'run.lock') as fd:
                    with self.assertRaisesRegex(r.Blocked, 'wall-clock'):
                        r.bounded_run(self.orphan_command(tmp), location, os.environ.copy(),
                                      location / 'log', fd, seconds=getattr(self, 'budget', 0.4))
                pid = self.wait_file(location / 'tool.pid')
                os.kill(pid, 0)
                with r.run_lock(location / 'run.lock'):
                    self.assert_future_blocked(r, location)
            finally:
                if (location / 'tool.pid').exists():
                    self.kill_owned(int((location / 'tool.pid').read_text()))

    def test_abrupt_supervisor_death_leaves_quarantine_after_lock_releases(self):
        import autonomy_runtime as r
        with tempfile.TemporaryDirectory() as tmp:
            location = Path(tmp)
            supervisor_code = (
                f"import sys,os,pathlib; sys.path.insert(0,{str(ROOT / 'scripts')!r}); "
                "import autonomy_runtime as r; "
                f"p=pathlib.Path({tmp!r}); "
                "\nwith r.run_lock(p / 'run.lock') as fd:\n "
                f"r.bounded_run({self.orphan_command(tmp)!r}, p, os.environ.copy(), p / 'log', fd, seconds=30)")
            supervisor = subprocess.Popen([sys.executable, '-c', supervisor_code], cwd=tmp)
            try:
                pid = self.wait_file(location / 'tool.pid')
                lead = self.wait_file(location / 'lead.pid')
                supervisor.kill()
                supervisor.wait(timeout=3)
                # The lead may inherit flock; end it, leaving only the ordinary tool.
                self.kill_owned(lead)
                deadline = time.monotonic() + 3
                while True:
                    try:
                        with r.run_lock(location / 'run.lock'):
                            os.kill(pid, 0)
                            self.assert_future_blocked(r, location)
                        break
                    except r.Blocked:
                        if time.monotonic() >= deadline:
                            raise
                        time.sleep(0.01)
            finally:
                if supervisor.poll() is None:
                    supervisor.kill()
                supervisor.wait(timeout=3)
                for name in ('lead.pid', 'tool.pid'):
                    if (location / name).exists():
                        self.kill_owned(int((location / name).read_text()))


@unittest.skipUnless(os.environ.get('LWL_HERMES_SOURCE'), 'opt in with installed Hermes source and its Python environment')
class InstalledLocalBackendTests(QuarantineTests):
    budget = 2

    def orphan_command(self, tmp):
        source = Path(os.environ['LWL_HERMES_SOURCE'])
        self.assertTrue((source / 'tools/environments/local.py').is_file())
        # No initialization/config snapshot: exercise the real ordinary launch site
        # with a temporary home and a minimal tool environment, never a model call.
        return [sys.executable, '-c',
                f"import sys,os,pathlib,time; os.environ['HERMES_HOME']={str(Path(tmp) / 'home')!r}; "
                f"sys.path.insert(0,{str(source)!r}); "
                "from tools.environments.local import LocalEnvironment; "
                "e=LocalEnvironment.__new__(LocalEnvironment); "
                f"e.cwd={tmp!r}; e.env={{'PATH':os.defpath,'HOME':{tmp!r}}}; "
                "pathlib.Path('lead.pid').write_text(str(os.getpid())); "
                "p=e._run_bash(\"printf '%s' $$ > tool.pid; exec sleep 30\"); "
                "exec(\"while not pathlib.Path('release').exists(): time.sleep(0.01)\")"]


if __name__ == '__main__': unittest.main()
