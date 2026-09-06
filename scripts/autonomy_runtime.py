"""POSIX lead-group bound and persistent quarantine for unverified shutdowns."""
import fcntl
import json
import os
import signal
import subprocess
from pathlib import Path
from contextlib import contextmanager
from autonomy_state import Blocked


@contextmanager
def run_lock(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise Blocked('another run holds the lock') from exc
        yield fd
    finally:
        # Close, do NOT unlink/unlock: a live child inherits the lock on supervisor crash.
        os.close(fd)


def unresolved_guard(location):
    """Presence alone blocks, including malformed markers and dangling symlinks."""
    marker = Path(location) / 'unresolved-process.json'
    try:
        marker.lstat()
    except FileNotFoundError:
        return None
    return {'wakeAgent': False, 'reason': 'unresolved prior processes; operator reconciliation required',
            'quarantine': str(marker)}


def _sync_directory(location):
    fd = os.open(location, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def clear_after_success(location, attempt, *, returncode, verified_success):
    """Caller holds run.lock and has checked this attempt's live-success ledger.

    Zero CLI exit plus verified live completion is our normal-shutdown contract,
    not a process-tree ownership receipt. Abnormal runs require an operator.
    """
    if returncode != 0 or verified_success is not True:
        raise Blocked('unresolved processes: verified success and zero exit required')
    marker = Path(location) / 'unresolved-process.json'
    try:
        fd = os.open(marker, os.O_RDONLY | os.O_NOFOLLOW)
    except FileNotFoundError:
        return  # A non-process injected runner may not have created a marker.
    with os.fdopen(fd) as receipt:
        data = json.load(receipt)
    if data != {'supervisor_pid': os.getpid(), 'attempt': str(attempt)}:
        raise Blocked('unresolved processes: marker does not belong to this supervisor attempt')
    marker.unlink()
    _sync_directory(location)


def bounded_run(command, cwd, env, log, lock_fd, seconds=2400):
    location = Path(log).parent
    decision = unresolved_guard(location)
    if decision:
        raise Blocked(decision['reason'])
    # Persist BEFORE launch. Never remove in finally: SIGKILL cannot run cleanup,
    # and ordinary Hermes terminal tools start new sessions without the lock FD.
    marker = location / 'unresolved-process.json'
    try:
        fd = os.open(marker, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    except FileExistsError as exc:
        raise Blocked('unresolved prior processes; operator reconciliation required') from exc
    with os.fdopen(fd, 'w') as receipt:
        json.dump({'supervisor_pid': os.getpid(), 'attempt': env.get('LWL_ATTEMPT')}, receipt)
        receipt.flush()
        os.fsync(receipt.fileno())
    _sync_directory(location)
    with open(log, 'a') as output:
        child = subprocess.Popen(command, cwd=cwd, env=env, stdout=output, stderr=subprocess.STDOUT,
                                 start_new_session=True, pass_fds=(lock_fd,))
        def terminate(signum=None, frame=None):
            try:
                os.killpg(child.pid, signal.SIGTERM)
                child.wait(timeout=2)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL)
                child.wait(timeout=3)
            except ProcessLookupError:
                pass
            if signum is not None:
                raise Blocked('supervisor interrupted')
        old = {s: signal.signal(s, terminate) for s in (signal.SIGTERM, signal.SIGINT)}
        try:
            return child.wait(timeout=seconds)
        except subprocess.TimeoutExpired as exc:
            terminate()
            raise Blocked('hard wall-clock budget exhausted') from exc
        finally:
            # Best effort for this group only; separate ordinary tool sessions survive.
            try:
                os.killpg(child.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            for sig, handler in old.items():
                signal.signal(sig, handler)
