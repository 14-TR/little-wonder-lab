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
        self.assertGreaterEqual(budget['Engineering and gates'], 720)
        engineer = re.search(r'a tighter (\d+)-minute/35-tool-call budget', lead)
        gates = re.search(r'reserve the other (\d+) seconds of this stage for lead gates', lead)
        assert engineer is not None and gates is not None, 'explicit engineer/gate split required'
        self.assertEqual(int(engineer[1]) * 60 + int(gates[1]), budget['Engineering and gates'])
        self.assertGreaterEqual(int(gates[1]), 180, 'selection must not consume mandatory lead gates')
        self.assertGreaterEqual(budget['Independent review'], 360)
        self.assertGreaterEqual(budget['Release'], 420)
        self.assertGreaterEqual(budget['Buffer'], 120)
        self.assertNotRegex(lead, r'3-minute|Three-minute|three-minute')
        self.assertIn('2400', lead)

    def test_selection_and_engineering_admission_boundaries(self):
        lead = (ROOT / 'automation/roles/lead.md').read_text()
        rows = re.findall(r'^\| (Selection|Planner|Engineering and gates|Independent review|Release|Buffer) \| (\d+) \| (\d+) \|$', lead, re.M)
        budget = {name: int(seconds) for name, seconds, _ in rows}
        elapsed = 0
        for name, seconds, finish in rows:
            elapsed += int(seconds)
            self.assertEqual(elapsed, int(finish), name)
        admission = re.search(r'Before engineering require at least (\d+) seconds remaining', lead)
        assert admission is not None, 'explicit engineering admission threshold required'
        reserve = int(admission[1])
        downstream = sum(budget[name] for name in (
            'Engineering and gates', 'Independent review', 'Release', 'Buffer'))
        self.assertEqual(reserve, downstream, 'all downstream allocations must remain reserved')
        self.assertIn('If selection cannot finish in its allocation', lead)

        # Model the actual prompt admission rules, including lead handoff time.
        # This is an offline contract regression, not a runtime enforcement test.
        def admitted(selection, planning, handoff: float = 0):
            return (selection <= budget['Selection']
                    and planning <= budget['Planner']
                    and elapsed - selection - planning - handoff >= reserve)

        self.assertTrue(admitted(65, 360), 'ordinary selection must leave the full planner window')
        handoff_room = elapsed - reserve - 65 - 360
        self.assertGreaterEqual(handoff_room, 0)
        self.assertTrue(admitted(65, 360, handoff_room), 'exact full downstream reserve fits')
        self.assertFalse(admitted(65, 360, handoff_room + 0.001), 'never borrow downstream reserves')
        self.assertTrue(admitted(budget['Selection'], 360))
        self.assertFalse(admitted(budget['Selection'] + 0.001, 360))
        self.assertFalse(admitted(65, 360.001), 'planner window remains bounded')

    def test_recovery_binds_pr_before_calling_strict_merge_helper(self):
        lead = (ROOT / 'automation/roles/lead.md').read_text()
        self.assertIn('If the pending checkpoint lacks `pr`', lead)
        self.assertIn('before `recover-merged`', lead)
        self.assertIn('Never call scripts/reconcile_completed.py from a supervised attempt', lead)
        docs = (ROOT / 'docs/AUTONOMY.md').read_text()
        for text in (lead, docs):
            self.assertIn('owner-only reconciliation', text)
            self.assertIn('evidence-<sha>.json', text)
            self.assertIn('public text or dates', text)

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
