"""
memory_sync.py — Sync SQLite data → JSON memory files for agent consumption.
Agents read JSON. SQLite is the durable source of truth.
Run before each orchestration pass to ensure agents see fresh state.
"""
import json
import sys
from datetime import date, timedelta
from pathlib import Path

_HERE = Path(__file__).parent
_CHIEF = _HERE.parent / "chief"
sys.path.insert(0, str(_CHIEF))

import db

MEM = _HERE / "memory"
TASKS = _HERE / "tasks"
DASH = _HERE / "dashboard"
INCOME_TARGET = 15000.0


def _write(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, default=str))


def _week_start() -> str:
    today = date.today()
    return (today - timedelta(days=today.weekday())).isoformat()


def sync_all() -> dict:
    """Sync all SQLite data → JSON. Returns the state dict."""
    db.init()

    streams = db.get_revenue_streams("active")
    initiatives_active = db.get_initiatives("active")
    initiatives_killed = db.get_initiatives("killed")
    decisions = db.get_decisions(20)
    weekly = db.get_weekly_metrics(4)
    pipeline = db.get_pipeline_metrics(4)
    queue = db.get_daily_queue()
    actions = db.get_actions(status="OPEN", priority="HIGH", limit=10)
    systems = db.get_systems("active")
    options = db.get_strategic_options()
    stats = db.stats()

    mrr = sum(s.get("monthly_revenue", 0) for s in streams)
    gap = INCOME_TARGET - mrr
    init_count = len(initiatives_active)
    focus_status = "GREEN" if init_count <= 2 else "YELLOW" if init_count == 3 else "RED"
    latest_week = weekly[0] if weekly else {}
    latest_pipeline = pipeline[0] if pipeline else {}

    state = {
        "today": date.today().isoformat(),
        "week_start": _week_start(),
        "north_star_90d": f"Reach ${INCOME_TARGET:,.0f}/month stable recurring income from AI + marketing systems",
        "current_revenue": mrr,
        "target_revenue": INCOME_TARGET,
        "gap": gap,
        "gap_pct": round((gap / INCOME_TARGET) * 100, 1) if INCOME_TARGET else 0,
        "focus_load": {
            "active_initiatives": init_count,
            "status": focus_status,
        },
        "energy_level": latest_week.get("energy_score", 0),
        "weekly_focus_score": latest_week.get("focus_score", 0),
        "deep_work_hours": latest_week.get("deep_work_hours", 0),
        "context_switches": latest_week.get("context_switches", 0),
        "contacts_total": stats.get("contacts", 0),
        "open_actions": stats.get("actions_open", 0),
    }

    kill_list = [
        {
            "initiative": i["name"],
            "reason_killed": i.get("kill_reason", ""),
            "date": i.get("updated_at", "")[:10] if i.get("updated_at") else "",
        }
        for i in initiatives_killed
    ]

    pipeline_data = {
        "week_start": latest_pipeline.get("week_start", _week_start()),
        "leads_generated": latest_pipeline.get("leads_generated", 0),
        "calls_booked": latest_pipeline.get("calls_booked", 0),
        "calls_completed": latest_pipeline.get("calls_completed", 0),
        "proposals_sent": latest_pipeline.get("proposals_sent", 0),
        "deals_closed": latest_pipeline.get("deals_closed", 0),
        "revenue_closed": latest_pipeline.get("revenue_closed", 0),
        "conversion_rate": round(
            (latest_pipeline.get("deals_closed", 0) / max(latest_pipeline.get("leads_generated", 1), 1)) * 100, 1
        ) if latest_pipeline else 0,
        "history": pipeline[:4],
    }

    tasks_today = {
        "date": date.today().isoformat(),
        "tasks": [
            {
                "task": t["title"],
                "priority": i + 1,
                "revenue_impact": t.get("rev_impact", "indirect"),
                "outcome": t.get("outcome", ""),
                "status": t.get("status", "pending"),
            }
            for i, t in enumerate(queue)
        ],
    }

    snapshot = {
        "revenue": mrr,
        "target": INCOME_TARGET,
        "gap": gap,
        "pipeline_health": "RED" if not latest_pipeline or latest_pipeline.get("leads_generated", 0) == 0 else "GREEN",
        "active_initiatives": init_count,
        "focus_status": focus_status,
        "burnout_risk": "HIGH" if (latest_week.get("energy_score") or 5) < 4 else "MEDIUM" if (latest_week.get("energy_score") or 5) < 7 else "LOW",
        "automation_ratio": round(
            sum(1 for s in systems if s.get("auto_status") == "automated") / max(len(systems), 1) * 100
        ) if systems else 0,
    }

    metrics = {
        "week_start": _week_start(),
        "weekly_history": weekly[:4],
        "pipeline_history": pipeline[:4],
        "systems_count": len(systems),
        "automated_systems": sum(1 for s in systems if s.get("auto_status") == "automated"),
        "strategic_options_active": sum(1 for o in options if o.get("status") != "killed"),
    }

    # Write all memory files
    _write(MEM / "state.json", state)
    _write(MEM / "revenue.json", streams)
    _write(MEM / "pipeline.json", pipeline_data)
    _write(MEM / "initiatives.json", initiatives_active)
    _write(MEM / "decisions_log.json", decisions[:10])
    _write(MEM / "kill_list.json", kill_list)
    _write(TASKS / "today.json", tasks_today)
    _write(DASH / "snapshot.json", snapshot)
    _write(DASH / "metrics.json", metrics)

    # Ensure backlog and completed exist
    backlog_path = TASKS / "backlog.json"
    if not backlog_path.exists():
        _write(backlog_path, {"items": [], "pruned_at": None})
    completed_path = TASKS / "completed.json"
    if not completed_path.exists():
        _write(completed_path, {"history": []})

    return state


def read_memory() -> dict:
    """Read all memory files into a single context dict for agents."""
    state_path = MEM / "state.json"
    if not state_path.exists():
        return sync_all()

    def _read(path: Path):
        try:
            return json.loads(path.read_text())
        except Exception:
            return {}

    return {
        "state": _read(MEM / "state.json"),
        "revenue": _read(MEM / "revenue.json"),
        "pipeline": _read(MEM / "pipeline.json"),
        "initiatives": _read(MEM / "initiatives.json"),
        "decisions": _read(MEM / "decisions_log.json"),
        "kill_list": _read(MEM / "kill_list.json"),
        "tasks_today": _read(TASKS / "today.json"),
        "snapshot": _read(DASH / "snapshot.json"),
    }


def update_state(patch: dict):
    """Patch memory/state.json with new values."""
    state_path = MEM / "state.json"
    state = json.loads(state_path.read_text()) if state_path.exists() else {}
    state.update(patch)
    _write(state_path, state)


def log_completed_task(task: dict):
    """Append a completed task to tasks/completed.json."""
    path = TASKS / "completed.json"
    data = json.loads(path.read_text()) if path.exists() else {"history": []}
    data["history"].insert(0, {**task, "completed_at": date.today().isoformat()})
    data["history"] = data["history"][:200]
    _write(path, data)


if __name__ == "__main__":
    state = sync_all()
    print(f"Memory synced. MRR: ${state['current_revenue']:,.0f} | Gap: ${state['gap']:,.0f} | Focus: {state['focus_load']['status']}")
