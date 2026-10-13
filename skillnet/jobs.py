"""SQLite durable job leases. Lost workers are recorded, never silently retried."""
from __future__ import annotations
import json
from pathlib import Path
import sqlite3
import time


class JobQueue:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute('PRAGMA journal_mode=WAL')
            db.execute('CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, payload TEXT NOT NULL, '
                       'state TEXT NOT NULL, created REAL NOT NULL, owner TEXT, lease REAL, error TEXT, cancel INTEGER DEFAULT 0)')
            db.execute('CREATE TABLE IF NOT EXISTS request_nonces (nonce TEXT PRIMARY KEY, expires REAL NOT NULL)')

    def consume_nonce(self, nonce):
        with self.connect() as db:
            db.execute('DELETE FROM request_nonces WHERE expires<?', (time.time(),))
            try:
                db.execute('INSERT INTO request_nonces VALUES(?,?)', (nonce, time.time()+245))
            except sqlite3.IntegrityError:
                return False
            return True

    def interrupt_unfinished(self):
        # Thread mode owns all jobs in this process. Never silently replay paid calls.
        with self.connect() as db:
            db.execute('UPDATE jobs SET state="interrupted",lease=NULL,error="API process restarted; resubmit explicitly" '
                       'WHERE state IN ("queued","running")')

    def connect(self):
        db = sqlite3.connect(self.path, timeout=15)
        db.row_factory = sqlite3.Row
        return db

    def enqueue(self, run_id, payload):
        with self.connect() as db:
            db.execute('INSERT INTO jobs(id,payload,state,created) VALUES(?,?,?,?)',
                       (run_id, json.dumps(payload, ensure_ascii=False), 'queued', time.time()))

    def claim(self, owner, *, run_id=None, lease_seconds=45):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT * FROM jobs WHERE state="queued" AND cancel=0 ' +
                             ('AND id=? ' if run_id else '') + 'ORDER BY created LIMIT 1',
                             (run_id,) if run_id else ()).fetchone()
            if row is None:
                return None
            db.execute('UPDATE jobs SET state="running",owner=?,lease=? WHERE id=?',
                       (owner, time.time() + lease_seconds, row['id']))
            return dict(row) | {'payload': json.loads(row['payload'])}

    def heartbeat(self, run_id, owner, lease_seconds=45):
        with self.connect() as db:
            return db.execute('UPDATE jobs SET lease=? WHERE id=? AND owner=? AND state="running"',
                              (time.time()+lease_seconds, run_id, owner)).rowcount == 1

    def finish(self, run_id, owner, state='finished', error=''):
        with self.connect() as db:
            return db.execute('UPDATE jobs SET state=?,error=?,lease=NULL WHERE id=? AND owner=?',
                              (state, error[:1000], run_id, owner)).rowcount == 1

    def cancel(self, run_id):
        with self.connect() as db:
            db.execute('UPDATE jobs SET cancel=1,state=CASE WHEN state="queued" THEN "cancelled" ELSE state END WHERE id=?', (run_id,))

    def cancelled(self, run_id):
        with self.connect() as db:
            row = db.execute('SELECT cancel FROM jobs WHERE id=?', (run_id,)).fetchone()
            return bool(row and row['cancel'])

    def recover(self):
        with self.connect() as db:
            rows = db.execute('SELECT id FROM jobs WHERE state="running" AND lease<?', (time.time(),)).fetchall()
            db.execute('UPDATE jobs SET state="interrupted",error="Worker lease expired; checkpoints preserved" '
                       'WHERE state="running" AND lease<?', (time.time(),))
            return [r['id'] for r in rows]

    def snapshot(self):
        with self.connect() as db:
            return {r['state']:r['n'] for r in db.execute('SELECT state,COUNT(*) AS n FROM jobs GROUP BY state')}
