"""Offline release regressions: real Git/SQLite, no remote API calls."""
import contextlib
import copy
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import autonomy as a
import autonomy_release as r


class FixtureAPI:
    def __init__(self, sha, base, files):
        self.sha, self.base, self.files = sha, base, files
        self.writes = []
        self.merged = False
        self.pr = {'number': 1, 'state': 'open', 'draft': False, 'changed_files': len(files),
                   'head': {'sha': sha, 'ref': 'auto/request-1', 'repo': {'full_name': r.REPO}},
                   'base': {'sha': base, 'ref': 'main', 'repo': {'full_name': r.REPO}},
                   'body': '<!-- lwl:item:request-1 -->'}

    def __call__(self, endpoint, method='GET', data=None):
        if method != 'GET':
            self.writes.append((endpoint, method, data))
        if endpoint.endswith('/merge'):
            self.merged = True
            return {'merged': True, 'sha': self.sha}
        if '/statuses/' in endpoint:
            return {'state': 'success'}
        if endpoint.endswith('/status'):
            return {'statuses': [{'context': 'independent-review', 'state': 'success'}]}
        if '/git/ref/heads/main' in endpoint:
            return {'object': {'sha': self.base}}
        if '/actions/workflows/quality.yml/runs?' in endpoint:
            return {'workflow_runs': [{'id': 9, 'head_sha': self.sha, 'head_branch': 'auto/request-1',
                    'event': 'pull_request', 'path': '.github/workflows/quality.yml',
                    'status': 'completed', 'conclusion': 'success'}]}
        if '/actions/runs/9/jobs?' in endpoint:
            return {'jobs': [{'name': 'quality', 'status': 'completed', 'conclusion': 'success', 'head_sha': self.sha}]}
        if '/files?' in endpoint:
            return copy.deepcopy(self.files)
        if endpoint.endswith('/pulls/1'):
            return {**self.pr, 'state': 'closed', 'merged': True, 'merge_commit_sha': self.sha} if self.merged else copy.deepcopy(self.pr)
        raise AssertionError(endpoint)


def evidence(sha, base):
    return {'sha': sha, 'base': base, 'engineer_agent_id': 'fixture-eng', 'lead_agent_id': 'fixture-lead',
            'reviews': [{'role': role, 'agent_id': 'fixture-' + role, 'sha': sha, 'base': base,
                         'passed': True, 'substantive': True, 'security_concerns': [], 'logic_errors': [],
                         'curriculum_concerns': [], 'tests': ['offline fixture receipt']}
                        for role in ['code', 'curriculum']]}


class ReleaseBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / 'repo'
        self.origin = Path(self.tmp.name) / 'origin'
        subprocess.run(['git', 'init', '-q', '-b', 'main', str(self.root)], check=True)
        subprocess.run(['git', 'init', '-q', '--bare', str(self.origin)], check=True)
        self.git('config', 'user.name', 'Test')
        self.git('config', 'user.email', 'test@example.invalid')
        (self.root / 'src/data').mkdir(parents=True)
        self.lesson = self.root / 'src/data/lessons.json'
        self.lesson.write_text('[{"id":"one","idea":"before"}]\n')
        self.git('add', 'src')
        self.git('commit', '-qm', 'base fixture')
        self.base = self.git('rev-parse', 'HEAD')
        self.git('remote', 'add', 'origin', str(self.origin))
        self.git('push', '-q', 'origin', 'main')
        self.git('checkout', '-qb', 'auto/request-1')
        self.lesson.write_text('[{"id":"one","idea":"substantive new explanation"}]\n')
        self.git('add', 'src')
        self.git('commit', '-qm', 'lesson fixture')
        self.sha = self.git('rev-parse', 'HEAD')
        self.git('push', '-q', 'origin', 'auto/request-1')
        self.files = [{'filename': 'src/data/lessons.json', 'status': 'modified', 'changes': 2}]

    def git(self, *args):
        return subprocess.run(['git', *args], cwd=self.root, check=True, capture_output=True, text=True).stdout.strip()

    def test_cli_mismatched_checkpoint_item_makes_no_writes(self):
        api = FixtureAPI(self.sha, self.base, self.files)
        location = a.state_dir(self.root)
        store = a.Store(location / 'state.sqlite3')
        self.addCleanup(store.close)
        attempt = store.begin(a.today())
        checkpoint = {'item': 'request-2', 'pr': 1, 'stage': 'reviewed'}
        store.checkpoint(attempt, checkpoint)
        source = Path(self.tmp.name) / 'review.json'
        source.write_text(json.dumps(evidence(self.sha, self.base)))
        caught = None
        with patch.dict(os.environ, {'LWL_ATTEMPT': str(attempt)}), patch.object(a, 'GitHub', return_value=api), contextlib.redirect_stdout(io.StringIO()):
            try:
                a.main(['merge', '--pr', '1', '--file', str(source)], root=self.root)
            except a.Blocked as exc:
                caught = exc
        self.assertEqual(api.writes, [], 'mismatched checkpoint must not publish status or merge')
        self.assertIsNotNone(caught)
        self.assertEqual(store.pending(), checkpoint)
        self.assertFalse((location / ('evidence-' + self.sha + '.json')).exists())

    def test_final_revalidation_rejects_item_change_before_merge(self):
        api = FixtureAPI(self.sha, self.base, self.files)
        def changing_api(endpoint, method='GET', data=None):
            result = api(endpoint, method, data)
            if method == 'POST':
                api.pr['head']['ref'] = 'auto/request-2'
                api.pr['body'] = '<!-- lwl:item:request-2 -->'
            return result
        caught = None
        try:
            r.release(changing_api, r.Git(self.root), 1, evidence(self.sha, self.base), 'request-1')
        except r.Blocked as exc:
            caught = exc
        self.assertEqual([x for x in api.writes if x[1] == 'PUT'], [])
        self.assertIsNotNone(caught)

    def test_cli_saved_merge_evidence_survives_checkpoint_and_live_interruptions(self):
        api = FixtureAPI(self.sha, self.base, self.files)
        location = a.state_dir(self.root)
        store = a.Store(location / 'state.sqlite3')
        self.addCleanup(store.close)
        attempt = store.begin('2026-09-09')
        checkpoint = {'item': 'request-1', 'pr': 1, 'stage': 'reviewed',
                      'sha': self.sha, 'base': self.base, 'lesson_id': 'one'}
        store.checkpoint(attempt, checkpoint)
        source = Path(self.tmp.name) / 'review.json'
        ev = evidence(self.sha, self.base)
        source.write_text(json.dumps(ev))
        proof = location / ('evidence-' + self.sha + '.json')
        original_command = a.command
        def offline_command(argv, cwd, timeout=60):
            if argv[0] == 'node':
                self.assertEqual(argv[2:], [self.sha, 'one'])
                return json.dumps({'passed': True, 'sha': self.sha, 'lesson_id': 'one'})
            return original_command(argv, cwd, timeout=timeout)
        def offline_api(endpoint, method='GET', data=None):
            if 'deploy.yml/runs?' in endpoint:
                return {'workflow_runs': [{'id': 20, 'head_sha': self.sha, 'head_branch': 'main',
                        'event': 'workflow_run', 'status': 'completed', 'conclusion': 'success'}]}
            return api(endpoint, method, data)
        with patch.dict(os.environ, {'LWL_ATTEMPT': str(attempt)}), \
                patch.object(a, 'GitHub', return_value=offline_api), \
                patch.object(a, 'today', return_value='2026-09-09'), \
                patch.object(a, 'command', side_effect=offline_command), contextlib.redirect_stdout(io.StringIO()):
            # Real protected release helper, offline API and local Git only.
            # Evidence is saved after merge read-back, before checkpointing.
            with patch.object(a.Store, 'checkpoint', side_effect=OSError('interrupted checkpoint')), \
                    self.assertRaisesRegex(OSError, 'interrupted checkpoint'):
                a.main(['merge', '--pr', '1', '--file', str(source)], root=self.root)
            self.assertTrue(api.merged)
            self.assertEqual(json.loads(proof.read_text()), ev)
            self.assertEqual(store.pending(), checkpoint)
            a.main(['recover-merged', '--pr', '1'], root=self.root)
            with patch.object(a.Store, 'finish', side_effect=OSError('interrupted live receipt')), \
                    self.assertRaisesRegex(OSError, 'interrupted live receipt'):
                a.main(['verify-live', '--lesson', 'one'], root=self.root)
            self.assertEqual(store.pending()['stage'], 'live')
            self.assertEqual(store.db.execute('SELECT * FROM releases').fetchall(), [])
            a.main(['recover-merged', '--pr', '1'], root=self.root)
            a.main(['verify-live', '--lesson', 'one'], root=self.root)
        self.assertEqual(store.pending(), {})
        self.assertEqual(store.db.execute('SELECT day, attempt FROM releases').fetchall(), [('2026-09-09', attempt)])
        self.assertEqual(len([call for call in api.writes if call[1] == 'PUT']), 1)
        self.assertEqual(json.loads(proof.read_text()), ev)

    def test_reviewed_binary_blob_blocks_writes_even_with_text_worktree(self):
        (self.root / 'public').mkdir()
        image = self.root / 'public/image.bin'
        image.write_bytes(b'\x00\x01binary fixture\x00')
        self.git('add', 'public')
        self.git('commit', '-qm', 'binary fixture')
        self.sha = self.git('rev-parse', 'HEAD')
        self.git('push', '-q', 'origin', 'auto/request-1')
        image.write_text('harmless unstaged text must not mask reviewed binary\n')
        self.assertIn('-\t-\tpublic/image.bin', self.git('diff', '--numstat', self.base, self.sha, '--'))
        api = FixtureAPI(self.sha, self.base, self.files + [
            {'filename': 'public/image.bin', 'status': 'added', 'changes': 0}])
        caught = None
        try:
            r.release(api, r.Git(self.root), 1, evidence(self.sha, self.base), 'request-1')
        except r.Blocked as exc:
            caught = exc
        self.assertEqual(api.writes, [], 'exact reviewed binary must not publish status or merge')
        self.assertIsNotNone(caught)
        self.assertIn('binary', str(caught))

    def test_inspect_derives_paths_sizes_status_and_modes_from_objects(self):
        note = self.root / 'src/note.js'
        note.write_text('// fixture\n')
        self.git('add', 'src/note.js')
        self.git('update-index', '--chmod=+x', 'src/note.js')
        self.git('commit', '-qm', 'text fixture')
        self.sha = self.git('rev-parse', 'HEAD')
        self.git('push', '-q', 'origin', 'auto/request-1')
        note.write_text('unstaged worktree content\n' * 10)
        files = [{'filename': 'public/not-in-the-commit.txt', 'status': 'added', 'changes': 0}]
        api = FixtureAPI(self.sha, self.base, files)
        before, after = r.Git(self.root).inspect(api.pr, files)
        self.assertEqual(files, [
            {'filename': 'src/data/lessons.json', 'status': 'modified', 'changes': 2, 'mode': '100644'},
            {'filename': 'src/note.js', 'status': 'added', 'changes': 1, 'mode': '100755'}])
        self.assertNotEqual(before[0]['idea'], after[0]['idea'])


if __name__ == '__main__':
    unittest.main()
