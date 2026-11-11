"""Workspace-contained SQLite records. No production paths or environment credentials."""
import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from relay.core import now, canonical, digest

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'

@contextmanager
def connect():
    if DATA.is_symlink():
        raise ValueError('Data directory cannot be a symlink')
    DATA.mkdir(exist_ok=True)
    path = DATA / 'relay.sqlite3'
    if path.is_symlink():
        raise ValueError('Database cannot be a symlink')
    db = sqlite3.connect(path, timeout=15)
    db.row_factory = sqlite3.Row
    db.executescript('''
    CREATE TABLE IF NOT EXISTS observations(id TEXT PRIMARY KEY, market TEXT, observed_at TEXT, payload TEXT);
    CREATE TABLE IF NOT EXISTS current_records(id TEXT PRIMARY KEY, market TEXT, payload TEXT);
    CREATE TABLE IF NOT EXISTS source_runs(id INTEGER PRIMARY KEY, market TEXT, at TEXT, status TEXT, count INTEGER, detail TEXT);
    CREATE TABLE IF NOT EXISTS plans(id TEXT PRIMARY KEY, created_at TEXT, payload TEXT);
    ''')
    try:
        with db:
            yield db
    finally:
        db.close()

def save_source(market, records, status, detail):
    with connect() as db:
        db.execute('INSERT INTO source_runs(market,at,status,count,detail) VALUES(?,?,?,?,?)', (market,now(),status,len(records),detail))
        if status == 'OK':
            # A successful source refresh atomically replaces its listing set. Failure preserves prior evidence.
            db.execute('DELETE FROM current_records WHERE market=?', (market,))
            for record in records:
                payload = canonical(record)
                db.execute('INSERT OR IGNORE INTO observations VALUES(?,?,?,?)', (digest(record),market,record['observed_at'],payload))
                db.execute('INSERT INTO current_records VALUES(?,?,?)', (record['id'],market,payload))

def records():
    with connect() as db:
        return [json.loads(row['payload']) for row in db.execute('SELECT payload FROM current_records ORDER BY market,id')]

def runs():
    with connect() as db:
        return [dict(row) for row in db.execute('SELECT * FROM source_runs WHERE id IN (SELECT MAX(id) FROM source_runs GROUP BY market) ORDER BY market')]

def save_plan(plan):
    with connect() as db:
        db.execute('INSERT OR IGNORE INTO plans VALUES(?,?,?)', (plan['id'],now(),canonical(plan)))
        return json.loads(db.execute('SELECT payload FROM plans WHERE id=?', (plan['id'],)).fetchone()['payload'])

def plans():
    with connect() as db:
        return [json.loads(row['payload']) for row in db.execute('SELECT payload FROM plans ORDER BY created_at DESC LIMIT 50')]
