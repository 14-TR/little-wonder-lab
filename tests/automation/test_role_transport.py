"""Finite role completion is an exit + full artifact, never an async handle."""
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from autonomy_state import Blocked


class RoleTransportTests(unittest.TestCase):
    def setUp(self):
        import os
        from unittest.mock import patch
        env = patch.dict(os.environ, {'LWL_LEAD_DEADLINE':'3100'})
        env.start()
        self.addCleanup(env.stop)

    def transport(self):
        path = ROOT / 'scripts/run_role.py'
        self.assertTrue(path.is_file(), 'one-shot leads need a synchronous role transport')
        spec = importlib.util.spec_from_file_location('role_transport', path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_completed_export_and_compact_artifact_required_together(self):
        m = self.transport()
        session = {'id': 'observed-session', 'ended_at': 10, 'end_reason': 'cli_close',
                   'messages': [{'role': 'assistant', 'tool_calls': [{'id': 't1', 'function': {'name': 'read_file', 'arguments': '{}'}}]},
                                {'role': 'tool', 'tool_call_id': 't1', 'content': '{}'},
                                {'role': 'assistant', 'content': 'LWL_ROLE_COMPLETE'}]}
        report = {'complete': True, 'status': 'ready', 'item': 'request-2', 'base': 'a' * 40}
        raw = json.dumps(report).encode()
        self.assertEqual(m.validate_completion(session, 'observed-session', raw, 'request-2', 'a' * 40), report)
        for change in ({'ended_at': None}, {'end_reason': 'interrupted'}, {'id': 'other'},
                       {'messages': session['messages'][:1] + session['messages'][2:]},
                       {'messages': session['messages'][:-1] + [{'role':'assistant','content':'max iterations'}]}):
            with self.subTest(change=change), self.assertRaises(Blocked):
                m.validate_completion({**session, **change}, 'observed-session', raw, 'request-2', 'a' * 40)
        for change in ({'complete': False}, {'base': 'b'*40}, {'item':'other'}, {'summary':'x'*12001}):
            with self.subTest(change=change), self.assertRaises(Blocked):
                m.validate_completion(session, 'observed-session', json.dumps({**report, **change}).encode(), 'request-2', 'a'*40)
        child = {'role':'assistant','tool_calls':[{'id':'t2','function':{'name':'delegate_task','arguments':'{}'}}]}
        with self.assertRaises(Blocked):
            m.validate_completion({**session,'messages':[child,{'role':'tool','tool_call_id':'t2'},session['messages'][-1]]},'observed-session',raw,'request-2','a'*40)

    def test_role_instructions_have_one_finite_completion_contract(self):
        lead = (ROOT/'automation/roles/lead.md').read_text()
        runbook = (ROOT/'docs/AUTONOMY.md').read_text()
        agents = (ROOT/'AGENTS.md').read_text()
        self.assertIn('fresh CLI role sessions', agents)
        self.assertIn('run_role.py', runbook)
        for obsolete in ('For every delegation', 'delegate_task(tasks=',
                         'delegate_task` engineer', 'runtime subagent_id'):
            self.assertNotIn(obsolete, lead)
        for role in ('planner', 'engineer', 'code-reviewer', 'curriculum-reviewer'):
            text = (ROOT/'automation/roles'/f'{role}.md').read_text()
            self.assertIn('REPORT_PATH', text)
            self.assertIn('LWL_ROLE_COMPLETE', text)
            self.assertNotIn('Return ONLY JSON', text)
            self.assertNotIn('brief callback', text)

    def test_engineer_reserves_handoff_inside_existing_dispatch_budget(self):
        m = self.transport()
        self.assertEqual(m.ROLE_SECONDS['engineer'], 390)
        engineer = (ROOT/'automation/roles/engineer.md').read_text()
        self.assertIn('390 seconds from dispatch', engineer)
        self.assertIn('1200 words / 12000 UTF-8 bytes', engineer)
        self.assertIn('Freeze implementation by 210 seconds', engineer)
        self.assertIn('complete the report by 300 seconds', engineer)
        self.assertNotIn('12 minutes', engineer)

    def test_engineer_rejects_old_window_before_launch(self):
        m = self.transport()
        pending = {'item':'request-2', 'base':'a'*40, 'worktree':str(ROOT),
                   'lesson_id':'pattern-path', 'stage':'planned'}
        spec = {'role':'engineer', 'item':'request-2', 'base':'a'*40,
                'worktree':str(ROOT), 'lesson_id':'pattern-path',
                'deadline':1540, 'context':'offline admission regression'}
        # Real admission, not arithmetic reconstructed from prompt wording:
        # the old 540-second role cannot fit the observed 420-second executor.
        with self.assertRaisesRegex(Blocked, 'window'):
            m.validate_spec(spec, ROOT, pending, now=1000)
        self.assertEqual(m.validate_spec({**spec, 'deadline':1390}, ROOT, pending, now=1000),
                         (ROOT, 390))
        with self.assertRaisesRegex(Blocked, 'window'):
            m.validate_spec({**spec, 'deadline':1390.001}, ROOT, pending, now=1000)

    def test_actual_downstream_admission_after_startup_and_handoff(self):
        import os
        from unittest.mock import patch
        m = self.transport()
        pending = {'item':'request-2', 'base':'a'*40, 'worktree':str(ROOT),
                   'lesson_id':'pattern-path', 'stage':'planned'}
        spec = {'role':'engineer', 'item':'request-2', 'base':'a'*40,
                'worktree':str(ROOT), 'lesson_id':'pattern-path',
                'context':'offline admission regression'}
        # Supervisor starts at 1000. 65s startup/selection + 360s planner;
        # 55s handoff fits exactly, but an extra millisecond spends a reserve.
        with patch.dict(os.environ, {'LWL_LEAD_DEADLINE':'3100'}):
            for now in (1425, 1480):
                self.assertEqual(m.validate_spec({**spec,'deadline':now+390}, ROOT, pending, now=now),
                                 (ROOT,390))
            with self.assertRaisesRegex(Blocked, 'downstream'):
                m.validate_spec({**spec,'deadline':1870.001}, ROOT, pending, now=1480.001)

    def test_all_roles_keep_reserves_and_require_supervisor_clock(self):
        import os
        from unittest.mock import patch
        m = self.transport()
        pending = {'item':'request-2','base':'a'*40,'sha':'b'*40,'worktree':str(ROOT),
                   'lesson_id':'pattern-path','stage':'engineered'}
        spec = {'item':'request-2','base':'a'*40,'sha':'b'*40,'worktree':str(ROOT),
                'lesson_id':'pattern-path','context':'offline admission boundaries'}
        for role, now in (('planner',1065), ('planner',1120), ('engineer',1480),
                          ('code-reviewer',2200), ('curriculum-reviewer',2200)):
            with self.subTest(role=role,now=now):
                window=m.ROLE_SECONDS[role]
                value={**spec,'role':role,'deadline':now+window}
                self.assertEqual(m.validate_spec(value,ROOT,pending,now=now),(ROOT,window))
                if now != 1065:
                    with self.assertRaisesRegex(Blocked,'downstream'):
                        m.validate_spec(value,ROOT,pending,now=now+0.001)
        value={**spec,'role':'engineer','deadline':1390}
        for clock in (None,'nan','inf','not-an-epoch','1000'):
            with self.subTest(clock=clock), patch.dict(os.environ, {}, clear=True):
                if clock is not None:
                    os.environ['LWL_LEAD_DEADLINE']=clock
                with self.assertRaises(Blocked):
                    m.validate_spec(value,ROOT,pending,now=1000)

    def test_entrypoint_requires_supervision_before_reading_a_spec(self):
        m = self.transport()
        self.assertTrue(hasattr(m, 'main'), 'supervised role entrypoint required')
        import os
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as tmp:
            with patch('autonomy.state_dir', return_value=Path(tmp)), patch.dict(os.environ, {}, clear=True):
                with self.assertRaisesRegex(Blocked, 'supervised'):
                    m.main(Path(tmp)/'nonexistent.json', ROOT)

    def test_spec_binds_finite_deadline_checkpoint_and_exact_identifiers(self):
        m = self.transport()
        self.assertTrue(hasattr(m, 'validate_spec'), 'validate before launching any role')
        pending = {'item':'request-2', 'base':'a'*40, 'worktree':str(ROOT),
                   'lesson_id':'pattern-path', 'sha':'b'*40, 'stage':'engineered'}
        spec = {'role':'code-reviewer', 'item':'request-2', 'base':'a'*40,
                'worktree':str(ROOT), 'lesson_id':'pattern-path', 'sha':'b'*40,
                'deadline':1360, 'context':'trusted acceptance criteria'}
        self.assertEqual(m.validate_spec(spec, ROOT, pending, now=1000), (ROOT, 360))
        for change in ({'deadline':float('nan')}, {'deadline':float('inf')},
                       {'deadline':True}, {'deadline':'1360'}, {'deadline':1060},
                       {'item':'request-3'}, {'base':'c'*40}, {'base':'A'*40},
                       {'worktree':str(ROOT/'..')}, {'lesson_id':'other'},
                       {'sha':'c'*40}, {'sha':'B'*40}, {'role':'probe'}):
            with self.subTest(change=change), self.assertRaises(Blocked):
                m.validate_spec({**spec, **change}, ROOT, pending, now=1000)
        with self.assertRaises(Blocked):
            m.validate_spec(spec, ROOT, {}, now=1000)
        planner = {**spec, 'role':'planner', 'base':'a'*40}
        self.assertEqual(m.validate_spec(planner, ROOT, {}, now=1000), (ROOT,360))
        for change in ({'item':'request-3'},{'lesson_id':'wrong'}):
            with self.subTest(change=change), self.assertRaises(Blocked):
                m.validate_spec({**planner,**change}, ROOT, pending, now=1000)
        self.assertEqual(m.validate_spec({**spec,'deadline':1061}, ROOT, pending, now=1000), (ROOT,61))

    def test_entrypoint_validates_before_launch_and_keeps_absolute_deadline(self):
        import os
        import subprocess
        import time
        from unittest.mock import patch
        from autonomy_state import Store
        m = self.transport()
        head = subprocess.check_output(['git','rev-parse','HEAD'], cwd=ROOT, text=True).strip()
        with tempfile.TemporaryDirectory() as tmp:
            location = Path(tmp).resolve()
            store = Store(location/'state.sqlite3')
            attempt = store.begin('2000-01-01')  # Isolated fixture ledger, never canonical state.
            pending = {'item':'request-2','base':head,'sha':head,'worktree':str(ROOT),
                       'lesson_id':'pattern-path','stage':'engineered'}
            store.checkpoint(attempt, pending)
            spec = {'role':'code-reviewer','item':'request-2','base':head,'sha':head,
                    'worktree':str(ROOT),'lesson_id':'pattern-path',
                    'deadline':time.time()+360,'context':'read-only fixture'}
            spec_path = location/'spec.json'
            with patch('autonomy.state_dir', return_value=location), \
                 patch.dict(os.environ, {'LWL_ATTEMPT':str(attempt), 'LWL_LEAD_DEADLINE':str(time.time()+2100)}), \
                 patch.object(m, 'run_role', return_value={'status':'fixture'}) as launch:
                for change in ({'item':'request-3'}, {'base':'c'*40}, {'sha':'d'*40}):
                    spec_path.write_text(json.dumps({**spec, **change}))
                    with self.subTest(change=change), self.assertRaises(Blocked):
                        m.main(spec_path, ROOT)
                    launch.assert_not_called()
                spec_path.write_text(json.dumps(spec))
                m.main(spec_path, ROOT)
                self.assertEqual(launch.call_args.kwargs['deadline_epoch'], spec['deadline'])
                self.assertEqual(launch.call_args.kwargs['sha'], head)
                self.assertEqual(launch.call_args.kwargs['lesson_id'], 'pattern-path')
                spec_path.write_text(json.dumps({**spec,'deadline':1360}))
                with patch.object(m.time,'time',return_value=1000) as clock:
                    def late_return(*args, **kwargs):
                        clock.return_value = 1361
                        return {'status':'fixture'}
                    launch.side_effect = late_return
                    with self.assertRaisesRegex(Blocked, 'deadline'):
                        m.main(spec_path, ROOT)
            store.close()

    def test_dispatch_rechecks_reserves_after_git_preflight(self):
        import os
        from unittest.mock import patch
        from autonomy_state import Store
        import autonomy_release
        m = self.transport()
        command = autonomy_release.command
        head = command(['git','rev-parse','HEAD'], ROOT)
        with tempfile.TemporaryDirectory() as tmp:
            location = Path(tmp).resolve()
            store = Store(location/'state.sqlite3')
            attempt = store.begin('2000-01-01')  # Isolated fixture only.
            store.checkpoint(attempt, {'item':'request-2','base':head,'sha':head,
                'worktree':str(ROOT),'lesson_id':'pattern-path','stage':'engineered'})
            spec = {'role':'code-reviewer','item':'request-2','base':head,'sha':head,
                    'worktree':str(ROOT),'lesson_id':'pattern-path','deadline':1360,
                    'context':'read-only fixture'}
            spec_path = location/'spec.json'
            spec_path.write_text(json.dumps(spec))
            try:
                with patch('autonomy.state_dir',return_value=location), \
                     patch.dict(os.environ,{'LWL_ATTEMPT':str(attempt),'LWL_LEAD_DEADLINE':'1900'}), \
                     patch.object(m.time,'time',return_value=1000) as clock, \
                     patch.object(m,'run_role',return_value={'status':'fixture'}) as launch:
                    def slow_git(*args, **kwargs):
                        result = command(*args, **kwargs)  # Actual repository identity read.
                        clock.return_value = 1000.001
                        return result
                    with patch.object(autonomy_release,'command',side_effect=slow_git):
                        with self.assertRaisesRegex(Blocked,'downstream'):
                            m.main(spec_path, ROOT)
                    launch.assert_not_called()
            finally:
                store.close()

    def resumption_fixture(self):
        """Real isolated Git/SQLite; no canonical state or model process."""
        import subprocess
        from autonomy_state import Store
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name).resolve()/'repo'
        root.mkdir()
        def git(*args, cwd=root):
            return subprocess.check_output(['git', *args], cwd=cwd, text=True,
                                           stderr=subprocess.PIPE, timeout=10).strip()
        git('init', '-q', '-b', 'main')
        (root/'.gitignore').write_text('/.autonomy-worktrees/\n')
        (root/'lesson.txt').write_text('original lesson\n')
        (root/'automation/roles').mkdir(parents=True)
        (root/'automation/roles/planner.md').write_text('Read-only fixture planner')
        git('add', '.')
        git('-c', 'user.name=Test', '-c', 'user.email=test@example.invalid',
            'commit', '-qm', 'fixture baseline')
        old = git('rev-parse', 'HEAD')
        worktree = root/'.autonomy-worktrees/request-42'
        git('worktree', 'add', '-b', 'auto/request-42', str(worktree))
        (worktree/'lesson.txt').write_text('preserved unfinished lesson\n')
        (root/'maintenance.txt').write_text('maintenance only\n')
        git('add', 'maintenance.txt')
        git('-c', 'user.name=Test', '-c', 'user.email=test@example.invalid',
            'commit', '-qm', 'fixture maintenance')
        current = git('rev-parse', 'HEAD')
        location = root/'.git/autonomy'
        store = Store(location/'state.sqlite3')
        self.addCleanup(store.close)
        attempt = store.begin('2000-01-01')
        prior_report = location/'original-plan.json'
        prior_report.write_text(json.dumps({'base':old, 'original':'immutable fixture'}))
        pending = {'item':'request-42', 'base':old, 'worktree':str(worktree),
                   'branch':'auto/request-42', 'lesson_id':'fixture-lesson',
                   'stage':'planned', 'plan':str(prior_report)}
        store.checkpoint(attempt, pending)
        spec = {'role':'planner', 'item':'request-42', 'base':current,
                'checkpoint_base':old, 'worktree':str(root), 'lesson_id':'fixture-lesson',
                'deadline':1360, 'context':'fresh-base delta; original plan remains historical'}
        return self.transport(), root, location, store, attempt, pending, spec, git

    def test_planner_current_base_preserves_original_checkpoint_and_dirty_work(self):
        import os
        from unittest.mock import patch
        m, root, location, store, attempt, pending, spec, git = self.resumption_fixture()
        prior = Path(pending['plan']).read_bytes()
        rows = store.db.execute('SELECT * FROM checkpoint').fetchall()
        worktree = Path(pending['worktree'])
        dirty = (worktree/'lesson.txt').read_bytes()
        path = location/'spec.json'
        path.write_text(json.dumps(spec))
        with patch.dict(os.environ, {'LWL_ATTEMPT':str(attempt)}), \
             patch.object(m.time, 'time', return_value=1000), \
             patch.object(m, 'run_role', return_value={'status':'offline fixture'}) as launch:
            try:
                m.main(path, root)
            except Blocked as exc:
                self.fail('fresh-base planner was blocked before handoff: '+str(exc))
            self.assertEqual(launch.call_args.args[4], spec['base'])
            self.assertEqual(launch.call_args.kwargs['deadline_epoch'], 1360)
        self.assertEqual(store.db.execute('SELECT * FROM checkpoint').fetchall(), rows)
        self.assertEqual(store.pending(), pending)
        self.assertEqual(Path(pending['plan']).read_bytes(), prior)
        self.assertEqual((worktree/'lesson.txt').read_bytes(), dirty)
        self.assertEqual(git('rev-parse', 'HEAD', cwd=worktree), pending['base'])
        self.assertEqual(store.db.execute('SELECT * FROM releases').fetchall(), [])
        self.assertEqual(store.db.execute('SELECT * FROM attempts').fetchall(),
                         [(attempt, '2000-01-01', 'running')])

    def test_resumed_planner_rejects_nonancestor_checkpoint_base(self):
        import os
        from unittest.mock import patch
        m, root, location, store, attempt, pending, spec, git = self.resumption_fixture()
        sibling = git('-c', 'user.name=Test', '-c', 'user.email=test@example.invalid',
                      'commit-tree', git('rev-parse', 'HEAD^{tree}'), '-p', pending['base'],
                      '-m', 'divergent fixture')
        pending = {**pending, 'base':sibling}
        store.checkpoint(attempt, pending)
        path = location/'spec.json'
        path.write_text(json.dumps({**spec, 'checkpoint_base':sibling}))
        with patch.dict(os.environ, {'LWL_ATTEMPT':str(attempt)}), \
             patch.object(m.time, 'time', return_value=1000), \
             patch.object(m, 'run_role', return_value={'status':'offline fixture'}) as launch:
            with self.assertRaisesRegex(Blocked, 'ancestor'):
                m.main(path, root)
            launch.assert_not_called()
        self.assertEqual(store.pending(), pending)

    def test_checkpoint_base_is_literal_and_planner_only(self):
        m = self.transport()
        pending = {'item':'request-42', 'base':'a'*40, 'worktree':str(ROOT),
                   'lesson_id':'fixture-lesson', 'stage':'planned', 'sha':'c'*40}
        spec = {'role':'planner', 'item':'request-42', 'base':'b'*40,
                'checkpoint_base':'a'*40, 'worktree':str(ROOT),
                'lesson_id':'fixture-lesson', 'deadline':1360, 'context':'offline fixture'}
        self.assertEqual(m.validate_spec(spec, ROOT, pending, now=1000), (ROOT,360))
        for change in ({'checkpoint_base':'A'*40}, {'checkpoint_base':'a'*39},
                       {'checkpoint_base':'a'*40+' '}, {'checkpoint_base':'b'*40},
                       {'item':'request-43'}, {'lesson_id':'other'},
                       {'role':'engineer'}, {'role':'code-reviewer', 'sha':'c'*40},
                       {'role':'curriculum-reviewer', 'sha':'c'*40}):
            with self.subTest(change=change), self.assertRaises(Blocked):
                m.validate_spec({**spec, **change}, ROOT, pending, now=1000)
        with self.assertRaises(Blocked):
            m.validate_spec({k:v for k,v in spec.items() if k != 'checkpoint_base'},
                            ROOT, pending, now=1000)
        for stage in ('merged', 'live', 'unknown', None):
            with self.subTest(stage=stage), self.assertRaises(Blocked):
                m.validate_spec(spec, ROOT, {**pending, 'stage':stage}, now=1000)
        with self.assertRaises(Blocked):
            m.validate_spec(spec, ROOT, {}, now=1000)

    def test_resumed_planner_still_requires_exact_current_head(self):
        import os
        from unittest.mock import patch
        m, root, location, store, attempt, pending, spec, git = self.resumption_fixture()
        path = location/'spec.json'
        path.write_text(json.dumps({**spec, 'base':pending['base']}))
        with patch.dict(os.environ, {'LWL_ATTEMPT':str(attempt)}), \
             patch.object(m.time, 'time', return_value=1000), \
             patch.object(m, 'run_role') as launch:
            with self.assertRaisesRegex(Blocked, 'HEAD'):
                m.main(path, root)
            launch.assert_not_called()
        self.assertEqual(store.pending(), pending)

    def test_resumed_planner_ancestry_preflight_counts_against_reserve(self):
        import os
        from unittest.mock import patch
        import autonomy_release
        m, root, location, store, attempt, pending, spec, git = self.resumption_fixture()
        command = autonomy_release.command
        path = location/'spec.json'
        path.write_text(json.dumps(spec))
        for delay, admitted in ((120, True), (120.001, False)):
            with self.subTest(delay=delay), \
                 patch.dict(os.environ, {'LWL_ATTEMPT':str(attempt)}), \
                 patch.object(m.time, 'time', return_value=1000) as clock, \
                 patch.object(m, 'run_role', return_value={'status':'offline fixture'}) as launch:
                def slow_ancestry(argv, *args, **kwargs):
                    result = command(argv, *args, **kwargs)
                    if argv[1] == 'merge-base':
                        clock.return_value += delay
                    return result
                with patch.object(autonomy_release, 'command', side_effect=slow_ancestry):
                    if admitted:
                        m.main(path, root)
                        self.assertEqual(launch.call_args.kwargs['deadline_epoch'], 1360)
                    else:
                        with self.assertRaisesRegex(Blocked, 'downstream'):
                            m.main(path, root)
                        launch.assert_not_called()
                self.assertEqual(store.pending(), pending)

    def test_resumed_planner_rejects_checkpoint_change_during_handoff(self):
        import os
        from unittest.mock import patch
        m, root, location, store, attempt, pending, spec, git = self.resumption_fixture()
        path = location/'spec.json'
        path.write_text(json.dumps(spec))
        changed = {**pending, 'base':spec['base']}
        def concurrent_change(*args, **kwargs):
            store.checkpoint(attempt, changed)  # Isolated conflicting writer fixture.
            return {'status':'offline fixture'}
        with patch.dict(os.environ, {'LWL_ATTEMPT':str(attempt)}), \
             patch.object(m.time, 'time', return_value=1000), \
             patch.object(m, 'run_role', side_effect=concurrent_change):
            with self.assertRaisesRegex(Blocked, 'checkpoint'):
                m.main(path, root)
        self.assertEqual(store.pending(), changed, 'do not silently undo another writer')

    def test_existing_checkpoint_command_advances_after_dirty_fast_forward(self):
        import os
        from unittest.mock import patch
        import autonomy
        m, root, location, store, attempt, pending, spec, git = self.resumption_fixture()
        worktree = Path(pending['worktree'])
        dirty = (worktree/'lesson.txt').read_bytes()
        prior_report = Path(pending['plan']).read_bytes()
        archive = location/'prior-checkpoint.json'
        with archive.open('x') as stream:
            json.dump(pending, stream)
        archive_bytes = archive.read_bytes()
        # Disjoint maintenance can fast-forward the SAME dirty branch; no stash,
        # reset, lesson commit, recreation or history rewrite is needed.
        git('merge', '--ff-only', spec['base'], cwd=worktree)
        self.assertEqual((worktree/'lesson.txt').read_bytes(), dirty)
        self.assertEqual(git('rev-parse', 'HEAD', cwd=worktree), spec['base'])
        self.assertEqual(git('branch', '--show-current', cwd=worktree), pending['branch'])
        new = {**pending, 'base':spec['base'], 'plan':str(location/'fresh-plan-fixture.json'),
               'prior_checkpoint_file':str(archive)}
        path = location/'next-checkpoint.json'
        path.write_text(json.dumps(new))
        with patch.dict(os.environ, {'LWL_ATTEMPT':str(attempt)}):
            autonomy.main(['checkpoint', '--file', str(path)], root=root)
        self.assertEqual(store.pending(), new)
        engineer = {'role':'engineer', 'item':new['item'], 'base':new['base'],
                    'worktree':str(worktree), 'lesson_id':new['lesson_id'],
                    'deadline':1390, 'context':'offline continuation fixture'}
        self.assertEqual(m.validate_spec(engineer, root, new, now=1000), (worktree,390))
        with self.assertRaises(Blocked):
            m.validate_spec({**engineer, 'base':pending['base']}, root, new, now=1000)
        self.assertEqual(archive.read_bytes(), archive_bytes)
        self.assertEqual(json.loads(archive_bytes), pending)
        self.assertEqual(Path(pending['plan']).read_bytes(), prior_report)
        self.assertEqual(store.db.execute('SELECT * FROM releases').fetchall(), [])
        self.assertEqual(store.db.execute('SELECT * FROM attempts').fetchall(),
                         [(attempt, '2000-01-01', 'running')])

    def fixture_cli(self, root):
        path = root/'cli.py'
        path.write_text('''import sys,time,json,pathlib,os
if 'export' in sys.argv:
    directory=pathlib.Path(sys.argv[-1]).parent
    context=(directory/'prompt.md').read_text()
    if 'SLOW_EXPORT' in context: time.sleep(10)
    if 'FAIL_EXPORT' in context: sys.exit(2)
    session_id=sys.argv[sys.argv.index('--session-id')+1]
    pathlib.Path(sys.argv[-1]).write_text(json.dumps({'id':session_id,'ended_at':10,'end_reason':'cli_close','messages':[{'role':'assistant','content':'LWL_ROLE_COMPLETE'}]}))
else:
    context=pathlib.Path(sys.argv[sys.argv.index('--query-file')+1]).read_text()
    report=pathlib.Path(context.split('REPORT_PATH=')[1].split('\\n')[0])
    report.write_text(json.dumps({'complete':True,'status':'blocked','item':'request-2','base':'a'*40,'lesson_id':'pattern-path','risks':['fixture only']}))
    if 'SLOW_CLI' in context: time.sleep(10)
    if 'NONZERO' in context: sys.exit(2)
    if 'SELF_SIGNAL' in context: os.kill(os.getpid(),15)
    identifier='20260908_154507_75fcb3'
    if 'UPPERCASE_ID' in context: identifier=identifier.upper()
    if 'EIGHT_HEX_ID' in context: identifier+='12'
    if 'TRAILING_ID' in context: identifier+=' '
    print('LWL_ROLE_COMPLETE')
    print('session_id: '+identifier,file=sys.stderr)
    if 'DUPLICATE_ID' in context: print('session_id: '+identifier,file=sys.stderr)
    if 'EXTRA_BAD_ID' in context: print('session_id: malformed',file=sys.stderr)
''')
        return [sys.executable,str(path)]

    def test_runtime_failures_save_exit_receipts_and_never_complete(self):
        import os
        import time
        m = self.transport()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cli = self.fixture_cli(root)
            for context in ('NONZERO', 'SELF_SIGNAL', 'SLOW_CLI', 'SLOW_EXPORT', 'FAIL_EXPORT',
                            'UPPERCASE_ID','EIGHT_HEX_ID','TRAILING_ID','DUPLICATE_ID','EXTRA_BAD_ID'):
                directory = root/context
                with self.subTest(context=context), self.assertRaises(Blocked):
                    m.run_role(root,directory,'planner','request-2','a'*40,context,
                               seconds=1 if context.startswith('SLOW') else 10,cli=cli)
                self.assertTrue((directory/'report.json').exists())
                self.assertFalse((directory/'completed.json').exists())
                self.assertTrue((directory/'exit.json').exists(), 'record actual CLI exit on every path')
                pid=json.loads((directory/'process.json').read_text())['pid']
                with self.assertRaises(ProcessLookupError):
                    os.kill(pid,0)
            for seconds in (0,-1,float('nan'),float('inf')):
                with self.subTest(seconds=seconds), self.assertRaises(Blocked):
                    m.run_role(root,root/'invalid','probe','request-2','a'*40,'',seconds=seconds,cli=cli)
                self.assertFalse((root/'invalid').exists())
            with self.assertRaises(Blocked):
                m.run_role(root,root/'expired','probe','request-2','a'*40,'',seconds=10,
                           deadline_epoch=time.time()-1,cli=cli)
            self.assertFalse((root/'expired').exists())

    def test_validation_time_is_inside_deadline_and_role_schema_is_checked(self):
        import time
        from unittest.mock import patch
        m = self.transport()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cli = self.fixture_cli(root)
            validate = m.validate_completion
            def slow_validation(*args, **kwargs):
                time.sleep(1)
                return validate(*args, **kwargs)
            with patch.object(m,'validate_completion',side_effect=slow_validation), self.assertRaises(Blocked):
                m.run_role(root,root/'late','probe','request-2','a'*40,'',seconds=0.6,cli=cli)
            self.assertFalse((root/'late/completed.json').exists())
            with self.assertRaises(Blocked):
                m.run_role(root,root/'wrong-role','engineer','request-2','a'*40,'',
                           seconds=10,lesson_id='pattern-path',cli=cli)
            self.assertFalse((root/'wrong-role/completed.json').exists())

    def artifact_fixture(self, directory, target, mutate):
        """Mock only CLI/export completion; all artifact I/O remains real."""
        session_id = '20260908_154507_75fcb3'
        def finished(command, worktree, env, location, prefix, deadline):
            if not prefix:
                (directory/'stdout.txt').write_text('LWL_ROLE_COMPLETE\n')
                (directory/'stderr.txt').write_text('session_id: '+session_id+'\n')
                (directory/'report.json').write_text(json.dumps(
                    {'complete':True, 'item':'request-2', 'base':'a'*40}))
            else:
                (directory/'session.jsonl').write_text(json.dumps(
                    {'id':session_id, 'ended_at':10, 'end_reason':'cli_close',
                     'messages':[{'role':'assistant', 'content':'LWL_ROLE_COMPLETE'}]}))
            if (directory/target).exists():
                mutate(directory/target)
            return 0
        return finished

    def test_artifact_fifos_rejected_without_blocking(self):
        import os
        import signal
        import time
        from unittest.mock import patch
        m = self.transport()
        def watchdog(signum, frame):
            self.fail('artifact read blocked past the role deadline')
        old = signal.signal(signal.SIGALRM, watchdog)
        try:
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                for target in ('report.json', 'session.jsonl', 'stdout.txt', 'stderr.txt'):
                    with self.subTest(target=target):
                        directory = root/target
                        def fifo(path):
                            path.unlink()
                            os.mkfifo(path)
                        with patch.object(m, 'run_process', side_effect=self.artifact_fixture(directory, target, fifo)):
                            signal.setitimer(signal.ITIMER_REAL, 1)
                            try:
                                with self.assertRaisesRegex(Blocked, 'regular'):
                                    m.run_role(root, directory, 'probe', 'request-2', 'a'*40,
                                               '', seconds=0.2, cli=['offline-fixture'])
                            finally:
                                signal.setitimer(signal.ITIMER_REAL, 0)
                        self.assertFalse((directory/'completed.json').exists())
        finally:
            signal.signal(signal.SIGALRM, old)

    def test_oversized_artifacts_rejected_before_reading_payload(self):
        import io
        import os
        from unittest.mock import patch
        m = self.transport()
        # A byte over each explicit finite envelope, not a huge allocation.
        limits = {'report.json':12000, 'session.jsonl':16*1024*1024,
                  'stdout.txt':1024*1024, 'stderr.txt':1024*1024}
        real_read, real_open = os.read, io.open
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for target, maximum in limits.items():
                with self.subTest(target=target):
                    directory = root/target
                    identity = []
                    def oversize(path):
                        with path.open('wb') as stream:
                            stream.truncate(maximum+1)
                        identity.append(path.stat().st_ino)
                    def read(fd, count):
                        self.assertNotIn(os.fstat(fd).st_ino, identity,
                                         'reject oversize via fstat before loading payload')
                        return real_read(fd, count)
                    def opened(path, mode='r', *args, **kwargs):
                        if Path(path) == directory/target and mode in ('r', 'rb'):
                            self.fail('unbounded path read attempted before size validation')
                        return real_open(path, mode, *args, **kwargs)
                    with patch.object(m, 'run_process', side_effect=self.artifact_fixture(directory, target, oversize)), \
                         patch.object(m.os, 'read', side_effect=read), patch.object(io, 'open', side_effect=opened):
                        with self.assertRaisesRegex(Blocked, 'exceeds'):
                            m.run_role(root, directory, 'probe', 'request-2', 'a'*40,
                                       '', seconds=1, cli=['offline-fixture'])
                    self.assertFalse((directory/'completed.json').exists())

    def test_log_fifo_is_rejected_before_process_launch(self):
        import os
        import signal
        import time
        from unittest.mock import patch
        m = self.transport()
        def watchdog(signum, frame):
            self.fail('log open blocked before launching the bounded process')
        old = signal.signal(signal.SIGALRM, watchdog)
        try:
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                for prefix in ('', 'export-'):
                    for stream in ('stdout.txt', 'stderr.txt'):
                        with self.subTest(prefix=prefix, stream=stream):
                            directory = root/(prefix+stream)
                            directory.mkdir()
                            os.mkfifo(directory/(prefix+stream))
                            with patch.object(m.subprocess, 'Popen') as spawn:
                                signal.setitimer(signal.ITIMER_REAL, 1)
                                try:
                                    with self.assertRaises(OSError):
                                        m.run_process(['offline-fixture'], root, {}, directory,
                                                      prefix, time.monotonic()+0.2)
                                finally:
                                    signal.setitimer(signal.ITIMER_REAL, 0)
                                spawn.assert_not_called()
        finally:
            signal.signal(signal.SIGALRM, old)

    def test_artifact_open_replacement_rejected_and_descriptor_closed(self):
        import os
        import time
        from unittest.mock import patch
        m = self.transport()
        real_open = os.open
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for replacement in ('fifo', 'symlink', 'regular'):
                with self.subTest(replacement=replacement):
                    path = root/replacement
                    path.write_bytes(b'original')
                    destination = root/(replacement+'-other')
                    destination.write_bytes(b'replacement')
                    descriptors = []
                    def raced_open(target, flags, *args, **kwargs):
                        self.assertTrue(flags & os.O_NONBLOCK, 'never block opening a replaced FIFO')
                        self.assertTrue(flags & os.O_NOFOLLOW, 'never follow a replaced symlink')
                        path.unlink()
                        if replacement == 'fifo':
                            os.mkfifo(path)
                        elif replacement == 'symlink':
                            path.symlink_to(destination)
                        else:
                            destination.rename(path)
                        fd = real_open(target, flags, *args, **kwargs)
                        descriptors.append(fd)
                        return fd
                    with patch.object(m.os, 'open', side_effect=raced_open):
                        with self.assertRaisesRegex(Blocked, 'regular'):
                            m.read_artifact(path, 100, time.monotonic()+1)
                    for fd in descriptors:
                        with self.assertRaises(OSError):
                            os.fstat(fd)
            for path in (root/'fifo', root/'symlink', root):
                with self.subTest(nonregular=path), self.assertRaisesRegex(Blocked, 'regular'):
                    m.read_artifact(path, 100, time.monotonic()+1)

    def test_artifact_growth_is_capped_and_read_deadline_closes_descriptor(self):
        import os
        import time
        from unittest.mock import patch
        m = self.transport()
        real_read, real_fstat = os.read, os.fstat
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'report.json'
            path.write_bytes(b'x'*16)
            self.assertEqual(m.read_artifact(path, 16, time.monotonic()+1), b'x'*16)
            path.write_bytes(b'')
            self.assertEqual(m.read_artifact(path, 16, time.monotonic()+1), b'')
            path.write_bytes(b'x'*16)
            sizes, descriptors = [], []
            def grow_after_stat(fd):
                checked = real_fstat(fd)
                with path.open('ab') as stream:
                    stream.write(b'x'*100)
                return checked
            def read(fd, count):
                sizes.append(count)
                descriptors.append(fd)
                return real_read(fd, count)
            with patch.object(m.os, 'fstat', side_effect=grow_after_stat), \
                 patch.object(m.os, 'read', side_effect=read):
                with self.assertRaisesRegex(Blocked, 'exceeds'):
                    m.read_artifact(path, 16, time.monotonic()+1)
            self.assertEqual(sum(sizes), 17, 'cap growth at limit plus one sentinel byte')
            with self.assertRaises(OSError):
                real_fstat(descriptors[-1])
            path.write_bytes(b'x'*100000)
            sizes.clear()
            with patch.object(m.os, 'read', side_effect=read), \
                 patch.object(m.time, 'monotonic', side_effect=[0, 0, 2]):
                with self.assertRaisesRegex(Blocked, 'deadline'):
                    m.read_artifact(path, 100000, 1)
            self.assertEqual(sizes, [65536], 'deadline checked between bounded reads')
            with self.assertRaises(OSError):
                real_fstat(descriptors[-1])
            with patch.object(m.os, 'open') as opened:
                with self.assertRaisesRegex(Blocked, 'deadline'):
                    m.read_artifact(path, 100000, time.monotonic()-1)
                opened.assert_not_called()

    def test_spawn_setup_failures_reap_child_without_masking_cause(self):
        import os
        import signal
        import subprocess
        import time
        from unittest.mock import patch
        m = self.transport()
        real_popen, real_write, real_signal = subprocess.Popen, Path.write_text, signal.signal
        real_dumps = json.dumps
        original_handlers = {sig: signal.getsignal(sig) for sig in (signal.SIGINT, signal.SIGTERM)}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for stage in ('process', 'handler'):
                for exit_failure in (False, True, 'serialization'):
                    with self.subTest(stage=stage, exit_failure=exit_failure):
                        directory = root/f'{stage}-{exit_failure}'
                        directory.mkdir()
                        children = []
                        cause = OSError('injected setup failure')
                        def spawn(*args, **kwargs):
                            child = real_popen(*args, **kwargs)
                            children.append(child)
                            return child
                        def write(path, *args, **kwargs):
                            if path.name == 'process.json' and stage == 'process':
                                raise cause
                            if path.name == 'exit.json' and exit_failure is True:
                                raise OSError('injected exit receipt failure')
                            return real_write(path, *args, **kwargs)
                        def serialize(value, *args, **kwargs):
                            if exit_failure == 'serialization' and 'ended_at' in value:
                                raise OSError('injected exit serialization failure')
                            return real_dumps(value, *args, **kwargs)
                        def install(sig, handler):
                            if stage == 'handler' and sig == signal.SIGTERM and callable(handler):
                                raise cause
                            return real_signal(sig, handler)
                        try:
                            with patch.object(m.subprocess, 'Popen', side_effect=spawn), \
                                 patch.object(Path, 'write_text', write), \
                                 patch.object(m.json, 'dumps', side_effect=serialize), \
                                 patch.object(m.signal, 'signal', side_effect=install):
                                with self.assertRaises(OSError) as raised:
                                    m.run_process([sys.executable, '-c', 'import time; time.sleep(30)'],
                                                  root, os.environ.copy(), directory, '', time.monotonic()+0.2)
                            self.assertIs(raised.exception, cause, 'cleanup must not mask the original failure')
                            self.assertEqual(len(children), 1)
                            child = children[0]
                            self.assertIsNotNone(child.returncode, 'spawned child must already be reaped')
                            with self.assertRaises(ProcessLookupError):
                                os.kill(child.pid, 0)
                            self.assertEqual({sig: signal.getsignal(sig) for sig in original_handlers},
                                             original_handlers, 'restore partially installed handlers')
                            if not exit_failure:
                                receipt = json.loads((directory/'exit.json').read_text())
                                self.assertEqual(receipt['pid'], child.pid)
                                self.assertEqual(receipt['returncode'], child.returncode)
                                self.assertEqual(receipt['reason'], 'interrupted')
                        finally:
                            # The RED version leaks; never leave the harmless fixture behind.
                            for child in children:
                                if child.poll() is None:
                                    os.killpg(child.pid, signal.SIGKILL)
                                child.wait(timeout=3)
                            for sig, handler in original_handlers.items():
                                real_signal(sig, handler)

    def test_transport_signal_reaps_exact_cli_and_preserves_quarantine(self):
        import os
        import signal
        import subprocess
        import time
        m = self.transport()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cli = self.fixture_cli(root)
            directory = root/'signal'
            marker = root/'unresolved-process.json'
            marker.write_text('{"existing":"owner-only"}')
            wrapper = root/'wrapper.py'
            wrapper.write_text('import sys\nfrom pathlib import Path\nsys.path.insert(0,' +
                               repr(str(ROOT/'scripts')) + ')\nfrom run_role import run_role\n' +
                               'run_role(Path('+repr(str(root))+'),Path('+repr(str(directory))+'),'+
                               repr('probe')+','+repr('request-2')+','+repr('a'*40)+','+
                               repr('SLOW_CLI')+',seconds=30,cli='+repr(cli)+')\n')
            child = subprocess.Popen([sys.executable,str(wrapper)],cwd=ROOT,
                                     stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
            try:
                end = time.monotonic()+5
                while not (directory/'report.json').exists() and time.monotonic()<end:
                    time.sleep(0.02)
                self.assertTrue((directory/'report.json').exists(), 'wait for the exact CLI readiness artifact')
                pid = json.loads((directory/'process.json').read_text())['pid']
                child.send_signal(signal.SIGTERM)
                self.assertNotEqual(child.wait(timeout=7),0)
                with self.assertRaises(ProcessLookupError):
                    os.kill(pid,0)
                self.assertEqual(json.loads((directory/'exit.json').read_text())['reason'],'interrupted')
                self.assertFalse((directory/'completed.json').exists())
                self.assertEqual(marker.read_text(),'{"existing":"owner-only"}')
            finally:
                if child.poll() is None:
                    os.killpg(child.pid,signal.SIGKILL)
                    child.wait(timeout=3)
                if (directory/'process.json').exists():
                    try:
                        os.killpg(json.loads((directory/'process.json').read_text())['pid'],signal.SIGKILL)
                    except ProcessLookupError:
                        pass

    def test_complete_reports_keep_failed_verdicts_and_reject_wrong_role_or_head(self):
        m = self.transport()
        session = {'id':'observed','ended_at':10,'end_reason':'cli_close',
                   'messages':[{'role':'assistant','content':'LWL_ROLE_COMPLETE'}]}
        common = {'complete':True,'item':'request-2','base':'a'*40,'lesson_id':'pattern-path'}
        review = {**common,'role':'code','sha':'b'*40,'passed':False,'substantive':False,
                  'security_concerns':[],'logic_errors':['No visual inspection yet'],
                  'curriculum_concerns':[],'tests':[],'summary':'blocked'}
        def check(report, role='code-reviewer'):
            return m.validate_completion(session,'observed',json.dumps(report).encode(),
                                         'request-2','a'*40,role=role,sha='b'*40,lesson_id='pattern-path')
        self.assertFalse(check(review)['passed'])
        passing = {**review,'passed':True,'substantive':True,'logic_errors':[],
                   'tests':['fixture assertions, not provider proof']}
        self.assertTrue(check(passing)['passed'])
        for change in ({'role':'curriculum'}, {'sha':'c'*40}, {'base':'c'*40},
                       {'passed':'true'}, {'tests':[]}, {'summary':''}, {'logic_errors':['bug']}):
            with self.subTest(change=change), self.assertRaises(Blocked):
                check({**passing, **change})
        planner = {**common,'status':'blocked','risks':['required source unavailable']}
        self.assertEqual(check(planner,'planner')['status'],'blocked')
        with self.assertRaises(Blocked):
            check({**planner,'status':'ready'},'planner')
        engineer = {**common,'status':'blocked','changed_paths':[],'red_green':[],
                    'tests':[],'visual_checks':[],'learning_changes':'','blockers':['not implemented']}
        self.assertEqual(check(engineer,'engineer')['status'],'blocked')
        with self.assertRaises(Blocked):
            check({**engineer,'lesson_id':'wrong'},'engineer')
        with self.assertRaises(Blocked):
            check({**engineer,'status':'ready','blockers':[]},'engineer')

    def test_real_subprocess_waits_for_exit_and_deadline_preserves_partial_artifacts(self):
        m = self.transport()
        self.assertTrue(hasattr(m, 'run_role'), 'bounded CLI role launcher is required')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture = root / 'fixture.py'
            fixture.write_text('''import sys,time,json,pathlib
if 'export' in sys.argv:
    target=pathlib.Path(sys.argv[-1])
    target.write_text(json.dumps({'id':'20260908_154507_75fcb3','ended_at':10,'end_reason':'cli_close','messages':[{'role':'assistant','content':'LWL_ROLE_COMPLETE'}]}))
else:
    prompt=pathlib.Path(sys.argv[sys.argv.index('--query-file')+1]).read_text()
    target=pathlib.Path(prompt.split('REPORT_PATH=')[1].split('\\n')[0])
    target.write_text(json.dumps({'complete':True,'item':'request-2','base':'a'*40}))
    if 'SLOW_FIXTURE' in prompt: time.sleep(5)
    print('LWL_ROLE_COMPLETE')
    print('session_id: 20260908_154507_75fcb3',file=sys.stderr)
''')
            result = m.run_role(root, root / 'success', 'probe', 'request-2', 'a'*40,
                                'FAST_FIXTURE', seconds=10, cli=[sys.executable,str(fixture)])
            self.assertEqual(result['status'], 'completed')
            self.assertEqual(result['agent_id'], '20260908_154507_75fcb3')
            self.assertTrue((root/'success/session.jsonl').is_file())
            with self.assertRaises(Blocked):
                m.run_role(root, root/'timeout', 'probe', 'request-2', 'a'*40,
                           'SLOW_FIXTURE', seconds=0.2, cli=[sys.executable,str(fixture)])
            self.assertTrue((root/'timeout/report.json').is_file())
            self.assertFalse((root/'timeout/completed.json').exists())
            self.assertTrue((root/'timeout/started.json').exists())
            with self.assertRaises(FileExistsError):
                m.run_role(root, root/'success', 'probe', 'request-2', 'a'*40,
                           'FAST_FIXTURE', seconds=10, cli=[sys.executable,str(fixture)])


if __name__ == '__main__':
    unittest.main()
