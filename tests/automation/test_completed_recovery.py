"""Offline SQLite/Git/API fixtures; these are not live publication evidence."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from autonomy_state import Store, Blocked
from autonomy_runtime import run_lock


class CompletedPublicationTests(unittest.TestCase):
    def setUp(self):
        target = ROOT / 'scripts/reconcile_completed.py'
        self.assertTrue(target.exists(), 'owner publication has no guarded canonical reconciliation path')
        spec = importlib.util.spec_from_file_location('reconcile_completed', target)
        assert spec is not None and spec.loader is not None
        self.helper = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.helper)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.env = patch.dict(os.environ, {}, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)
        self.root = Path(self.tmp.name).resolve()
        self.git(self.root, 'init', '-q', '-b', 'main')
        (self.root/'lesson').write_text('base')
        self.git(self.root, 'add', 'lesson')
        self.git(self.root, '-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', 'commit', '-qm', 'base')
        base = self.git(self.root, 'rev-parse', 'HEAD')
        self.worktree = self.root/'.autonomy-worktrees/request-2'
        self.git(self.root, 'worktree', 'add', '-b', 'auto/request-2', str(self.worktree))
        (self.worktree/'lesson').write_text('published candidate')
        self.git(self.worktree, 'add', 'lesson')
        self.git(self.worktree, '-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', 'commit', '-qm', 'candidate')
        head = self.git(self.worktree, 'rev-parse', 'HEAD')
        self.state = self.root/'.git/autonomy'
        self.store = Store(self.state/'state.sqlite3')
        self.addCleanup(self.store.close)
        self.pending = {'item': 'request-2', 'branch': 'auto/request-2', 'lesson_id': 'pattern-path',
                        'stage': 'planned', 'base': base, 'blocker': 'original engineer interrupted',
                        'worktree': str(self.worktree)}
        for day in ('2026-09-07', '2026-09-07', '2026-09-08', '2026-09-08'):
            attempt = self.store.begin(day)
            self.store.checkpoint(attempt, self.pending)
            self.store.finish(attempt, 'blocked')
        self.attempts = self.store.db.execute('SELECT * FROM attempts').fetchall()
        self.intent = {'item': 'request-2', 'pr': 7, 'lesson_id': 'pattern-path',
                       'sha': head, 'base': base, 'merge_sha': 'c'*40,
                       'authorization': 'Owner explicitly requests reconciliation of this completed publication'}
        self.pr = {'number': 7, 'state': 'closed', 'merged': True, 'merge_commit_sha': 'c'*40,
                   'body': '<!-- lwl:item:request-2 -->',
                   'head': {'ref': 'auto/request-2', 'sha': head, 'repo': {'full_name': self.helper.REPO}},
                   'base': {'ref': 'main', 'sha': base, 'repo': {'full_name': self.helper.REPO}}}
        self.status = {'sha': head, 'statuses': [{'id': 1, 'context': 'independent-review', 'state': 'success'}]}
        self.quality = True
        self.deploy = True
        self.live = {'passed': True, 'sha': 'c'*40, 'lesson': 'pattern-path'}
        self.endpoints = []
        self.verified = []

    def git(self, root, *args):
        return subprocess.run(['git', *args], cwd=root, capture_output=True, text=True, check=True, timeout=30).stdout.strip()

    def api(self, endpoint):
        self.endpoints.append(endpoint)
        if endpoint.endswith('/pulls/7'):
            return self.pr
        if '/commits/' in endpoint:
            return self.status
        if 'quality.yml/runs?' in endpoint:
            return {'workflow_runs': [{'id': 1, 'head_sha': self.intent['sha'], 'head_branch': 'auto/request-2',
                    'event': 'pull_request', 'path': '.github/workflows/quality.yml',
                    'status': 'completed', 'conclusion': 'success' if self.quality else 'failure'}]}
        if '/actions/runs/1/jobs?' in endpoint:
            return {'jobs': [{'name': 'quality', 'head_sha': self.intent['sha'], 'status': 'completed', 'conclusion': 'success'}]}
        if 'deploy.yml/runs?' in endpoint:
            return {'workflow_runs': [{'id': 2, 'head_sha': 'c'*40, 'head_branch': 'main',
                    'event': 'workflow_run', 'status': 'completed', 'conclusion': 'success' if self.deploy else 'failure'}]}
        self.fail(endpoint)

    def browser(self, root, sha, lesson):
        self.verified.append((root, sha, lesson))
        return self.live

    def reconcile(self):
        return self.helper.reconcile_completed(self.root, self.intent, api=self.api, verify=self.browser)

    def assert_blocked_unchanged(self):
        before = '\n'.join(self.store.db.iterdump())
        with self.assertRaises((Blocked, ValueError, KeyError, TypeError)):
            self.reconcile()
        self.assertEqual('\n'.join(self.store.db.iterdump()), before)
        self.assertFalse(list(self.state.glob('owner-completed-*')))

    def test_verified_existing_publication_archives_without_resetting_attempts(self):
        result = self.reconcile()
        self.assertEqual(result['status'], 'owner publication reconciled')
        receipt = json.loads(Path(result['receipt']).read_text())
        self.assertEqual(receipt['prior_checkpoint'], self.pending)
        self.assertEqual(receipt['intent'], self.intent)
        self.assertEqual(self.store.pending(), {})
        self.assertEqual(self.store.db.execute('SELECT * FROM attempts').fetchall(), self.attempts)
        self.assertEqual(self.store.db.execute('SELECT * FROM releases').fetchall(), [])
        self.assertEqual(self.store.gate('2026-09-08'), {'wakeAgent': False, 'reason': 'daily attempt limit'})
        self.assertEqual(self.store.gate('2026-09-09'), {'wakeAgent': True, 'reason': 'daily target due'})
        self.assertEqual((self.worktree/'lesson').read_text(), 'published candidate')
        self.assertEqual(self.verified, [(self.root, 'c'*40, 'pattern-path')])
        backup = sqlite3.connect(result['backup'])
        self.assertEqual(json.loads(backup.execute('SELECT data FROM checkpoint').fetchone()[0]), self.pending)
        backup.close()

    def test_saved_candidate_mismatch_blocks_before_network(self):
        with self.store.db:
            self.store.db.execute('UPDATE checkpoint SET data=?', (json.dumps({**self.pending, 'sha': 'd'*40}),))
        self.assert_blocked_unchanged()
        self.assertFalse(self.endpoints)

    def test_dirty_worktree_is_not_mistaken_for_completed_pending_work(self):
        (self.worktree/'lesson').write_text('newer human draft')
        self.assert_blocked_unchanged()
        self.assertEqual((self.worktree/'lesson').read_text(), 'newer human draft')

    def test_guards_reject_supervised_lock_quarantine_and_running_attempt(self):
        with patch.dict(os.environ, {'LWL_ATTEMPT': '4'}):
            self.assert_blocked_unchanged()
        with run_lock(self.state/'run.lock'):
            self.assert_blocked_unchanged()
        (self.state/'unresolved-process.json').write_text('{}')
        self.assert_blocked_unchanged()
        (self.state/'unresolved-process.json').unlink()
        with self.store.db:
            self.store.db.execute("UPDATE attempts SET status='running' WHERE id=4")
        self.assert_blocked_unchanged()
        self.assertFalse(self.endpoints)

    def test_untrusted_or_stale_remote_pr_never_clears_checkpoint(self):
        original = copy.deepcopy(self.pr)
        for field, value in [('body', ''), ('merged', False), ('number', 8), ('merge_commit_sha', 'd'*40)]:
            with self.subTest(field=field):
                self.pr = {**copy.deepcopy(original), field: value}
                self.assert_blocked_unchanged()
        self.pr = copy.deepcopy(original)
        self.pr['head']['repo']['full_name'] = 'other/fork'
        self.assert_blocked_unchanged()

    def test_documented_supervised_checkpoint_then_recover_sequence(self):
        import autonomy as a
        from test_release_boundary import evidence
        # Canonical evidence saved by a completed supervised merge, before its
        # checkpoint write. Public PR text and caller-supplied evidence_file do not suffice.
        proof = self.state / ('evidence-' + self.intent['sha'] + '.json')
        proof.write_text(json.dumps(evidence(self.intent['sha'], self.intent['base'])))
        attempt = self.store.begin('2026-09-09')
        binding = {**self.pending, 'pr': 7, 'sha': self.intent['sha']}
        path = self.state/'binding.json'
        path.write_text(json.dumps(binding))
        with patch.dict(os.environ, {'LWL_ATTEMPT': str(attempt)}), patch.object(a, 'GitHub', lambda _: self.api):
            # The release helper stays strict; the documented prerequisite is necessary.
            with self.assertRaises(Blocked):
                a.main(['recover-merged', '--pr', '7'], root=self.root)
            self.assertFalse(self.endpoints)
            a.main(['checkpoint', '--file', str(path)], root=self.root)
            a.main(['recover-merged', '--pr', '7'], root=self.root)
        self.assertEqual(self.store.pending()['stage'], 'merged')
        self.assertEqual(self.store.pending()['pr'], 7)
        self.assertEqual(self.store.pending()['merge_sha'], self.intent['merge_sha'])
        self.assertEqual(self.store.pending()['blocker'], self.pending['blocker'])
        self.assertEqual(self.store.db.execute('SELECT * FROM releases').fetchall(), [])
        with patch.dict(os.environ, {'LWL_ATTEMPT': str(attempt)}), patch.object(a, 'GitHub', lambda _: self.api), \
                patch.object(a, 'today', return_value='2026-09-09'), \
                patch.object(a, 'command', side_effect=self.offline_live_command):
            a.main(['verify-live', '--lesson', 'pattern-path'], root=self.root)
        self.assertEqual(self.store.pending(), {})
        self.assertEqual(self.store.db.execute('SELECT day, attempt FROM releases').fetchall(), [('2026-09-09', attempt)])
        self.assertEqual(self.store.db.execute('SELECT * FROM attempts WHERE id < ?', (attempt,)).fetchall(), self.attempts)

    def offline_live_command(self, argv, cwd, timeout=60):
        from autonomy_release import command
        if argv[0] == 'node':
            self.assertEqual(argv[2:], [self.intent['merge_sha'], self.intent['lesson_id']])
            return json.dumps(self.live)
        return command(argv, cwd, timeout=timeout)

    def test_historical_or_ambiguous_binding_cannot_award_daily_success(self):
        import autonomy as a
        self.pr['merged_at'] = '2026-09-07T18:00:00Z'
        attempt = self.store.begin('2026-09-09')
        binding = {**self.pending, 'pr': 7, 'sha': self.intent['sha']}
        path = self.state / 'binding.json'
        path.write_text(json.dumps(binding))
        with patch.dict(os.environ, {'LWL_ATTEMPT': str(attempt)}), patch.object(a, 'GitHub', lambda _: self.api), \
                patch.object(a, 'today', return_value='2026-09-09'), \
                patch.object(a, 'command', side_effect=self.offline_live_command):
            a.main(['checkpoint', '--file', str(path)], root=self.root)
            with self.assertRaisesRegex(Blocked, 'owner-only reconciliation'):
                a.main(['recover-merged', '--pr', '7'], root=self.root)
                a.main(['verify-live', '--lesson', 'pattern-path'], root=self.root)
        self.assertEqual(self.store.pending(), binding)
        self.assertEqual(self.store.db.execute('SELECT * FROM releases').fetchall(), [])
        self.assertEqual(self.store.db.execute('SELECT * FROM attempts WHERE id < ?', (attempt,)).fetchall(), self.attempts)
        self.assertEqual(self.store.db.execute('SELECT status FROM attempts WHERE id=?', (attempt,)).fetchone(), ('running',))

    def test_fabricated_merged_checkpoint_cannot_bypass_local_provenance(self):
        import autonomy as a
        from test_release_boundary import evidence
        attempt = self.store.begin('2026-09-09')
        binding = {**self.pending, 'pr': 7, 'sha': self.intent['sha'],
                   'merge_sha': self.intent['merge_sha'], 'stage': 'merged'}
        proof = self.state / ('evidence-' + self.intent['sha'] + '.json')
        valid = evidence(self.intent['sha'], self.intent['base'])
        external = self.state / 'caller-evidence.json'
        external.write_text(json.dumps(valid))
        binding['evidence_file'] = str(external)
        self.store.checkpoint(attempt, binding)
        variants = [None, '{', json.dumps({}), json.dumps({**valid, 'sha': 'd'*40}),
                    json.dumps({**valid, 'base': 'e'*40}),
                    json.dumps({**valid, 'reviews': []}), 'symlink']
        for value in variants:
            with self.subTest(proof=value):
                if value == 'symlink':
                    proof.unlink()
                    proof.symlink_to(external)
                elif value is not None:
                    proof.write_text(value)
                with patch.dict(os.environ, {'LWL_ATTEMPT': str(attempt)}), patch.object(a, 'GitHub', lambda _: self.api), \
                        patch.object(a, 'command', side_effect=self.offline_live_command), \
                        self.assertRaisesRegex(Blocked, 'owner-only reconciliation'):
                    a.main(['verify-live', '--lesson', 'pattern-path'], root=self.root)
                self.assertEqual(self.store.pending(), binding)
                self.assertEqual(self.store.db.execute('SELECT * FROM releases').fetchall(), [])

    def test_candidate_branch_head_path_and_untracked_changes_remain_pending(self):
        (self.worktree/'new-draft').write_text('retain me')
        self.assert_blocked_unchanged()
        (self.worktree/'new-draft').unlink()
        self.git(self.worktree, '-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', 'commit', '--allow-empty', '-qm', 'later candidate')
        self.assert_blocked_unchanged()
        self.assertEqual(self.store.pending(), self.pending)

    def test_archive_collision_never_overwrites_evidence_or_checkpoint(self):
        target = self.state/f"owner-completed-request-2-{self.intent['merge_sha']}.json"
        target.write_text('previous evidence')
        before = self.store.pending()
        with self.assertRaises(Blocked):
            self.reconcile()
        self.assertEqual(target.read_text(), 'previous evidence')
        self.assertEqual(self.store.pending(), before)

    def test_ci_review_deployment_and_live_must_all_match(self):
        self.quality = False
        self.assert_blocked_unchanged()
        self.quality = True
        self.status['statuses'].append({'id': 2, 'context': 'independent-review', 'state': 'failure'})
        self.assert_blocked_unchanged()
        self.status['statuses'].pop()
        self.deploy = False
        self.assert_blocked_unchanged()
        self.deploy = True
        self.live['sha'] = 'e'*40
        self.assert_blocked_unchanged()
        self.live['sha'] = 'c'*40
        self.live['passed'] = False
        self.assert_blocked_unchanged()

    def test_release_gates_revoked_during_browser_or_archive_preserve_pending(self):
        for boundary in ('browser', 'archive'):
            for gate in ('quality', 'independent-review', 'deployment'):
                with self.subTest(boundary=boundary, gate=gate):
                    f = CompletedPublicationTests()
                    f.setUp()
                    try:
                        def revoke():
                            if gate == 'quality':
                                f.quality = False
                            elif gate == 'deployment':
                                f.deploy = False
                            else:
                                f.status['statuses'].append({'id': 2, 'context': gate, 'state': 'failure'})
                        def browser(root, sha, lesson):
                            if boundary == 'browser':
                                revoke()
                            return f.live
                        original = os.open
                        def archive(path, flags, *args, **kwargs):
                            if boundary == 'archive' and str(path).endswith('.sqlite3'):
                                revoke()
                            return original(path, flags, *args, **kwargs)
                        with patch.object(f.helper.os, 'open', archive), self.assertRaises(Blocked):
                            f.helper.reconcile_completed(f.root, f.intent, api=f.api, verify=browser)
                        self.assertEqual(f.store.pending(), f.pending)
                        self.assertEqual(f.store.db.execute('SELECT * FROM attempts').fetchall(), f.attempts)
                        self.assertEqual(f.store.db.execute('SELECT * FROM releases').fetchall(), [])
                        self.assertEqual(len(list(f.state.glob('owner-completed-*'))), 2 if boundary == 'archive' else 0)
                    finally:
                        f.doCleanups()

    def test_worktree_changes_during_archival_preserve_checkpoint_and_archives(self):
        for change in ('dirty', 'head', 'branch', 'identity'):
            with self.subTest(change=change):
                f = CompletedPublicationTests()
                f.setUp()
                try:
                    original = os.open
                    def archive(path, flags, *args, **kwargs):
                        if str(path).endswith('.json') and Path(path).name.startswith('owner-completed-'):
                            if change == 'dirty':
                                (f.worktree / 'lesson').write_text('retained human edit')
                            elif change == 'head':
                                f.git(f.worktree, '-c', 'user.name=Test', '-c', 'user.email=test@example.invalid',
                                      'commit', '--allow-empty', '-qm', 'new head')
                            elif change == 'branch':
                                f.git(f.worktree, 'switch', '-c', 'human-draft')
                            else:
                                moved = f.worktree.with_name('retained-worktree')
                                f.git(f.root, 'worktree', 'move', str(f.worktree), str(moved))
                                f.worktree.symlink_to(moved, target_is_directory=True)
                        return original(path, flags, *args, **kwargs)
                    with patch.object(f.helper.os, 'open', archive), self.assertRaises(Blocked):
                        f.reconcile()
                    self.assertEqual(f.store.pending(), f.pending)
                    self.assertEqual(len(list(f.state.glob('owner-completed-*'))), 2)
                    self.assertEqual(f.store.db.execute('SELECT * FROM attempts').fetchall(), f.attempts)
                    self.assertEqual(f.store.db.execute('SELECT * FROM releases').fetchall(), [])
                    with self.assertRaises(Blocked):
                        f.reconcile()
                finally:
                    f.doCleanups()


if __name__ == '__main__':
    unittest.main()
