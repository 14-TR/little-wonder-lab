import copy
import sys
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))


class ReleaseTests(unittest.TestCase):
    def test_release_pins_merge_and_reads_back_status_and_merge(self):
        self.assertTrue((ROOT / 'scripts/autonomy_release.py').exists(), 'release adapter missing')
        import autonomy_release as r
        sha, base, merged = 'a'*40, 'b'*40, 'c'*40
        pr = {'number': 1, 'state': 'open', 'draft': False, 'changed_files': 1,
              'head': {'sha': sha, 'ref': 'auto/request-1', 'repo': {'full_name': r.REPO}},
              'base': {'sha': base, 'ref': 'main', 'repo': {'full_name': r.REPO}},
              'body': '<!-- lwl:item:request-1 -->'}
        ev = {'sha': sha, 'base': base, 'engineer_agent_id': 'eng', 'lead_agent_id': 'lead', 'reviews': [
            {'role': role, 'agent_id': role, 'sha': sha, 'base': base, 'passed': True, 'substantive': True,
             'security_concerns': [], 'logic_errors': [], 'curriculum_concerns': [], 'tests': ['actual test receipt']} for role in ['code', 'curriculum']]}
        class API:
            def __init__(self): self.calls = []; self.merged = False; self.status = False
            def __call__(self, endpoint, method='GET', data=None):
                self.calls.append((endpoint, method, data))
                if endpoint.endswith('/merge'):
                    self.merged = True
                    return {'merged': True, 'sha': merged}
                if '/statuses/' in endpoint:
                    self.status = True
                    return {'state': 'success'}
                if endpoint.endswith('/status'):
                    return {'statuses': [{'context': 'independent-review', 'state': 'success'}] if self.status else []}
                if '/git/ref/heads/main' in endpoint: return {'object': {'sha': base}}
                if '/actions/workflows/quality.yml/runs?' in endpoint:
                    return {'workflow_runs': [{'id': 9, 'head_sha': sha, 'head_branch': 'auto/request-1',
                            'event': 'pull_request', 'path': '.github/workflows/quality.yml', 'status': 'completed', 'conclusion': 'success'}]}
                if '/actions/runs/9/jobs?' in endpoint:
                    return {'jobs': [{'name': 'quality', 'status': 'completed', 'conclusion': 'success', 'head_sha': sha}]}
                if '/files?' in endpoint: return [{'filename': 'src/data/lessons.json', 'status': 'modified', 'changes': 20}]
                if endpoint.endswith('/pulls/1'):
                    return {**pr, 'state': 'closed', 'merged': True, 'merge_commit_sha': merged} if self.merged else copy.deepcopy(pr)
                raise AssertionError(endpoint)
        class Git:
            def inspect(self, pr, files): return ([{'id': 'one', 'idea': 'a'}], [{'id': 'one', 'idea': 'b'}])
        api = API()
        receipt = r.release(api, Git(), 1, ev, 'request-1')
        self.assertEqual(receipt['merge_sha'], merged)
        self.assertEqual([x[2] for x in api.calls if x[0].endswith('/merge')], [{'sha': sha, 'merge_method': 'squash'}])
        self.assertEqual(api.calls[-1][0], f'repos/{r.REPO}/pulls/1')
        self.assertTrue(any(x[0].endswith('/status') and x[1] == 'GET' for x in api.calls))
        broken = copy.deepcopy(ev); broken['reviews'][0]['passed'] = False
        api = API()
        with self.assertRaises(r.Blocked): r.release(api, Git(), 1, broken, 'request-1')
        self.assertTrue(all(x[1] == 'GET' for x in api.calls))


if __name__ == '__main__': unittest.main()
