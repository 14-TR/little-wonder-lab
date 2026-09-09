"""Bounded fresh CLI roles for a one-shot lead (no async callback consumer)."""
import json
import math
import os
import re
import signal
import stat
import subprocess
import sys
import time
from pathlib import Path
from autonomy_state import Blocked


REPORT_BYTES = 12000
LOG_BYTES = 1024 * 1024
EXPORT_BYTES = 16 * 1024 * 1024


def read_artifact(path, maximum, deadline):
    """Read only a bounded regular local file, never wait for a FIFO writer.

    Check both the path and opened descriptor: a path check alone races replacement.
    O_NONBLOCK/O_NOFOLLOW guard the open; fstat and capped reads guard its payload.
    Like the supervisor, this is not a sandbox against a stalled kernel/filesystem.
    """
    if time.monotonic() >= deadline:
        raise Blocked('role deadline exhausted before artifact read')
    try:
        before = path.lstat()
        if not stat.S_ISREG(before.st_mode):
            raise Blocked(f'role artifact must be a regular file: {path.name}')
        fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
        try:
            opened = os.fstat(fd)
            if (not stat.S_ISREG(opened.st_mode) or
                    (before.st_dev, before.st_ino) != (opened.st_dev, opened.st_ino)):
                raise Blocked(f'role artifact changed or is not a regular file: {path.name}')
            if opened.st_size > maximum:
                raise Blocked(f'role artifact exceeds {maximum} bytes: {path.name}')
            data = bytearray()
            while True:
                if time.monotonic() >= deadline:
                    raise Blocked('role deadline exhausted during artifact read')
                chunk = os.read(fd, min(65536, maximum + 1 - len(data)))
                data.extend(chunk)
                if len(data) > maximum:
                    raise Blocked(f'role artifact exceeds {maximum} bytes: {path.name}')
                if not chunk:
                    break
            if time.monotonic() >= deadline:
                raise Blocked('role deadline exhausted during artifact read')
            return bytes(data)
        finally:
            os.close(fd)
    except OSError as exc:
        raise Blocked(f'role artifact regular-file read failed: {path.name}: {exc}') from exc


def validate_completion(session, session_id, raw, item, base, *, role="probe", lesson_id=None, sha=None):
    """Accept a closed matching session, paired tools, final marker AND full report."""
    try:
        if (session['id'] != session_id or not session['ended_at'] or
                session['end_reason'] != 'cli_close'):
            raise ValueError('session did not close normally')
        messages = session['messages']
        if (not messages or messages[-1].get('role') != 'assistant' or
                messages[-1].get('content', '').strip() != 'LWL_ROLE_COMPLETE' or
                messages[-1].get('tool_calls')):
            raise ValueError('missing final completion marker')
        calls, results = [], []
        for message in messages:
            for call in message.get('tool_calls') or []:
                function = call['function']
                if function['name'] == 'delegate_task':
                    raise ValueError('roles cannot delegate from a one-shot session')
                arguments = function.get('arguments') or '{}'
                arguments = json.loads(arguments) if isinstance(arguments, str) else arguments
                if function['name'] == 'terminal' and arguments.get('background'):
                    raise ValueError('background process has no completion owner')
                calls.append(call['id'])
            if message.get('role') == 'tool':
                results.append(message['tool_call_id'])
        if len(set(calls)) != len(calls) or sorted(calls) != sorted(results):
            raise ValueError('unmatched or duplicate tool calls/results')
        if len(raw) > REPORT_BYTES or len(raw.decode('utf-8').split()) > 1200:
            raise ValueError('report exceeds compact handoff limits')
        report = json.loads(raw)
        if (report.get('complete') is not True or report.get('item') != item or
                report.get('base') != base):
            raise ValueError('incomplete or stale handoff identity')
        validate_report(report, role, lesson_id=lesson_id, sha=sha)
        return report
    except (ValueError, KeyError, TypeError, AttributeError) as exc:
        raise Blocked('role completion rejected: ' + str(exc)) from exc


