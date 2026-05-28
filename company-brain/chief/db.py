"""
db.py — SQLite database for the Chief of Staff system.
Shares the email analyzer cache (read-only) and adds its own tables.
"""
import sqlite3
import json
from contextlib import contextmanager
from pathlib import Path

_HERE = Path(__file__).parent
DB_PATH = _HERE / "chief.db"
EMAIL_CACHE_PATH = _HERE.parent / "email-analyzer" / "email_cache.db"


def init():
    with _conn() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS contacts (
            email           TEXT PRIMARY KEY,
            name            TEXT,
            company         TEXT,
            role            TEXT,
            relationship    TEXT,   -- Family|Close friend|Key business partner|Client (Banoo)|Lead|Vendor|Acquaintance|Needs rekindling|Mentor/Advisor
            how_we_met      TEXT,
            strength        REAL DEFAULT 0,   -- 0-10 score
            email_count     INTEGER DEFAULT 0,
            last_contact    TEXT,
            first_contact   TEXT,
            sentiment_avg   REAL DEFAULT 0,
            obligations     TEXT,   -- JSON list of strings
            notes           TEXT,
            nurture_score   REAL DEFAULT 0,
            is_business_owner INTEGER DEFAULT 0,
            suggested_action TEXT,
            updated_at      TEXT
        );

        CREATE TABLE IF NOT EXISTS actions (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            title           TEXT NOT NULL,
            from_email      TEXT,
            from_name       TEXT,
            gmail_id        TEXT,
            deadline        TEXT,
            priority        TEXT DEFAULT 'MEDIUM',  -- HIGH|MEDIUM|LOW
            status          TEXT DEFAULT 'OPEN',    -- OPEN|DONE|SNOOZED
            action_type     TEXT,  -- task|followup|promise|decision
            suggested_next  TEXT,
            created_at      TEXT DEFAULT (datetime('now')),
            snoozed_until   TEXT
        );

        CREATE TABLE IF NOT EXISTS calendar_events (
            event_id        TEXT PRIMARY KEY,
            title           TEXT,
            start_time      TEXT,
            end_time        TEXT,
            attendees       TEXT,   -- JSON list
            description     TEXT,
            location        TEXT,
            is_recurring    INTEGER DEFAULT 0,
            fetched_at      TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS briefs (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            generated_at    TEXT,
            content         TEXT,   -- JSON brief data
            delivered       INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS sync_state (
            key     TEXT PRIMARY KEY,
            value   TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_contacts_strength ON contacts(strength DESC);
        CREATE INDEX IF NOT EXISTS idx_actions_priority ON actions(priority, status);
        CREATE INDEX IF NOT EXISTS idx_calendar_start ON calendar_events(start_time);
        """)


@contextmanager
def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


# ── Contacts ──────────────────────────────────────────────────────────────────

def upsert_contact(c: dict):
    with _conn() as conn:
        existing = conn.execute("SELECT * FROM contacts WHERE email=?", (c["email"],)).fetchone()
        if existing:
            conn.execute("""
            UPDATE contacts SET
                name=COALESCE(?,name), company=COALESCE(NULLIF(?,\"\"),company),
                role=COALESCE(NULLIF(?,\"\"),role), relationship=COALESCE(NULLIF(?,\"\"),relationship),
                how_we_met=COALESCE(NULLIF(?,\"\"),how_we_met), strength=MAX(strength,?),
                email_count=?, last_contact=COALESCE(NULLIF(?,\"\"),last_contact),
                first_contact=COALESCE(NULLIF(?,\"\"),first_contact), obligations=COALESCE(?,obligations),
                nurture_score=MAX(nurture_score,?),
                is_business_owner=MAX(is_business_owner,?),
                suggested_action=COALESCE(NULLIF(?,\"\"),suggested_action), updated_at=datetime('now')
            WHERE email=?
            """, (
                c.get("name"), c.get("company"), c.get("role"), c.get("relationship"),
                c.get("how_we_met"), c.get("strength", 0), c.get("email_count", 0),
                c.get("last_contact"), c.get("first_contact"),
                json.dumps(c.get("obligations", [])) if c.get("obligations") else None,
                c.get("nurture_score") or 0, c.get("is_business_owner") or 0,
                c.get("suggested_action"), c["email"],
            ))
        else:
            conn.execute("""
            INSERT INTO contacts
              (email,name,company,role,relationship,how_we_met,strength,email_count,
               last_contact,first_contact,obligations,nurture_score,is_business_owner,
               suggested_action,updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,datetime('now'))
            """, (
                c["email"], c.get("name",""), c.get("company",""), c.get("role",""),
                c.get("relationship","Acquaintance"), c.get("how_we_met",""),
                c.get("strength",0), c.get("email_count",1),
                c.get("last_contact",""), c.get("first_contact",""),
                json.dumps(c.get("obligations",[])),
                c.get("nurture_score",0), c.get("is_business_owner",0),
                c.get("suggested_action",""),
            ))


def get_contacts(relationship: str = None, min_strength: float = 0, limit: int = 100) -> list[dict]:
    with _conn() as c:
        q = "SELECT * FROM contacts WHERE strength >= ?"
        params = [min_strength]
        if relationship:
            q += " AND relationship=?"
            params.append(relationship)
        q += " ORDER BY strength DESC, email_count DESC LIMIT ?"
        params.append(limit)
        return [dict(r) for r in c.execute(q, params).fetchall()]


def get_contact(email: str) -> dict | None:
    with _conn() as c:
        row = c.execute("SELECT * FROM contacts WHERE email=?", (email,)).fetchone()
    return dict(row) if row else None


def get_top_contacts(n: int = 20) -> list[dict]:
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM contacts ORDER BY strength DESC, email_count DESC LIMIT ?", (n,)
        ).fetchall()
    return [dict(r) for r in rows]


def get_dormant_contacts(days: int = 180) -> list[dict]:
    with _conn() as c:
        rows = c.execute("""
        SELECT * FROM contacts
        WHERE last_contact < date('now', ? || ' days')
          AND strength >= 3
        ORDER BY strength DESC
        """, (f"-{days}",)).fetchall()
    return [dict(r) for r in rows]


# ── Actions ───────────────────────────────────────────────────────────────────

def add_action(a: dict) -> int:
    with _conn() as c:
        cur = c.execute("""
        INSERT INTO actions (title, from_email, from_name, gmail_id, deadline,
          priority, action_type, suggested_next)
        VALUES (?,?,?,?,?,?,?,?)
        """, (
            a["title"], a.get("from_email",""), a.get("from_name",""),
            a.get("gmail_id",""), a.get("deadline",""),
            a.get("priority","MEDIUM"), a.get("action_type","task"),
            a.get("suggested_next",""),
        ))
        return cur.lastrowid


def get_actions(status: str = "OPEN", priority: str = None, limit: int = 50) -> list[dict]:
    with _conn() as c:
        q = "SELECT * FROM actions WHERE status=?"
        params = [status]
        if priority:
            q += " AND priority=?"
            params.append(priority)
        q += " ORDER BY CASE priority WHEN 'HIGH' THEN 1 WHEN 'MEDIUM' THEN 2 ELSE 3 END, deadline ASC LIMIT ?"
        params.append(limit)
        return [dict(r) for r in c.execute(q, params).fetchall()]


def update_action_status(action_id: int, status: str):
    with _conn() as c:
        c.execute("UPDATE actions SET status=? WHERE id=?", (status, action_id))


# ── Calendar ──────────────────────────────────────────────────────────────────

def upsert_event(e: dict):
    with _conn() as c:
        c.execute("""
        INSERT OR REPLACE INTO calendar_events
          (event_id, title, start_time, end_time, attendees, description, location, is_recurring)
        VALUES (?,?,?,?,?,?,?,?)
        """, (
            e["event_id"], e.get("title",""), e.get("start_time",""), e.get("end_time",""),
            json.dumps(e.get("attendees",[])), e.get("description",""),
            e.get("location",""), e.get("is_recurring",0),
        ))


def get_upcoming_events(days: int = 7) -> list[dict]:
    with _conn() as c:
        rows = c.execute("""
        SELECT * FROM calendar_events
        WHERE start_time >= datetime('now')
          AND start_time <= datetime('now', ? || ' days')
        ORDER BY start_time ASC
        """, (f"+{days}",)).fetchall()
    return [dict(r) for r in rows]


# ── Sync state ────────────────────────────────────────────────────────────────

def get_sync_state(key: str, default=None):
    with _conn() as c:
        row = c.execute("SELECT value FROM sync_state WHERE key=?", (key,)).fetchone()
    return row[0] if row else default


def set_sync_state(key: str, value: str):
    with _conn() as c:
        c.execute("INSERT OR REPLACE INTO sync_state (key,value) VALUES (?,?)", (key, value))


# ── Stats ─────────────────────────────────────────────────────────────────────

def stats() -> dict:
    with _conn() as c:
        return {
            "contacts": c.execute("SELECT COUNT(*) FROM contacts").fetchone()[0],
            "actions_open": c.execute("SELECT COUNT(*) FROM actions WHERE status='OPEN'").fetchone()[0],
            "actions_total": c.execute("SELECT COUNT(*) FROM actions").fetchone()[0],
            "calendar_events": c.execute("SELECT COUNT(*) FROM calendar_events").fetchone()[0],
            "briefs": c.execute("SELECT COUNT(*) FROM briefs").fetchone()[0],
        }
