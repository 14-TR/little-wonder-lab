"""Durable local receipts. Call begin only while holding the run lock."""
import json
import sqlite3
from pathlib import Path


class Blocked(RuntimeError):
    pass


class Store:
    def __init__(self, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path, timeout=5)
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.executescript('''
            CREATE TABLE IF NOT EXISTS attempts (
                id INTEGER PRIMARY KEY, day TEXT NOT NULL, status TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS releases (
                day TEXT PRIMARY KEY, attempt INTEGER NOT NULL, receipt TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS checkpoint (
                singleton INTEGER PRIMARY KEY CHECK(singleton=1), data TEXT NOT NULL);
        ''')

    def close(self):
        self.db.close()

    def attempts(self, day):
        return self.db.execute('SELECT count(*) FROM attempts WHERE day=?', (day,)).fetchone()[0]

    def pending(self):
        row = self.db.execute('SELECT data FROM checkpoint WHERE singleton=1').fetchone()
        return json.loads(row[0]) if row else {}

    def begin(self, day):
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            decision = self.gate(day)
            if not decision['wakeAgent']:
                raise Blocked(decision['reason'])
            self.db.execute("UPDATE attempts SET status='interrupted' WHERE status='running'")
            return self.db.execute("INSERT INTO attempts(day,status) VALUES (?, 'running')", (day,)).lastrowid

    def gate(self, day):
        if self.db.execute('SELECT 1 FROM releases WHERE day=?', (day,)).fetchone():
            return {'wakeAgent': False, 'reason': 'daily target already verified'}
        if self.attempts(day) >= 2:
            return {'wakeAgent': False, 'reason': 'daily attempt limit'}
        return {'wakeAgent': True, 'reason': 'recover checkpoint' if self.pending() else 'daily target due'}

    def finish(self, attempt, status, day=None):
        if status not in {'success', 'blocked', 'interrupted'}:
            raise ValueError('invalid final status')
        with self.db:
            if status == 'success':
                if not day or self.pending().get('stage') != 'live':
                    raise Blocked('live verification receipt required')
                self.db.execute('INSERT INTO releases VALUES (?,?,?)',
                                (day, attempt, json.dumps(self.pending(), sort_keys=True)))
                self.db.execute('DELETE FROM checkpoint')
            self.db.execute('UPDATE attempts SET status=? WHERE id=?', (status, attempt))

    def checkpoint(self, attempt, data):
        with self.db:
            if not self.db.execute("SELECT 1 FROM attempts WHERE id=? AND status='running'", (attempt,)).fetchone():
                raise Blocked('attempt is not running')
            self.db.execute('INSERT OR REPLACE INTO checkpoint VALUES (1,?)', (json.dumps(data, sort_keys=True),))
