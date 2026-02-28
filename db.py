import datetime
import json
import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), 'subscriptions.db')

SCHEMA = """
CREATE TABLE IF NOT EXISTS subscriptions (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    destination       TEXT    NOT NULL,
    subscription_type TEXT    NOT NULL DEFAULT 'discord',
    papers            TEXT    NOT NULL,
    label             TEXT,               -- optional: Discord sender name or email subject modifier
    ip_address        TEXT,
    created_at        TEXT    NOT NULL,
    last_posted_at    TEXT,
    last_error        TEXT,
    consecutive_errors INTEGER NOT NULL DEFAULT 0,
    active            INTEGER NOT NULL DEFAULT 1
);
"""

AUTO_DEACTIVATE_THRESHOLD = 7


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA journal_mode=WAL')
    return conn


def init():
    with _connect() as conn:
        conn.executescript(SCHEMA)


def create_subscription(destination, papers, label, ip_address, subscription_type='discord'):
    now = datetime.datetime.utcnow().isoformat()
    papers_json = json.dumps(papers)
    with _connect() as conn:
        cur = conn.execute(
            """INSERT INTO subscriptions
               (destination, subscription_type, papers, label, ip_address, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (destination, subscription_type, papers_json, label, ip_address, now),
        )
        sub_id = cur.lastrowid
    return get_subscription(sub_id)


def get_subscription(sub_id):
    with _connect() as conn:
        row = conn.execute('SELECT * FROM subscriptions WHERE id = ?', (sub_id,)).fetchone()
    return dict(row) if row else None


def get_active_subscriptions():
    with _connect() as conn:
        rows = conn.execute('SELECT * FROM subscriptions WHERE active = 1').fetchall()
    return [dict(r) for r in rows]


def deactivate_subscription(sub_id):
    with _connect() as conn:
        conn.execute('UPDATE subscriptions SET active = 0 WHERE id = ?', (sub_id,))


def deactivate_by_destination(destination):
    """Deactivate the active subscription for a given destination. Returns True if found."""
    with _connect() as conn:
        cur = conn.execute(
            'UPDATE subscriptions SET active = 0 WHERE destination = ? AND active = 1',
            (destination,),
        )
        return cur.rowcount > 0


def record_success(sub_id, d):
    now = datetime.datetime.utcnow().isoformat()
    with _connect() as conn:
        conn.execute(
            """UPDATE subscriptions
               SET last_posted_at = ?, last_error = NULL, consecutive_errors = 0
               WHERE id = ?""",
            (now, sub_id),
        )


def record_error(sub_id, error_msg):
    with _connect() as conn:
        conn.execute(
            """UPDATE subscriptions
               SET last_error = ?,
                   consecutive_errors = consecutive_errors + 1,
                   active = CASE WHEN consecutive_errors + 1 >= ? THEN 0 ELSE active END
               WHERE id = ?""",
            (error_msg, AUTO_DEACTIVATE_THRESHOLD, sub_id),
        )


if __name__ == '__main__':
    init()
    print(f'Database initialized at {DB_PATH}')