def validate_report(report, role, *, lesson_id=None, sha=None):
    """Shape/identity only: a completed blocked report is not a passing decision."""
    if role == 'probe':  # Internal transport smoke tests; never a routine spec role.
        return
    if lesson_id is not None and report.get('lesson_id') != lesson_id and not role.endswith('-reviewer'):
        raise ValueError('report lesson differs from checkpoint')
    if role.endswith('-reviewer'):
        expected_role = {'code-reviewer':'code', 'curriculum-reviewer':'curriculum'}[role]
        findings = ['security_concerns','logic_errors','curriculum_concerns']
        if (report.get('role') != expected_role or report.get('sha') != sha or
                type(report.get('passed')) is not bool or type(report.get('substantive')) is not bool or
                not isinstance(report.get('summary'), str) or not report['summary'].strip() or
                any(not isinstance(report.get(key), list) for key in findings + ['tests'])):
            raise ValueError('malformed or stale reviewer verdict')
        if report['passed'] and (any(report[key] for key in findings) or
                                 not report['tests'] or report['substantive'] is not True):
            raise ValueError('passing verdict contradicts findings or evidence')
        if not report['passed'] and not any(report[key] for key in findings):
            raise ValueError('failed review must explain its blocker')
        return
    if report.get('status') not in {'ready', 'blocked'} or not re.fullmatch(
            '[a-z0-9]+(?:-[a-z0-9]+)*', report.get('lesson_id', '')):
        raise ValueError('invalid role status or lesson identity')
    if role == 'planner':
        if not isinstance(report.get('risks'), list):
            raise ValueError('planner risks must be explicit')
        if report['status'] == 'blocked':
            if not report['risks']:
                raise ValueError('blocked planner needs a reason')
            return
        required = ['learning_objective','prerequisites','child_explanation','activity_safety',
                    'interaction','sources','allowed_files','acceptance_tests','roadmap_update',
                    'curriculum_update','substantive_rationale']
        if any(key not in report for key in required) or any(
                not isinstance(report[key], list) for key in
                ['prerequisites','sources','allowed_files','acceptance_tests']):
            raise ValueError('planner design fields missing or malformed')
        if any(not report[key] for key in required if key != 'prerequisites'):
            raise ValueError('ready planner lacks design or evidence')
    elif role == 'engineer':
        fields = ['changed_paths','red_green','tests','visual_checks','blockers']
        if any(not isinstance(report.get(key), list) for key in fields) or 'learning_changes' not in report:
            raise ValueError('engineer handoff fields missing or malformed')
        if report['status'] == 'blocked' and not report['blockers']:
            raise ValueError('blocked engineer needs a reason')
        if report['status'] == 'ready' and (report['blockers'] or
                any(not report[key] for key in fields[:-1]) or
                len(report['visual_checks']) < 2 or not report['learning_changes']):
            raise ValueError('ready engineer lacks tests, visual evidence or learning change')
    else:
        raise ValueError('unknown role')


