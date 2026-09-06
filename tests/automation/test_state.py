"""Behavioral tests use real SQLite and OS locks, never profile state."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class StateTests(unittest.TestCase):
    def test_success_stops_same_day_but_not_next_day(self):
        import sys
        sys.path.insert(0, str(ROOT / 'scripts'))
        from autonomy_state import Store, Blocked
        with tempfile.TemporaryDirectory() as tmp:
            db = Store(Path(tmp) / 'state.sqlite3')
            self.assertTrue(hasattr(db, 'finish'), 'finish receipt is missing')
            attempt = db.begin('2026-09-06')
            db.checkpoint(attempt, {'item': 'request-42', 'stage': 'live'})
            db.finish(attempt, 'success', day='2026-09-07')
            self.assertEqual(db.gate('2026-09-07'), {'wakeAgent': False, 'reason': 'daily target already verified'})
            self.assertTrue(db.gate('2026-09-08')['wakeAgent'])
            self.assertEqual(db.pending(), {})
            with self.assertRaises(Blocked):
                db.begin('2026-09-07')
            db.close()

    def test_attempt_limit_survives_restart_and_recovers_checkpoint(self):
        spec = importlib.util.spec_from_file_location('state', ROOT / 'scripts' / 'autonomy_state.py')
        self.assertTrue(Path(spec.origin).exists(), 'durable state implementation is missing')
        state = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(state)
        with tempfile.TemporaryDirectory() as tmp:
            db = state.Store(Path(tmp) / 'state.sqlite3')
            first = db.begin('2026-09-06')
            db.checkpoint(first, {'item': 'request-42', 'stage': 'planned'})
            db.close()
            db = state.Store(Path(tmp) / 'state.sqlite3')
            self.assertEqual(db.pending()['item'], 'request-42')
            second = db.begin('2026-09-06')
            self.assertNotEqual(first, second)
            with self.assertRaises(state.Blocked):
                db.begin('2026-09-06')
            self.assertEqual(db.attempts('2026-09-06'), 2)
            db.close()


if __name__ == '__main__':
    unittest.main()
