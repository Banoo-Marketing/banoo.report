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

        CREATE TABLE IF NOT EXISTS revenue_streams (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL,
            stream_type TEXT DEFAULT 'retainer',
            monthly_revenue REAL DEFAULT 0,
            growth_rate REAL DEFAULT 0,
            time_hours  REAL DEFAULT 0,
            roi_score   REAL DEFAULT 5,
            status      TEXT DEFAULT 'active',
            notes       TEXT,
            updated_at  TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS initiatives (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL,
            objective   TEXT,
            roi_level   TEXT DEFAULT 'medium',
            time_hours  REAL DEFAULT 0,
            deadline    TEXT,
            kill_condition TEXT,
            status      TEXT DEFAULT 'active',
            kill_reason TEXT,
            roi_score   REAL DEFAULT 5,
            updated_at  TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS decision_log (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            title        TEXT NOT NULL,
            reason       TEXT,
            expected_outcome TEXT,
            risk         TEXT,
            review_date  TEXT,
            outcome      TEXT,
            created_at   TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS weekly_metrics (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            week_start      TEXT UNIQUE,
            revenue_produced REAL DEFAULT 0,
            deep_work_hours REAL DEFAULT 0,
            tasks_completed INTEGER DEFAULT 0,
            bottlenecks     INTEGER DEFAULT 0,
            systems_improved INTEGER DEFAULT 0,
            context_switches INTEGER DEFAULT 0,
            energy_score    INTEGER DEFAULT 5,
            focus_score     INTEGER DEFAULT 5,
            notes           TEXT,
            created_at      TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS pipeline_metrics (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            week_start      TEXT UNIQUE,
            leads_generated INTEGER DEFAULT 0,
            calls_booked    INTEGER DEFAULT 0,
            calls_completed INTEGER DEFAULT 0,
            proposals_sent  INTEGER DEFAULT 0,
            deals_closed    INTEGER DEFAULT 0,
            revenue_closed  REAL DEFAULT 0,
            created_at      TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS strategic_options (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            name            TEXT NOT NULL,
            roi_potential   INTEGER DEFAULT 5,
            time_to_revenue INTEGER DEFAULT 90,
            complexity      INTEGER DEFAULT 5,
            fit_score       INTEGER DEFAULT 5,
            status          TEXT DEFAULT 'watching',
            notes           TEXT,
            updated_at      TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS systems_inventory (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL,
            category    TEXT DEFAULT 'other',
            auto_status TEXT DEFAULT 'manual',
            roi_score   INTEGER DEFAULT 5,
            dep_risk    TEXT DEFAULT 'medium',
            maint_hours REAL DEFAULT 0,
            notes       TEXT,
            status      TEXT DEFAULT 'active',
            updated_at  TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS daily_queue (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            title       TEXT NOT NULL,
            outcome     TEXT,
            rev_impact  TEXT DEFAULT 'indirect',
            status      TEXT DEFAULT 'pending',
            queue_date  TEXT DEFAULT (date('now')),
            created_at  TEXT DEFAULT (datetime('now'))
        );
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


# ── Revenue streams ───────────────────────────────────────────────────────────

def get_revenue_streams(status: str = "active") -> list[dict]:
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM revenue_streams WHERE status=? ORDER BY monthly_revenue DESC", (status,)
        ).fetchall()
    return [dict(r) for r in rows]


def upsert_revenue_stream(d: dict) -> int:
    with _conn() as c:
        if d.get("id"):
            c.execute("""UPDATE revenue_streams SET name=?,stream_type=?,monthly_revenue=?,
                growth_rate=?,time_hours=?,roi_score=?,status=?,notes=?,updated_at=datetime('now')
                WHERE id=?""",
                (d["name"], d.get("stream_type","retainer"), d.get("monthly_revenue",0),
                 d.get("growth_rate",0), d.get("time_hours",0), d.get("roi_score",5),
                 d.get("status","active"), d.get("notes",""), d["id"]))
            return d["id"]
        cur = c.execute("""INSERT INTO revenue_streams
            (name,stream_type,monthly_revenue,growth_rate,time_hours,roi_score,status,notes)
            VALUES (?,?,?,?,?,?,?,?)""",
            (d["name"], d.get("stream_type","retainer"), d.get("monthly_revenue",0),
             d.get("growth_rate",0), d.get("time_hours",0), d.get("roi_score",5),
             d.get("status","active"), d.get("notes","")))
        return cur.lastrowid


def delete_revenue_stream(stream_id: int):
    with _conn() as c:
        c.execute("UPDATE revenue_streams SET status='killed',updated_at=datetime('now') WHERE id=?", (stream_id,))


# ── Initiatives ───────────────────────────────────────────────────────────────

def get_initiatives(status: str = "active") -> list[dict]:
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM initiatives WHERE status=? ORDER BY roi_score DESC", (status,)
        ).fetchall()
    return [dict(r) for r in rows]


def get_all_initiatives() -> list[dict]:
    with _conn() as c:
        rows = c.execute("SELECT * FROM initiatives ORDER BY status ASC, roi_score DESC").fetchall()
    return [dict(r) for r in rows]


def upsert_initiative(d: dict) -> int:
    with _conn() as c:
        if d.get("id"):
            c.execute("""UPDATE initiatives SET name=?,objective=?,roi_level=?,time_hours=?,
                deadline=?,kill_condition=?,status=?,kill_reason=?,roi_score=?,updated_at=datetime('now')
                WHERE id=?""",
                (d["name"], d.get("objective",""), d.get("roi_level","medium"),
                 d.get("time_hours",0), d.get("deadline",""), d.get("kill_condition",""),
                 d.get("status","active"), d.get("kill_reason",""), d.get("roi_score",5), d["id"]))
            return d["id"]
        cur = c.execute("""INSERT INTO initiatives
            (name,objective,roi_level,time_hours,deadline,kill_condition,roi_score)
            VALUES (?,?,?,?,?,?,?)""",
            (d["name"], d.get("objective",""), d.get("roi_level","medium"),
             d.get("time_hours",0), d.get("deadline",""), d.get("kill_condition",""),
             d.get("roi_score",5)))
        return cur.lastrowid


def kill_initiative(initiative_id: int, reason: str = ""):
    with _conn() as c:
        c.execute("""UPDATE initiatives SET status='killed',kill_reason=?,updated_at=datetime('now')
            WHERE id=?""", (reason, initiative_id))


# ── Decision log ──────────────────────────────────────────────────────────────

def get_decisions(limit: int = 20) -> list[dict]:
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM decision_log ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]


def add_decision(d: dict) -> int:
    with _conn() as c:
        cur = c.execute("""INSERT INTO decision_log
            (title,reason,expected_outcome,risk,review_date,outcome)
            VALUES (?,?,?,?,?,?)""",
            (d["title"], d.get("reason",""), d.get("expected_outcome",""),
             d.get("risk",""), d.get("review_date",""), d.get("outcome","")))
        return cur.lastrowid


def update_decision_outcome(decision_id: int, outcome: str):
    with _conn() as c:
        c.execute("UPDATE decision_log SET outcome=? WHERE id=?", (outcome, decision_id))


# ── Weekly metrics ────────────────────────────────────────────────────────────

def get_weekly_metrics(weeks: int = 8) -> list[dict]:
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM weekly_metrics ORDER BY week_start DESC LIMIT ?", (weeks,)
        ).fetchall()
    return [dict(r) for r in rows]


def upsert_weekly_metrics(d: dict):
    with _conn() as c:
        c.execute("""INSERT INTO weekly_metrics
            (week_start,revenue_produced,deep_work_hours,tasks_completed,bottlenecks,
             systems_improved,context_switches,energy_score,focus_score,notes)
            VALUES (?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(week_start) DO UPDATE SET
            revenue_produced=excluded.revenue_produced,
            deep_work_hours=excluded.deep_work_hours,
            tasks_completed=excluded.tasks_completed,
            bottlenecks=excluded.bottlenecks,
            systems_improved=excluded.systems_improved,
            context_switches=excluded.context_switches,
            energy_score=excluded.energy_score,
            focus_score=excluded.focus_score,
            notes=excluded.notes""",
            (d["week_start"], d.get("revenue_produced",0), d.get("deep_work_hours",0),
             d.get("tasks_completed",0), d.get("bottlenecks",0), d.get("systems_improved",0),
             d.get("context_switches",0), d.get("energy_score",5), d.get("focus_score",5),
             d.get("notes","")))


# ── Pipeline metrics ──────────────────────────────────────────────────────────

def get_pipeline_metrics(weeks: int = 8) -> list[dict]:
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM pipeline_metrics ORDER BY week_start DESC LIMIT ?", (weeks,)
        ).fetchall()
    return [dict(r) for r in rows]


def upsert_pipeline_metrics(d: dict):
    with _conn() as c:
        c.execute("""INSERT INTO pipeline_metrics
            (week_start,leads_generated,calls_booked,calls_completed,proposals_sent,deals_closed,revenue_closed)
            VALUES (?,?,?,?,?,?,?)
            ON CONFLICT(week_start) DO UPDATE SET
            leads_generated=excluded.leads_generated,
            calls_booked=excluded.calls_booked,
            calls_completed=excluded.calls_completed,
            proposals_sent=excluded.proposals_sent,
            deals_closed=excluded.deals_closed,
            revenue_closed=excluded.revenue_closed""",
            (d["week_start"], d.get("leads_generated",0), d.get("calls_booked",0),
             d.get("calls_completed",0), d.get("proposals_sent",0),
             d.get("deals_closed",0), d.get("revenue_closed",0)))


# ── Strategic options ─────────────────────────────────────────────────────────

def get_strategic_options(status: str = None) -> list[dict]:
    with _conn() as c:
        if status:
            rows = c.execute(
                "SELECT * FROM strategic_options WHERE status=? ORDER BY fit_score DESC", (status,)
            ).fetchall()
        else:
            rows = c.execute(
                "SELECT * FROM strategic_options ORDER BY status ASC, fit_score DESC"
            ).fetchall()
    return [dict(r) for r in rows]


def upsert_strategic_option(d: dict) -> int:
    with _conn() as c:
        if d.get("id"):
            c.execute("""UPDATE strategic_options SET name=?,roi_potential=?,time_to_revenue=?,
                complexity=?,fit_score=?,status=?,notes=?,updated_at=datetime('now') WHERE id=?""",
                (d["name"], d.get("roi_potential",5), d.get("time_to_revenue",90),
                 d.get("complexity",5), d.get("fit_score",5), d.get("status","watching"),
                 d.get("notes",""), d["id"]))
            return d["id"]
        cur = c.execute("""INSERT INTO strategic_options
            (name,roi_potential,time_to_revenue,complexity,fit_score,status,notes)
            VALUES (?,?,?,?,?,?,?)""",
            (d["name"], d.get("roi_potential",5), d.get("time_to_revenue",90),
             d.get("complexity",5), d.get("fit_score",5), d.get("status","watching"),
             d.get("notes","")))
        return cur.lastrowid


# ── Systems inventory ─────────────────────────────────────────────────────────

def get_systems(status: str = "active") -> list[dict]:
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM systems_inventory WHERE status=? ORDER BY roi_score DESC", (status,)
        ).fetchall()
    return [dict(r) for r in rows]


def upsert_system(d: dict) -> int:
    with _conn() as c:
        if d.get("id"):
            c.execute("""UPDATE systems_inventory SET name=?,category=?,auto_status=?,roi_score=?,
                dep_risk=?,maint_hours=?,notes=?,status=?,updated_at=datetime('now') WHERE id=?""",
                (d["name"], d.get("category","other"), d.get("auto_status","manual"),
                 d.get("roi_score",5), d.get("dep_risk","medium"), d.get("maint_hours",0),
                 d.get("notes",""), d.get("status","active"), d["id"]))
            return d["id"]
        cur = c.execute("""INSERT INTO systems_inventory
            (name,category,auto_status,roi_score,dep_risk,maint_hours,notes)
            VALUES (?,?,?,?,?,?,?)""",
            (d["name"], d.get("category","other"), d.get("auto_status","manual"),
             d.get("roi_score",5), d.get("dep_risk","medium"), d.get("maint_hours",0),
             d.get("notes","")))
        return cur.lastrowid


# ── Daily queue ───────────────────────────────────────────────────────────────

def get_daily_queue(date: str = None) -> list[dict]:
    with _conn() as c:
        if date:
            rows = c.execute(
                "SELECT * FROM daily_queue WHERE queue_date=? ORDER BY id ASC", (date,)
            ).fetchall()
        else:
            rows = c.execute(
                "SELECT * FROM daily_queue WHERE queue_date=date('now') ORDER BY id ASC"
            ).fetchall()
    return [dict(r) for r in rows]


def add_queue_item(d: dict) -> int:
    with _conn() as c:
        cur = c.execute("""INSERT INTO daily_queue (title,outcome,rev_impact,queue_date)
            VALUES (?,?,?,?)""",
            (d["title"], d.get("outcome",""), d.get("rev_impact","indirect"),
             d.get("queue_date", "date('now')")))
        return cur.lastrowid


def update_queue_status(item_id: int, status: str):
    with _conn() as c:
        c.execute("UPDATE daily_queue SET status=? WHERE id=?", (status, item_id))


def delete_queue_item(item_id: int):
    with _conn() as c:
        c.execute("DELETE FROM daily_queue WHERE id=?", (item_id,))


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
