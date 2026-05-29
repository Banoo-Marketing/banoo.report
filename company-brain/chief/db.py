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

        CREATE TABLE IF NOT EXISTS agents (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            name            TEXT NOT NULL UNIQUE,
            purpose         TEXT,
            agent_type      TEXT DEFAULT 'generated',  -- native|generated
            native_module   TEXT,   -- for native: module name (e.g. 'pulse')
            native_fn       TEXT,   -- for native: function name
            scope           TEXT,
            inputs          TEXT,   -- JSON list of data sources
            outputs         TEXT,   -- JSON: what it produces
            frequency       TEXT DEFAULT 'weekly',  -- daily|weekly|monthly|triggered
            system_prompt   TEXT,   -- for generated agents
            rules           TEXT,   -- JSON rules
            escalation_rules TEXT,  -- JSON: when to escalate to Emod
            success_metric  TEXT,
            status          TEXT DEFAULT 'active',  -- active|paused|killed
            last_run        TEXT,
            last_output     TEXT,   -- compressed last output JSON
            run_count       INTEGER DEFAULT 0,
            exception_count INTEGER DEFAULT 0,
            kill_reason     TEXT,
            created_at      TEXT DEFAULT (datetime('now')),
            updated_at      TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS agent_outputs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_id    INTEGER NOT NULL,
            agent_name  TEXT,
            ran_at      TEXT DEFAULT (datetime('now')),
            output      TEXT,       -- JSON compressed output
            exceptions  TEXT,       -- JSON list of exceptions found
            has_escalation INTEGER DEFAULT 0,
            escalation_reason TEXT,
            status      TEXT DEFAULT 'new'  -- new|reviewed|acted
        );

        CREATE INDEX IF NOT EXISTS idx_agent_outputs_agent ON agent_outputs(agent_id, ran_at DESC);
        CREATE INDEX IF NOT EXISTS idx_agent_outputs_escalation ON agent_outputs(has_escalation, status);

        CREATE TABLE IF NOT EXISTS action_queue (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            action_type     TEXT NOT NULL,
            permission_level INTEGER NOT NULL DEFAULT 2,
            payload         TEXT NOT NULL,          -- JSON
            source_agent    TEXT DEFAULT '',
            rationale       TEXT DEFAULT '',
            status          TEXT DEFAULT 'pending', -- pending|approved|executed|rejected|failed
            created_at      TEXT DEFAULT (datetime('now')),
            approved_at     TEXT,
            executed_at     TEXT,
            result          TEXT,
            rejected_reason TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_action_queue_status ON action_queue(status, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_action_queue_type ON action_queue(action_type, status);

        CREATE TABLE IF NOT EXISTS feedback_log (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            action_id       INTEGER,
            action_type     TEXT,
            source_agent    TEXT,
            outcome         TEXT,          -- executed|rejected|failed
            rejection_reason TEXT,
            execution_result TEXT,
            permission_level INTEGER,
            signal          TEXT,          -- positive|negative|neutral
            created_at      TEXT DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_feedback_agent ON feedback_log(source_agent, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_feedback_outcome ON feedback_log(outcome, created_at DESC);

        CREATE TABLE IF NOT EXISTS strategic_context (
            id                INTEGER PRIMARY KEY DEFAULT 1,
            life_phase        TEXT DEFAULT 'young_family_stabilization',
            primary_goal      TEXT DEFAULT 'stable recurring income',
            active_focus      TEXT DEFAULT '[]',
            deprioritized     TEXT DEFAULT '[]',
            stress_tolerance  TEXT DEFAULT 'medium_low',
            financial_pressure TEXT DEFAULT 'high',
            current_constraints TEXT DEFAULT '[]',
            last_date_night   TEXT,
            updated_at        TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS relationship_memory (
            id                 INTEGER PRIMARY KEY AUTOINCREMENT,
            name               TEXT NOT NULL UNIQUE,
            type               TEXT DEFAULT 'client',
            organization       TEXT,
            last_contact       TEXT,
            relationship_score REAL DEFAULT 5.0,
            warmth_score       REAL DEFAULT 5.0,
            notes              TEXT,
            next_touchpoint    TEXT,
            cadence_days       INTEGER DEFAULT 30,
            tags               TEXT DEFAULT '[]',
            risk_of_decay      REAL DEFAULT 0.0,
            opportunity_score  REAL DEFAULT 0.0,
            created_at         TEXT DEFAULT (datetime('now')),
            updated_at         TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS child_profiles (
            id                    INTEGER PRIMARY KEY AUTOINCREMENT,
            child_name            TEXT NOT NULL UNIQUE,
            birth_date            TEXT NOT NULL,
            developmental_stage   TEXT,
            milestones            TEXT DEFAULT '[]',
            current_focus         TEXT,
            recommended_activities TEXT DEFAULT '[]',
            notes                 TEXT,
            updated_at            TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS attention_log (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            date          TEXT DEFAULT (date('now')),
            interruptions INTEGER DEFAULT 0,
            task_switches INTEGER DEFAULT 0,
            deep_work_hrs REAL DEFAULT 0,
            agent_alerts  INTEGER DEFAULT 0,
            overload_flag INTEGER DEFAULT 0,
            notes         TEXT
        );

        CREATE TABLE IF NOT EXISTS trajectory_state (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            domain           TEXT NOT NULL,
            metric_name      TEXT NOT NULL,
            current_value    REAL,
            previous_value   REAL,
            trend_direction  TEXT,
            trajectory_score REAL,
            risk_level       TEXT,
            projected_7d     REAL,
            projected_30d    REAL,
            projected_90d    REAL,
            confidence_score REAL,
            updated_at       TEXT DEFAULT (datetime('now')),
            UNIQUE(domain, metric_name)
        );

        CREATE INDEX IF NOT EXISTS idx_trajectory_domain ON trajectory_state(domain);
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


def create_action(a: dict) -> int:
    """Insert a new action item. Returns the new row id."""
    # Compose suggested_next from notes if provided (actions table has no notes column)
    suggested = a.get("suggested_next") or a.get("notes") or ""
    with _conn() as c:
        cur = c.execute("""
            INSERT INTO actions
              (title, from_name, deadline, priority, status, action_type, suggested_next)
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (a.get("title", ""),
             a.get("contact_name", ""),
             a.get("due_date") or a.get("deadline"),
             (a.get("priority", "MEDIUM") or "MEDIUM").upper(),
             a.get("status", "OPEN"),
             a.get("action_type", "task"),
             suggested))
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


# ── Agent registry ───────────────────────────────────────────────────────────

def register_agent(a: dict) -> int:
    with _conn() as c:
        existing = c.execute("SELECT id FROM agents WHERE name=?", (a["name"],)).fetchone()
        if existing:
            c.execute("""UPDATE agents SET purpose=?,agent_type=?,native_module=?,native_fn=?,
                scope=?,inputs=?,outputs=?,frequency=?,system_prompt=?,rules=?,
                escalation_rules=?,success_metric=?,status=?,updated_at=datetime('now')
                WHERE name=?""",
                (a.get("purpose",""), a.get("agent_type","generated"),
                 a.get("native_module",""), a.get("native_fn",""),
                 a.get("scope",""), json.dumps(a.get("inputs",[])),
                 json.dumps(a.get("outputs",{})), a.get("frequency","weekly"),
                 a.get("system_prompt",""), json.dumps(a.get("rules",{})),
                 json.dumps(a.get("escalation_rules",{})), a.get("success_metric",""),
                 a.get("status","active"), a["name"]))
            return existing[0]
        cur = c.execute("""INSERT INTO agents
            (name,purpose,agent_type,native_module,native_fn,scope,inputs,outputs,
             frequency,system_prompt,rules,escalation_rules,success_metric,status)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (a["name"], a.get("purpose",""), a.get("agent_type","generated"),
             a.get("native_module",""), a.get("native_fn",""),
             a.get("scope",""), json.dumps(a.get("inputs",[])),
             json.dumps(a.get("outputs",{})), a.get("frequency","weekly"),
             a.get("system_prompt",""), json.dumps(a.get("rules",{})),
             json.dumps(a.get("escalation_rules",{})), a.get("success_metric",""),
             a.get("status","active")))
        return cur.lastrowid


def get_agents(status: str = "active") -> list[dict]:
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM agents WHERE status=? ORDER BY frequency ASC, name ASC", (status,)
        ).fetchall()
    return [dict(r) for r in rows]


def get_agent(name: str) -> dict | None:
    with _conn() as c:
        row = c.execute("SELECT * FROM agents WHERE name=?", (name,)).fetchone()
    return dict(row) if row else None


def update_agent_last_run(agent_name: str, output: str = "", exception: bool = False):
    with _conn() as c:
        if exception:
            c.execute("""UPDATE agents SET last_run=datetime('now'), last_output=?,
                run_count=run_count+1, exception_count=exception_count+1,
                updated_at=datetime('now') WHERE name=?""",
                (str(output)[:2000], agent_name))
        else:
            c.execute("""UPDATE agents SET last_run=datetime('now'), last_output=?,
                run_count=run_count+1, updated_at=datetime('now') WHERE name=?""",
                (str(output)[:2000], agent_name))


def kill_agent(agent_name: str, reason: str = ""):
    with _conn() as c:
        c.execute("""UPDATE agents SET status='killed', kill_reason=?,
            updated_at=datetime('now') WHERE name=?""", (reason, agent_name))


def update_agent_frequency(agent_name: str, new_frequency: str) -> bool:
    with _conn() as c:
        cur = c.execute("""UPDATE agents SET frequency=?, updated_at=datetime('now')
            WHERE name=? AND status='active'""", (new_frequency, agent_name))
        return cur.rowcount > 0


def log_agent_output(agent_name: str, output: str = "", exceptions: str = None,
                     has_escalation: bool = False, escalation_reason: str = "") -> int:
    with _conn() as c:
        agent_row = c.execute("SELECT id FROM agents WHERE name=?", (agent_name,)).fetchone()
        agent_id = agent_row[0] if agent_row else None
        cur = c.execute("""INSERT INTO agent_outputs
            (agent_id, agent_name, output, exceptions, has_escalation, escalation_reason)
            VALUES (?,?,?,?,?,?)""",
            (agent_id, agent_name, str(output)[:4000],
             str(exceptions) if exceptions else None,
             1 if has_escalation else 0, escalation_reason))
        return cur.lastrowid


def get_pending_escalations(limit: int = 20) -> list[dict]:
    with _conn() as c:
        rows = c.execute("""SELECT * FROM agent_outputs
            WHERE has_escalation=1 AND status='new'
            ORDER BY ran_at DESC LIMIT ?""", (limit,)).fetchall()
    return [dict(r) for r in rows]


def get_agent_history(agent_name: str, limit: int = 10) -> list[dict]:
    with _conn() as c:
        rows = c.execute("""SELECT * FROM agent_outputs
            WHERE agent_name=? ORDER BY ran_at DESC LIMIT ?""",
            (agent_name, limit)).fetchall()
    return [dict(r) for r in rows]


def mark_escalation_reviewed(output_id: int):
    with _conn() as c:
        c.execute("UPDATE agent_outputs SET status='reviewed' WHERE id=?", (output_id,))


# ── Action Queue ─────────────────────────────────────────────────────────────

def queue_action(a: dict) -> int:
    """Insert a new action into the queue. Returns the new row id."""
    with _conn() as c:
        cur = c.execute("""
            INSERT INTO action_queue
              (action_type, permission_level, payload, source_agent, rationale, status)
            VALUES (?, ?, ?, ?, ?, ?)""",
            (a["action_type"],
             a.get("permission_level", 2),
             json.dumps(a.get("payload", {}), default=str),
             a.get("source_agent", ""),
             a.get("rationale", ""),
             a.get("status", "pending")))
        return cur.lastrowid


def get_pending_actions(limit: int = 50) -> list[dict]:
    with _conn() as c:
        rows = c.execute("""SELECT * FROM action_queue
            WHERE status IN ('pending','approved')
            ORDER BY permission_level ASC, created_at ASC LIMIT ?""", (limit,)).fetchall()
    return [dict(r) for r in rows]


def get_queued_action(action_id: int) -> dict | None:
    with _conn() as c:
        row = c.execute("SELECT * FROM action_queue WHERE id=?", (action_id,)).fetchone()
    return dict(row) if row else None


def approve_action(action_id: int) -> bool:
    with _conn() as c:
        cur = c.execute("""UPDATE action_queue
            SET status='approved', approved_at=datetime('now')
            WHERE id=? AND status='pending'""", (action_id,))
        return cur.rowcount > 0


def reject_action(action_id: int, reason: str = "") -> bool:
    with _conn() as c:
        cur = c.execute("""UPDATE action_queue
            SET status='rejected', rejected_reason=?
            WHERE id=? AND status='pending'""", (reason, action_id))
        return cur.rowcount > 0


def mark_action_executed(action_id: int, result: str = "") -> bool:
    with _conn() as c:
        cur = c.execute("""UPDATE action_queue
            SET status='executed', executed_at=datetime('now'), result=?
            WHERE id=?""", (result[:2000], action_id))
        return cur.rowcount > 0


def mark_action_failed(action_id: int, error: str = "") -> bool:
    with _conn() as c:
        cur = c.execute("""UPDATE action_queue
            SET status='failed', result=?
            WHERE id=?""", (f"ERROR: {error}"[:2000], action_id))
        return cur.rowcount > 0


def get_action_queue_stats() -> dict:
    with _conn() as c:
        rows = c.execute("""SELECT status, COUNT(*) as n
            FROM action_queue GROUP BY status""").fetchall()
    return {r["status"]: r["n"] for r in rows}


# ── Feedback Log ─────────────────────────────────────────────────────────────

def insert_feedback(f: dict) -> int:
    """Insert a feedback_log row. Returns new row id."""
    with _conn() as c:
        cur = c.execute("""
            INSERT INTO feedback_log
              (action_id, action_type, source_agent, outcome,
               rejection_reason, execution_result, permission_level, signal)
            VALUES (?,?,?,?,?,?,?,?)""",
            (f.get("action_id"), f.get("action_type", ""), f.get("source_agent", ""),
             f.get("outcome", ""), f.get("rejection_reason", ""),
             f.get("execution_result", ""), f.get("permission_level", 2),
             f.get("signal", "neutral")))
        return cur.lastrowid


def get_feedback_for_agent(agent_name: str, days: int = 30) -> list[dict]:
    with _conn() as c:
        rows = c.execute("""SELECT * FROM feedback_log
            WHERE source_agent=?
              AND created_at >= datetime('now', ?)
            ORDER BY created_at DESC""",
            (agent_name, f"-{days} days")).fetchall()
    return [dict(r) for r in rows]


def get_all_feedback(days: int = 7) -> list[dict]:
    with _conn() as c:
        rows = c.execute("""SELECT * FROM feedback_log
            WHERE created_at >= datetime('now', ?)
            ORDER BY created_at DESC""",
            (f"-{days} days",)).fetchall()
    return [dict(r) for r in rows]


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


# ── Strategic Context ─────────────────────────────────────────────────────────

_DEFAULT_CTX_VALUES = {
    "life_phase": "young_family_stabilization",
    "primary_goal": "stable recurring income — $15,000+/month",
    "active_focus": '["cashflow", "family stability", "time leverage", "Banoo agency growth"]',
    "deprioritized": '["high-risk speculative projects", "new platforms before current stable"]',
    "stress_tolerance": "medium_low",
    "financial_pressure": "high",
    "current_constraints": '["twin infants (Diyar + Dario)", "RBC low balance", "218 Wilfred legal active"]',
}


def get_strategic_context() -> dict:
    """Return the single strategic context row, seeding defaults if empty."""
    with _conn() as c:
        row = c.execute("SELECT * FROM strategic_context WHERE id=1").fetchone()
        if row:
            return dict(row)
        # Seed defaults
        c.execute("""INSERT OR IGNORE INTO strategic_context
            (id, life_phase, primary_goal, active_focus, deprioritized,
             stress_tolerance, financial_pressure, current_constraints)
            VALUES (1, ?, ?, ?, ?, ?, ?, ?)""",
            (_DEFAULT_CTX_VALUES["life_phase"], _DEFAULT_CTX_VALUES["primary_goal"],
             _DEFAULT_CTX_VALUES["active_focus"], _DEFAULT_CTX_VALUES["deprioritized"],
             _DEFAULT_CTX_VALUES["stress_tolerance"], _DEFAULT_CTX_VALUES["financial_pressure"],
             _DEFAULT_CTX_VALUES["current_constraints"]))
        row = c.execute("SELECT * FROM strategic_context WHERE id=1").fetchone()
        return dict(row) if row else dict(_DEFAULT_CTX_VALUES)


def upsert_strategic_context(updates: dict):
    """Update specific fields of the strategic context (id=1)."""
    with _conn() as c:
        # Ensure row exists
        c.execute("""INSERT OR IGNORE INTO strategic_context (id) VALUES (1)""")
        for field, value in updates.items():
            if field in ("id", "updated_at"):
                continue
            if isinstance(value, (list, dict)):
                value = json.dumps(value)
            c.execute(f"UPDATE strategic_context SET {field}=?, updated_at=datetime('now') WHERE id=1",
                      (value,))


# ── Relationship Memory ───────────────────────────────────────────────────────

def upsert_relationship(r: dict) -> int:
    """Insert or update a relationship record by name."""
    with _conn() as c:
        existing = c.execute("SELECT id FROM relationship_memory WHERE name=?", (r["name"],)).fetchone()
        if isinstance(r.get("tags"), list):
            r = dict(r)
            r["tags"] = json.dumps(r["tags"])
        if existing:
            c.execute("""UPDATE relationship_memory SET
                type=COALESCE(?,type), organization=COALESCE(NULLIF(?,""),organization),
                last_contact=COALESCE(NULLIF(?,""),last_contact),
                relationship_score=COALESCE(?,relationship_score),
                warmth_score=COALESCE(?,warmth_score),
                notes=COALESCE(NULLIF(?,""),notes),
                next_touchpoint=COALESCE(NULLIF(?,""),next_touchpoint),
                cadence_days=COALESCE(?,cadence_days),
                tags=COALESCE(NULLIF(?,""),tags),
                risk_of_decay=COALESCE(?,risk_of_decay),
                opportunity_score=COALESCE(?,opportunity_score),
                updated_at=datetime('now')
                WHERE name=?""",
                (r.get("type"), r.get("organization"), r.get("last_contact"),
                 r.get("relationship_score"), r.get("warmth_score"), r.get("notes"),
                 r.get("next_touchpoint"), r.get("cadence_days"), r.get("tags"),
                 r.get("risk_of_decay"), r.get("opportunity_score"), r["name"]))
            return existing[0]
        cur = c.execute("""INSERT INTO relationship_memory
            (name, type, organization, last_contact, relationship_score, warmth_score,
             notes, next_touchpoint, cadence_days, tags, risk_of_decay, opportunity_score)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (r["name"], r.get("type","client"), r.get("organization",""),
             r.get("last_contact"), r.get("relationship_score", 5.0),
             r.get("warmth_score", 5.0), r.get("notes",""), r.get("next_touchpoint",""),
             r.get("cadence_days", 30), r.get("tags", "[]"),
             r.get("risk_of_decay", 0.0), r.get("opportunity_score", 0.0)))
        return cur.lastrowid


def get_relationships(type: str = None, limit: int = 50) -> list[dict]:
    with _conn() as c:
        if type:
            rows = c.execute(
                "SELECT * FROM relationship_memory WHERE type=? ORDER BY risk_of_decay DESC LIMIT ?",
                (type, limit)).fetchall()
        else:
            rows = c.execute(
                "SELECT * FROM relationship_memory ORDER BY risk_of_decay DESC LIMIT ?",
                (limit,)).fetchall()
    return [dict(r) for r in rows]


def get_decaying_relationships(threshold: float = 0.6) -> list[dict]:
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM relationship_memory WHERE risk_of_decay >= ? ORDER BY risk_of_decay DESC",
            (threshold,)).fetchall()
    return [dict(r) for r in rows]


def update_relationship_decay(name: str, risk_of_decay: float):
    with _conn() as c:
        c.execute("UPDATE relationship_memory SET risk_of_decay=?, updated_at=datetime('now') WHERE name=?",
                  (min(1.0, max(0.0, risk_of_decay)), name))


# ── Child Profiles ────────────────────────────────────────────────────────────

def get_child_profile(name: str) -> dict | None:
    with _conn() as c:
        row = c.execute("SELECT * FROM child_profiles WHERE child_name=?", (name,)).fetchone()
    return dict(row) if row else None


def upsert_child_profile(p: dict):
    with _conn() as c:
        for key in ("milestones", "recommended_activities"):
            if isinstance(p.get(key), list):
                p = dict(p)
                p[key] = json.dumps(p[key])
        existing = c.execute("SELECT id FROM child_profiles WHERE child_name=?", (p["child_name"],)).fetchone()
        if existing:
            c.execute("""UPDATE child_profiles SET
                birth_date=COALESCE(?,birth_date),
                developmental_stage=COALESCE(NULLIF(?,""),developmental_stage),
                milestones=COALESCE(NULLIF(?,""),milestones),
                current_focus=COALESCE(NULLIF(?,""),current_focus),
                recommended_activities=COALESCE(NULLIF(?,""),recommended_activities),
                notes=COALESCE(NULLIF(?,""),notes),
                updated_at=datetime('now')
                WHERE child_name=?""",
                (p.get("birth_date"), p.get("developmental_stage",""),
                 p.get("milestones"), p.get("current_focus",""),
                 p.get("recommended_activities"), p.get("notes",""), p["child_name"]))
        else:
            c.execute("""INSERT INTO child_profiles
                (child_name, birth_date, developmental_stage, milestones, current_focus,
                 recommended_activities, notes)
                VALUES (?,?,?,?,?,?,?)""",
                (p["child_name"], p.get("birth_date",""), p.get("developmental_stage",""),
                 p.get("milestones", "[]"), p.get("current_focus",""),
                 p.get("recommended_activities","[]"), p.get("notes","")))


def get_all_child_profiles() -> list[dict]:
    with _conn() as c:
        rows = c.execute("SELECT * FROM child_profiles ORDER BY child_name").fetchall()
    return [dict(r) for r in rows]


# ── Attention Log ─────────────────────────────────────────────────────────────

def log_attention(entry: dict):
    with _conn() as c:
        c.execute("""INSERT OR REPLACE INTO attention_log
            (date, interruptions, task_switches, deep_work_hrs, agent_alerts, overload_flag, notes)
            VALUES (COALESCE(?,date('now')),?,?,?,?,?,?)""",
            (entry.get("date"), entry.get("interruptions", 0), entry.get("task_switches", 0),
             entry.get("deep_work_hrs", 0), entry.get("agent_alerts", 0),
             1 if entry.get("overload_flag") else 0, entry.get("notes","")))


def get_attention_log(days: int = 7) -> list[dict]:
    with _conn() as c:
        rows = c.execute("""SELECT * FROM attention_log
            WHERE date >= date('now', ?) ORDER BY date DESC""",
            (f"-{days} days",)).fetchall()
    return [dict(r) for r in rows]


# ── Trajectory State ──────────────────────────────────────────────────────────

def upsert_trajectory_state(row: dict) -> int:
    with _conn() as c:
        cur = c.execute("""
            INSERT INTO trajectory_state
              (domain, metric_name, current_value, previous_value, trend_direction,
               trajectory_score, risk_level, projected_7d, projected_30d, projected_90d,
               confidence_score, updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,datetime('now'))
            ON CONFLICT(domain, metric_name) DO UPDATE SET
              previous_value   = current_value,
              current_value    = excluded.current_value,
              trend_direction  = excluded.trend_direction,
              trajectory_score = excluded.trajectory_score,
              risk_level       = excluded.risk_level,
              projected_7d     = excluded.projected_7d,
              projected_30d    = excluded.projected_30d,
              projected_90d    = excluded.projected_90d,
              confidence_score = excluded.confidence_score,
              updated_at       = datetime('now')
        """, (
            row["domain"], row.get("metric_name", row["domain"]),
            row.get("current_value"), row.get("previous_value"),
            row.get("trend_direction", "unknown"),
            row.get("trajectory_score", 0.0), row.get("risk_level", "low"),
            row.get("projected_7d"), row.get("projected_30d"), row.get("projected_90d"),
            row.get("confidence_score", 0.0),
        ))
        return cur.lastrowid


def get_trajectory_state(domain: str) -> dict | None:
    with _conn() as c:
        row = c.execute(
            "SELECT * FROM trajectory_state WHERE domain=? ORDER BY updated_at DESC LIMIT 1",
            (domain,)).fetchone()
    return dict(row) if row else None


def get_all_trajectory_states() -> list[dict]:
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM trajectory_state ORDER BY domain ASC"
        ).fetchall()
    return [dict(r) for r in rows]