def run_role(worktree, directory, role, item, base, context, *, seconds, cli=None,
             deadline_epoch=None, lesson_id=None, sha=None):
    """Caller owns the supervisor lock/quarantine. No retries; retain every artifact.

    This is normal CLI completion evidence, not an OS sandbox or proof against
    arbitrary detached shell commands. Abnormal exits retain canonical quarantine.
    """
    cli = cli or ['hermes', '--profile', 'default']
    started = time.time()
    if type(seconds) not in (int, float) or not math.isfinite(seconds) or seconds <= 0:
        raise Blocked('role time must be positive and finite')
    if deadline_epoch is not None:
        if type(deadline_epoch) not in (int, float) or not math.isfinite(deadline_epoch):
            raise Blocked('role deadline must be finite')
        seconds = min(seconds, deadline_epoch - started)
    if seconds <= 0:
        raise Blocked('role absolute deadline already exhausted')
    deadline = time.monotonic() + seconds
    directory.mkdir(mode=0o700)  # Exclusive: never overwrite an earlier attempt.
    report_path = directory / 'report.json'
    prompt = (f'Finite fresh {role} role. No delegation or background/detached work. '
              'No commits, remote writes, state/cron/config/skills/memory edits. '
              f'Every terminal workdir must be {worktree}; every file path absolute. '
              f'Dispatch deadline epoch {started + seconds}. All work, QA, compact report and final response '
              'must fit this deadline; leave 60 seconds for startup/export/return. '
              f'REPORT_PATH={report_path}\n'
              f'Exact item={item}; base={base}; lesson_id={lesson_id}; sha={sha}. Save the complete role JSON (including '
              'complete:true, item and base) at REPORT_PATH, at most 1200 words / 12000 UTF-8 bytes. '
              'Use complete:true for an honest final blocked report too, never to disguise partial work. '
              'Then return ONLY LWL_ROLE_COMPLETE, without markdown. A final marker without the '
              'full correct artifact does not pass. Do not invent session IDs.\n\n' + context)
    (directory / 'prompt.md').write_text(prompt)
    command = cli + ['chat', '--oneshot', '-Q', '--pass-session-id', '--provider', 'openai-codex',
                     '--model', 'gpt-6-astra', '--max-turns', '35', '--run-budget', str(max(1, seconds-60)),
                     '--in', str(worktree), '--toolsets', 'terminal,file,web,skills,vision',
                     '--query-file', str(directory / 'prompt.md')]
    (directory / 'started.json').write_text(json.dumps({'role':role, 'item':item, 'base':base,
        'started_at':started, 'deadline':started+seconds, 'command':command}) + '\n')
    env = dict(os.environ, TERMINAL_CWD=str(worktree))
    # Roles cannot call supervised mutation helpers on behalf of the release lead.
    env.pop('LWL_ATTEMPT', None)
    code = run_process(command, worktree, env, directory, '', deadline)
    if code != 0:
        raise Blocked(f'role CLI failed ({code}); preserve artifacts and reconcile quarantine')
    # Six hex characters are emitted by the supported fresh CLI session creator.
    # Inspect every ID line before export (which also accepts prefixes); no repair.
    id_lines = [line for line in read_artifact(directory/'stderr.txt', LOG_BYTES, deadline).decode('utf-8').splitlines()
                if line.startswith('session_id:')]
    if len(id_lines) != 1 or not re.fullmatch(
            r'session_id: [0-9]{8}_[0-9]{6}_[0-9a-f]{6}', id_lines[0]):
        raise Blocked('missing exact runtime session ID')
    ids = [id_lines[0].removeprefix('session_id: ')]
    if read_artifact(directory/'stdout.txt', LOG_BYTES, deadline).decode('utf-8').strip() != 'LWL_ROLE_COMPLETE':
        raise Blocked('missing exact runtime session ID or final marker')
    remaining = deadline-time.monotonic()
    if remaining <= 0:
        raise Blocked('role deadline exhausted before completion export')
    code = run_process(cli + ['sessions','export','--session-id',ids[0],'--redact',
                              '--format','jsonl',str(directory/'session.jsonl')],
                       worktree, env, directory, 'export-', min(deadline, time.monotonic()+30))
    if code != 0 or time.monotonic() > deadline:
        raise Blocked('role completion export failed or exceeded deadline')
    sessions = [json.loads(line) for line in read_artifact(
        directory/'session.jsonl', EXPORT_BYTES, deadline).decode('utf-8').splitlines() if line]
    if len(sessions) != 1:
        raise Blocked('ambiguous session export or report path')
    report = validate_completion(sessions[0], ids[0], read_artifact(report_path, REPORT_BYTES, deadline), item, base,
                                 role=role, lesson_id=lesson_id, sha=sha)
    if time.monotonic() > deadline:
        raise Blocked('role deadline exhausted during artifact validation')
    result = {'status':'completed', 'agent_id':ids[0], 'role':role, 'item':item, 'base':base,
              'elapsed_seconds':time.time()-started, 'report_path':str(report_path), 'report':report,
              'session_export':str(directory/'session.jsonl')}
    (directory/'completed.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def run_process(command, worktree, env, directory, prefix, deadline):
    """Wait/reap each exact CLI group and retain exit evidence, including failure.

    Separate terminal sessions may survive; the supervisor quarantine still owns
    their reconciliation. Cleanup may use five seconds of containment, not work.
    """
    if time.monotonic() >= deadline:
        raise Blocked('role deadline exhausted before process launch')
    # Exclusive creation also rejects preexisting FIFO/symlink export logs before spawn.
    with (directory/(prefix+'stdout.txt')).open('x') as output, (directory/(prefix+'stderr.txt')).open('x') as error:
        child, old, reason = None, {}, 'exited'
        def interrupted(signum, frame):
            raise Blocked(f'role transport interrupted by signal {signum}; reconcile quarantine')
        try:
            # Own the child before any fallible receipt or signal-handler setup.
            child = subprocess.Popen(command, cwd=worktree, env=env, stdin=subprocess.DEVNULL,
                                     stdout=output, stderr=error, start_new_session=True)
            (directory/(prefix+'process.json')).write_text(json.dumps(
                {'pid':child.pid, 'started_at':time.time(), 'command':command})+'\n')
            for sig in (signal.SIGINT, signal.SIGTERM):
                old[sig] = signal.getsignal(sig)
                signal.signal(sig, interrupted)
            return child.wait(timeout=max(0.001,deadline-time.monotonic()))
        except subprocess.TimeoutExpired as exc:
            reason = 'deadline'
            raise Blocked('role deadline exhausted; preserve artifacts and reconcile quarantine') from exc
        except BaseException:
            reason = 'interrupted'
            raise
        finally:
            if child is not None:
                failure, cleanup_errors = sys.exc_info()[1], []
                def cleanup(action, *args, **kwargs):
                    try:
                        action(*args, **kwargs)
                    except BaseException as exc:
                        cleanup_errors.append(exc)
                def kill_group(sig):
                    try:
                        os.killpg(child.pid, sig)
                    except ProcessLookupError:
                        pass
                # A handler failure must not skip termination, reaping or receipts.
                for sig in old:
                    cleanup(signal.signal, sig, signal.SIG_IGN)
                cleanup(kill_group, signal.SIGTERM)
                try:
                    child.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    pass
                except BaseException as exc:
                    cleanup_errors.append(exc)
                cleanup(kill_group, signal.SIGKILL)
                cleanup(child.wait, timeout=3)
                cleanup(lambda: (directory/(prefix+'exit.json')).write_text(json.dumps(
                    {'pid':child.pid, 'returncode':child.returncode,
                     'ended_at':time.time(), 'reason':reason})+'\n'))
                for sig, handler in old.items():
                    cleanup(signal.signal, sig, handler)
                if cleanup_errors:
                    if failure is None:
                        raise cleanup_errors[0]
                    # Preserve the initiating exception even when storage is full.
                    if hasattr(failure, 'add_note'):
                        for exc in cleanup_errors:
                            failure.add_note(f'role cleanup also failed: {exc!r}')


ROLE_SECONDS = {'planner':360, 'engineer':540, 'code-reviewer':360, 'curriculum-reviewer':360}


def validate_spec(spec, root, pending, *, now):
    """Validate literal identity and finite time before any model process starts."""
    import math
    from autonomy_policy import sha40, item_id
    try:
        role = spec['role']
        maximum = ROLE_SECONDS[role]
        item, base = item_id(spec['item']), sha40(spec['base'])
        deadline = spec['deadline']
        if type(deadline) not in (int, float) or not math.isfinite(deadline):
            raise ValueError('deadline must be a finite epoch number')
        seconds = min(maximum, deadline - now)
        if seconds <= 60:
            raise ValueError('insufficient role time including transport reserve')
        if not isinstance(spec['context'], str) or not spec['context'].strip():
            raise ValueError('trusted role context required')
        if pending and (pending['item'] != item or pending['base'] != base):
            raise ValueError('role item/base differs from supervised checkpoint')
        if pending.get('lesson_id') and spec.get('lesson_id', pending['lesson_id']) != pending['lesson_id']:
            raise ValueError('role lesson differs from supervised checkpoint')
        expected = root if role == 'planner' else Path(pending['worktree'])
        if spec['worktree'] != str(expected) or not expected.is_absolute() or expected.resolve() != expected:
            raise ValueError('role worktree differs from supervised checkpoint')
        if role != 'planner' and (not pending.get('lesson_id') or
                                  spec['lesson_id'] != pending['lesson_id']):
            raise ValueError('role lesson differs from supervised checkpoint')
        if role.endswith('-reviewer') and (sha40(spec['sha']) != pending['sha'] or
                                           pending['stage'] not in {'engineered', 'reviewed'}):
            raise ValueError('review head/stage differs from supervised checkpoint')
        return expected, seconds
    except (KeyError, TypeError, ValueError) as exc:
        raise Blocked('role spec rejected: ' + str(exc)) from exc


def main(spec_path, root):
    """Only the active lead may launch routine roles; no owner/quota bypass flag."""
    import uuid
    from autonomy import active, state_dir
    from autonomy_state import Store
    location = state_dir(root)
    store = Store(location/'state.sqlite3')
    try:
        attempt = active(store)
        if not spec_path.is_absolute() or spec_path.resolve().parent != location:
            raise Blocked('role spec must be a canonical private state file')
        spec = json.loads(spec_path.read_text())
        pending = store.pending()
        expected, seconds = validate_spec(spec, root, pending, now=time.time())
        role, item, base = spec['role'], spec['item'], spec['base']
        from autonomy_release import command
        bound_head = base if role == 'planner' else spec.get('sha') if role.endswith('-reviewer') else None
        if bound_head and command(['git','rev-parse','HEAD'], expected) != bound_head:
            raise Blocked('role repository HEAD differs from exact spec')
        context = (root/'automation/roles'/f'{role}.md').read_text()+'\n\n'+spec['context']
        directory = location/f'role-{attempt}-{role}-{uuid.uuid4().hex[:8]}'
        result = run_role(expected, directory, role, item, base, context, seconds=seconds,
                          deadline_epoch=spec['deadline'], lesson_id=pending.get('lesson_id') or spec.get('lesson_id'),
                          sha=spec.get('sha') if role.endswith('-reviewer') else None)
        remaining = spec['deadline'] - time.time()
        if remaining <= 0:
            raise Blocked('role deadline exhausted before final checkpoint validation')
        if store.pending() != pending or (bound_head and
                command(['git','rev-parse','HEAD'], expected, timeout=min(60,remaining)) != bound_head):
            raise Blocked('role checkpoint or repository HEAD changed during handoff')
        if time.time() > spec['deadline']:
            raise Blocked('role deadline exhausted during final checkpoint validation')
        print(json.dumps(result))
    finally:
        store.close()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--file', type=Path, required=True)
    args = parser.parse_args()
    main(args.file, Path(__file__).resolve().parents[1])
