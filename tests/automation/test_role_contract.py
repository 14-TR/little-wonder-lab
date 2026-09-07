"""Regression checks for the executable lead/planner timing contract.

These check prompt instructions, not provider latency or a live lesson release.
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class RoleContractTests(unittest.TestCase):
    def test_phase_allocations_fit_lead_budget_with_real_planning_window(self):
        lead = (ROOT / 'automation/roles/lead.md').read_text()
        # Keep the human-readable schedule machine-checkable without runtime changes.
        rows = re.findall(r'^\| (Selection|Planner|Engineering and gates|Independent review|Release|Buffer) \| (\d+) \|', lead, re.M)
        budget = {name: int(seconds) for name, seconds in rows}
        self.assertEqual(len(rows), 6, 'explicit non-overlapping phase allocations required')
        self.assertEqual(len(budget), 6)
        self.assertEqual(sum(budget.values()), 2100)
        self.assertGreaterEqual(budget['Planner'], 360, 'three minutes interrupted observed provider response')
        self.assertGreaterEqual(budget['Engineering and gates'], 780)
        self.assertGreaterEqual(budget['Independent review'], 360)
        self.assertGreaterEqual(budget['Release'], 420)
        self.assertGreaterEqual(budget['Buffer'], 120)
        self.assertNotRegex(lead, r'3-minute|Three-minute|three-minute')
        self.assertIn('2400', lead)

    def test_new_item_can_receive_a_planner_chosen_lesson_id(self):
        for relative in ('automation/roles/lead.md', 'automation/roles/planner.md'):
            text = (ROOT / relative).read_text()
            self.assertIn('new item', text)
            self.assertIn('unique lesson_id', text)
            self.assertIn('resumed item', text)

    def test_planner_handoff_is_compact_bound_and_fail_closed(self):
        lead = (ROOT / 'automation/roles/lead.md').read_text()
        planner = (ROOT / 'automation/roles/planner.md').read_text()
        docs = (ROOT / 'docs/AUTONOMY.md').read_text()
        for text in (lead, planner, docs):
            with self.subTest(document=text.splitlines()[0]):
                self.assertIn('360', text)
                self.assertIn('1200 words', text)
                self.assertIn('12000 UTF-8 bytes', text)
        for field in ('status', 'complete', 'item', 'lesson_id', 'base',
                      'learning_objective', 'prerequisites', 'child_explanation',
                      'activity_safety', 'interaction', 'sources', 'allowed_files',
                      'acceptance_tests', 'roadmap_update', 'curriculum_update',
                      'substantive_rationale', 'risks'):
            self.assertIn(f'`{field}`', planner)
        self.assertIn('status=ready', lead)
        self.assertIn('complete=true', lead)
        self.assertIn('not a release verdict', planner)
        self.assertIn('missing, oversized, malformed, stale or incomplete', lead)
        self.assertIn('No baseline tests', planner)
        self.assertIn('source bodies', planner)
        self.assertNotRegex(planner, r'Three-minute|three-minute|3-minute')


if __name__ == '__main__':
    unittest.main()
