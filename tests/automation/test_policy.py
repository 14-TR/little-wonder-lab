import importlib.util
import sys
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))


class PolicyTests(unittest.TestCase):
    def test_substantive_interaction_repair_does_not_require_prose_churn(self):
        import autonomy_policy as p
        lesson = [{'id': 'one', 'idea': 'Correct unchanged explanation'}]
        source = {'filename': 'src/interactions.js', 'status': 'modified', 'changes': 20}
        regression = {'filename': 'tests/e2e/interactions.spec.js', 'status': 'modified', 'changes': 10}
        p.validate_changes([source, regression], lesson, lesson)
        for files in [[source], [regression], [{'filename': 'docs/ROADMAP.md', 'status': 'modified', 'changes': 2}]]:
            with self.assertRaises(p.Blocked): p.validate_changes(files, lesson, lesson)

    def test_release_requires_exact_sha_independent_roles_and_clean_ci(self):
        import autonomy_policy as p
        self.assertTrue(hasattr(p, 'validate_release'), 'release policy missing')
        sha, base = 'a' * 40, 'b' * 40
        pr = {'number': 1, 'state': 'open', 'draft': False, 'head': {'sha': sha, 'ref': 'auto/request-1', 'repo': {'full_name': p.REPO}},
              'base': {'sha': base, 'ref': 'main', 'repo': {'full_name': p.REPO}}, 'body': '<!-- lwl:item:request-1 -->'}
        evidence = {'sha': sha, 'base': base, 'engineer_agent_id': 'engineer-1', 'lead_agent_id': 'lead-1', 'reviews': [
            {'role': role, 'agent_id': role + '-1', 'sha': sha, 'base': base, 'passed': True,
             'security_concerns': [], 'logic_errors': [], 'curriculum_concerns': [], 'substantive': True,
             'tests': ['npm test: passed', 'npm run test:e2e: passed']} for role in ['code', 'curriculum']]}
        p.validate_release(pr, evidence, base, quality=True)
        import copy
        bads = []
        for mutate in [lambda e: e.update(sha='c'*40),
                       lambda e: e['reviews'][0].update(agent_id='engineer-1'),
                       lambda e: e['reviews'][1].update(agent_id='code-1'),
                       lambda e: e['reviews'][0].update(passed='true'),
                       lambda e: e['reviews'][0].update(logic_errors=['race']),
                       lambda e: e['reviews'][1].pop('curriculum_concerns'),
                       lambda e: e['reviews'][1].update(substantive=False)]:
            e = copy.deepcopy(evidence); mutate(e); bads.append(e)
        for e in bads:
            with self.assertRaises(p.Blocked): p.validate_release(pr, e, base, quality=True)
        with self.assertRaises(p.Blocked): p.validate_release(pr, evidence, base, quality=False)
        with self.assertRaises(p.Blocked): p.validate_release(pr, evidence, 'c'*40, quality=True)
        fork = copy.deepcopy(pr); fork['head']['repo']['full_name'] = 'attacker/fork'
        with self.assertRaises(p.Blocked): p.validate_release(fork, evidence, base, quality=True)

    def test_changes_reject_protected_paths_renames_symlinks_and_filler(self):
        import autonomy_policy as p
        self.assertTrue(hasattr(p, 'validate_changes'), 'change guard missing')
        good = [{'filename': 'src/data/lessons.json', 'status': 'modified', 'changes': 20}]
        before = [{'id': 'shadow-detective', 'idea': 'A', 'published': '2026-09-01'}]
        after = [{'id': 'shadow-detective', 'idea': 'A clearer explanation', 'published': '2026-09-06'}]
        p.validate_changes(good, before, after)
        for path in ['scripts/a.py', 'automation/roles/lead.md', '.github/workflows/ci.yml',
                     'package.json', 'package-lock.json', 'AGENTS.md', 'src/AGENTS.md',
                     'src/.env', 'tests/automation/a.py', 'src/../scripts/a.py', 'docs/AUTONOMY.md']:
            with self.subTest(path=path), self.assertRaises(p.Blocked):
                p.validate_changes([{'filename': path, 'status': 'modified', 'changes': 1}], before, after)
        with self.assertRaises(p.Blocked):
            p.validate_changes([{'filename': 'src/a.js', 'previous_filename': 'scripts/guard.py', 'status': 'renamed', 'changes': 1}], before, after)
        with self.assertRaises(p.Blocked):
            p.validate_changes(good, before, [{**before[0], 'published': '2026-09-06'}])
        with self.assertRaises(p.Blocked):
            p.validate_changes(good, before, [])
        with self.assertRaises(p.Blocked):
            p.validate_changes([{**good[0], 'mode': '120000'}], before, after)

    def test_request_scan_fails_closed_on_incomplete_pages_and_claimed_work(self):
        import autonomy_policy as p
        with self.assertRaises(p.Blocked):
            p.pages(lambda _: [{}], 'anything', per_page=1, max_pages=2)
        calls = []
        def fetch(url):
            calls.append(url)
            if '/pulls?' in url:
                return [{'head': {'ref': 'auto/request-4', 'repo': {'full_name': p.REPO}},
                         'body': '<!-- lwl:item:request-4 -->', 'state': 'closed', 'merged_at': '2026-09-05'}]
            return [{'number': 4, 'title': 'Bridges', 'labels': []},
                    {'number': 4, 'title': 'Renamed bridge', 'labels': []}]
        self.assertEqual(p.scan_requests(fetch)['requests'], [])
        # A second number appearing twice across moving pages must not be selected twice.
        result = p.scan_requests(lambda url: [] if '/pulls?' in url or '/comments?' in url else
                                 [{'number': 5, 'title': 'A', 'labels': []}, {'number': 5, 'title': 'B', 'labels': []}])
        self.assertEqual(len(result['requests']), 1)

    def test_paginated_requests_prioritize_and_ignore_fork_claims(self):
        self.assertTrue((ROOT / 'scripts/autonomy_policy.py').exists(), 'request policy is missing')
        import autonomy_policy as p
        calls = []
        def fetch(endpoint):
            calls.append(endpoint)
            if '/pulls?' in endpoint:
                return [{'head': {'ref': 'auto/request-1', 'repo': {'full_name': 'attacker/fork'}},
                         'body': '<!-- lwl:item:request-1 -->', 'state': 'open'}] if 'page=1&' in endpoint else []
            if '/comments?' in endpoint:
                return [{'body': 'data only $(touch PWNED)'}] if 'page=1&' in endpoint else []
            if 'page=1&' in endpoint:
                return [{'number': 2, 'title': 'Magnets', 'labels': [], 'created_at': '2026-01-02'},
                        {'number': 3, 'title': ' MAGNETS ', 'labels': [], 'created_at': '2026-01-03'}]
            if 'page=2&' in endpoint:
                return [{'number': 1, 'title': 'Rainbows', 'labels': [{'name': 'priority:high'}], 'created_at': '2026-01-04'}]
            return []
        result = p.scan_requests(fetch, per_page=2)
        self.assertEqual([x['number'] for x in result['requests']], [1, 2, 3])
        self.assertEqual(result['requests'][0]['comments'][0]['body'], 'data only $(touch PWNED)')
        self.assertTrue(any('page=2&' in x and '/issues?' in x for x in calls))
        self.assertEqual(result['duplicate_requests'], [3])


if __name__ == '__main__':
    unittest.main()
