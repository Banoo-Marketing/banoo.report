"""
cache.py — SQLite cache to avoid re-fetching and re-processing emails.
"""
import sqlite3
import json
from contextlib import contextmanager
from pathlib import Path
import config

_DB = str(config.CACHE_DB)


def init():
    with _conn() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS emails (
            gmail_id    TEXT PRIMARY KEY,
            thread_id   TEXT,
            sender      TEXT,
            recipients  TEXT,
            subject     TEXT,
            date_ts     INTEGER,
            date_str    TEXT,
            body_text   TEXT,
            labels      TEXT,
            fetched_at  INTEGER DEFAULT (strftime('%s','now'))
        );

        CREATE TABLE IF NOT EXISTS processing (
            gmail_id        TEXT PRIMARY KEY,
            categories      TEXT,   -- JSON list of category keys
            summary         TEXT,
            sentiment       TEXT,
            action_items    TEXT,   -- JSON list
            key_people      TEXT,   -- JSON list of {name, email}
            themes          TEXT,   -- JSON list
            processed_at    INTEGER DEFAULT (strftime('%s','now')),
            FOREIGN KEY (gmail_id) REFERENCES emails(gmail_id)
        );

        CREATE INDEX IF NOT EXISTS idx_emails_date ON emails(date_ts);
        CREATE INDEX IF NOT EXISTS idx_emails_sender ON emails(sender);
        """)


@contextmanager
def _conn():
    conn = sqlite3.connect(_DB)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def email_exists(gmail_id: str) -> bool:
    with _conn() as c:
        row = c.execute("SELECT 1 FROM emails WHERE gmail_id=?", (gmail_id,)).fetchone()
    return row is not None


def is_processed(gmail_id: str) -> bool:
    with _conn() as c:
        row = c.execute("SELECT 1 FROM processing WHERE gmail_id=?", (gmail_id,)).fetchone()
    return row is not None


def save_email(email: dict):
    with _conn() as c:
        c.execute("""
        INSERT OR REPLACE INTO emails
          (gmail_id, thread_id, sender, recipients, subject, date_ts, date_str, body_text, labels)
        VALUES (?,?,?,?,?,?,?,?,?)
        """, (
            email["gmail_id"],
            email.get("thread_id", ""),
            email.get("sender", ""),
            json.dumps(email.get("recipients", [])),
            email.get("subject", ""),
            email.get("date_ts", 0),
            email.get("date_str", ""),
            email.get("body_text", "")[:5000],  # cap at 5k chars
            json.dumps(email.get("labels", [])),
        ))


def save_processing(result: dict):
    with _conn() as c:
        c.execute("""
        INSERT OR REPLACE INTO processing
          (gmail_id, categories, summary, sentiment, action_items, key_people, themes)
        VALUES (?,?,?,?,?,?,?)
        """, (
            result["gmail_id"],
            json.dumps(result.get("categories", [])),
            result.get("summary", ""),
            result.get("sentiment", "neutral"),
            json.dumps(result.get("action_items", [])),
            json.dumps(result.get("key_people", [])),
            json.dumps(result.get("themes", [])),
        ))


def get_all_emails(limit: int = 0) -> list[dict]:
    with _conn() as c:
        q = """
        SELECT e.*, p.categories, p.summary, p.sentiment,
               p.action_items, p.key_people, p.themes
        FROM emails e
        LEFT JOIN processing p ON p.gmail_id = e.gmail_id
        ORDER BY e.date_ts DESC
        """
        if limit:
            q += f" LIMIT {limit}"
        rows = c.execute(q).fetchall()
    return [dict(r) for r in rows]


def get_unprocessed(limit: int = 100) -> list[dict]:
    with _conn() as c:
        rows = c.execute("""
        SELECT * FROM emails e
        WHERE NOT EXISTS (SELECT 1 FROM processing p WHERE p.gmail_id = e.gmail_id)
        ORDER BY e.date_ts DESC
        LIMIT ?
        """, (limit,)).fetchall()
    return [dict(r) for r in rows]


def stats() -> dict:
    with _conn() as c:
        total = c.execute("SELECT COUNT(*) FROM emails").fetchone()[0]
        processed = c.execute("SELECT COUNT(*) FROM processing").fetchone()[0]
        oldest = c.execute("SELECT MIN(date_str) FROM emails").fetchone()[0]
        newest = c.execute("SELECT MAX(date_str) FROM emails").fetchone()[0]
    return {"total": total, "processed": processed, "oldest": oldest, "newest": newest}
