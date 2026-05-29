"""
dashboard.py — Atlas Operating Dashboard (FastAPI)
Run: python dashboard.py   → http://localhost:8001
"""
import json
import sqlite3
from datetime import date, timedelta
from pathlib import Path
from fastapi import FastAPI, Body, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import db

app = FastAPI(title="Atlas", version="2.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

_HERE = Path(__file__).parent
INCOME_TARGET = 15000.0


def _week_start() -> str:
    today = date.today()
    return (today - timedelta(days=today.weekday())).isoformat()


# ── Health ───────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok"}


# ── Snapshot (North Star + Risk computed) ────────────────────────────────────

@app.get("/api/snapshot")
def api_snapshot():
    db.init()
    streams = db.get_revenue_streams("active")
    initiatives = db.get_initiatives("active")
    current_mrr = sum(s.get("monthly_revenue", 0) for s in streams)
    gap = INCOME_TARGET - current_mrr

    # Focus load: 0-2 = green, 3 = yellow, >3 = red
    init_count = len(initiatives)
    if init_count <= 2:
        focus_status = "GREEN"
    elif init_count == 3:
        focus_status = "YELLOW"
    else:
        focus_status = "RED"

    # Income dependency risk
    if streams and current_mrr > 0:
        top_share = max(s.get("monthly_revenue", 0) for s in streams) / current_mrr
        dep_risk = "RED" if top_share > 0.8 else "YELLOW" if top_share > 0.5 else "GREEN"
    else:
        dep_risk = "RED" if not streams else "YELLOW"

    # Cash runway (months current can cover obligations — simplified)
    obligations = 1428.36  # mortgage
    runway_months = round(current_mrr / obligations, 1) if obligations > 0 else 0
    runway_status = "RED" if runway_months < 1.5 else "YELLOW" if runway_months < 3 else "GREEN"

    # Weekly metrics for energy/focus scores
    weekly = db.get_weekly_metrics(1)
    latest_week = weekly[0] if weekly else {}

    # Pipeline health
    pipeline = db.get_pipeline_metrics(1)
    latest_pipeline = pipeline[0] if pipeline else {}
    if not latest_pipeline:
        pipeline_status = "YELLOW"
    else:
        if latest_pipeline.get("leads_generated", 0) == 0:
            pipeline_status = "RED"
        elif latest_pipeline.get("proposals_sent", 0) == 0:
            pipeline_status = "YELLOW"
        else:
            pipeline_status = "GREEN"

    return {
        "target": INCOME_TARGET,
        "current_mrr": current_mrr,
        "gap": gap,
        "gap_pct": round((gap / INCOME_TARGET) * 100, 1) if INCOME_TARGET > 0 else 0,
        "stream_count": len(streams),
        "initiative_count": init_count,
        "focus_status": focus_status,
        "income_dep_risk": dep_risk,
        "runway_months": runway_months,
        "runway_status": runway_status,
        "pipeline_status": pipeline_status,
        "energy_score": latest_week.get("energy_score", 0),
        "focus_score": latest_week.get("focus_score", 0),
        "week_start": _week_start(),
    }


# ── Revenue ──────────────────────────────────────────────────────────────────

@app.get("/api/revenue")
def api_get_revenue():
    db.init()
    active = db.get_revenue_streams("active")
    killed = db.get_revenue_streams("killed")
    return {"active": active, "killed": killed}


@app.post("/api/revenue")
def api_create_revenue(data: dict = Body(...)):
    db.init()
    item_id = db.upsert_revenue_stream(data)
    return {"id": item_id, "ok": True}


@app.put("/api/revenue/{item_id}")
def api_update_revenue(item_id: int, data: dict = Body(...)):
    db.init()
    data["id"] = item_id
    db.upsert_revenue_stream(data)
    return {"ok": True}


@app.delete("/api/revenue/{item_id}")
def api_kill_revenue(item_id: int):
    db.init()
    db.delete_revenue_stream(item_id)
    return {"ok": True}


# ── Initiatives ───────────────────────────────────────────────────────────────

@app.get("/api/initiatives")
def api_get_initiatives():
    db.init()
    return {
        "active": db.get_initiatives("active"),
        "killed": db.get_initiatives("killed"),
        "paused": db.get_initiatives("paused"),
    }


@app.post("/api/initiatives")
def api_create_initiative(data: dict = Body(...)):
    db.init()
    active = db.get_initiatives("active")
    if len(active) >= 3 and not data.get("force"):
        raise HTTPException(400, "Focus overload: 3 active initiatives already. Kill one first or pass force=true.")
    item_id = db.upsert_initiative(data)
    return {"id": item_id, "ok": True}


@app.put("/api/initiatives/{item_id}")
def api_update_initiative(item_id: int, data: dict = Body(...)):
    db.init()
    data["id"] = item_id
    db.upsert_initiative(data)
    return {"ok": True}


@app.post("/api/initiatives/{item_id}/kill")
def api_kill_initiative(item_id: int, data: dict = Body(...)):
    db.init()
    db.kill_initiative(item_id, data.get("reason", ""))
    return {"ok": True}


# ── Decisions ─────────────────────────────────────────────────────────────────

@app.get("/api/decisions")
def api_get_decisions():
    db.init()
    return {"decisions": db.get_decisions(30)}


@app.post("/api/decisions")
def api_add_decision(data: dict = Body(...)):
    db.init()
    item_id = db.add_decision(data)
    return {"id": item_id, "ok": True}


@app.put("/api/decisions/{item_id}/outcome")
def api_decision_outcome(item_id: int, data: dict = Body(...)):
    db.init()
    db.update_decision_outcome(item_id, data.get("outcome", ""))
    return {"ok": True}


# ── Weekly metrics ────────────────────────────────────────────────────────────

@app.get("/api/metrics/weekly")
def api_get_weekly():
    db.init()
    return {"weeks": db.get_weekly_metrics(8)}


@app.post("/api/metrics/weekly")
def api_upsert_weekly(data: dict = Body(...)):
    db.init()
    if "week_start" not in data:
        data["week_start"] = _week_start()
    db.upsert_weekly_metrics(data)
    return {"ok": True}


# ── Pipeline ──────────────────────────────────────────────────────────────────

@app.get("/api/pipeline")
def api_get_pipeline():
    db.init()
    return {"weeks": db.get_pipeline_metrics(8)}


@app.post("/api/pipeline")
def api_upsert_pipeline(data: dict = Body(...)):
    db.init()
    if "week_start" not in data:
        data["week_start"] = _week_start()
    db.upsert_pipeline_metrics(data)
    return {"ok": True}


# ── Strategic options ─────────────────────────────────────────────────────────

@app.get("/api/strategic-options")
def api_get_options():
    db.init()
    return {"options": db.get_strategic_options()}


@app.post("/api/strategic-options")
def api_create_option(data: dict = Body(...)):
    db.init()
    item_id = db.upsert_strategic_option(data)
    return {"id": item_id, "ok": True}


@app.put("/api/strategic-options/{item_id}")
def api_update_option(item_id: int, data: dict = Body(...)):
    db.init()
    data["id"] = item_id
    db.upsert_strategic_option(data)
    return {"ok": True}


# ── Systems ───────────────────────────────────────────────────────────────────

@app.get("/api/systems")
def api_get_systems():
    db.init()
    return {"systems": db.get_systems("active")}


@app.post("/api/systems")
def api_create_system(data: dict = Body(...)):
    db.init()
    item_id = db.upsert_system(data)
    return {"id": item_id, "ok": True}


@app.put("/api/systems/{item_id}")
def api_update_system(item_id: int, data: dict = Body(...)):
    db.init()
    data["id"] = item_id
    db.upsert_system(data)
    return {"ok": True}


# ── Daily queue ───────────────────────────────────────────────────────────────

@app.get("/api/queue")
def api_get_queue():
    db.init()
    items = db.get_daily_queue()
    count = len([i for i in items if i["status"] == "pending"])
    return {"items": items, "pending_count": count, "overloaded": count > 3}


@app.post("/api/queue")
def api_add_queue(data: dict = Body(...)):
    db.init()
    today_items = db.get_daily_queue()
    pending = [i for i in today_items if i["status"] == "pending"]
    if len(pending) >= 3 and not data.get("force"):
        raise HTTPException(400, "Task overload: 3 tasks already queued for today. Complete one first or pass force=true.")
    item_id = db.add_queue_item(data)
    return {"id": item_id, "ok": True}


@app.put("/api/queue/{item_id}/done")
def api_queue_done(item_id: int):
    db.init()
    db.update_queue_status(item_id, "done")
    return {"ok": True}


@app.delete("/api/queue/{item_id}")
def api_delete_queue(item_id: int):
    db.init()
    db.delete_queue_item(item_id)
    return {"ok": True}


# ── Existing endpoints ────────────────────────────────────────────────────────

@app.get("/api/stats")
def api_stats():
    db.init()
    st = db.stats()
    email_db = _HERE.parent / "email-analyzer" / "email_cache.db"
    if email_db.exists():
        with sqlite3.connect(email_db) as c:
            try:
                st["emails_total"] = c.execute("SELECT COUNT(*) FROM emails").fetchone()[0]
                st["emails_processed"] = c.execute("SELECT COUNT(*) FROM processing").fetchone()[0]
            except Exception:
                pass
    return st


@app.get("/api/contacts")
def api_contacts(limit: int = 50, relationship: str = None):
    db.init()
    contacts = db.get_contacts(relationship=relationship, limit=limit)
    for c in contacts:
        try:
            c["obligations"] = json.loads(c.get("obligations") or "[]")
        except Exception:
            c["obligations"] = []
    return {"contacts": contacts, "count": len(contacts)}


@app.get("/api/contacts/top")
def api_top_contacts(n: int = 20):
    db.init()
    return {"contacts": db.get_top_contacts(n=n)}


@app.get("/api/contacts/reconnect")
def api_reconnect(days: int = 180):
    db.init()
    return {"contacts": db.get_dormant_contacts(days=days)}


@app.get("/api/contacts/nurture")
def api_nurture():
    db.init()
    with sqlite3.connect(db.DB_PATH) as c:
        c.row_factory = sqlite3.Row
        rows = c.execute("""
        SELECT * FROM contacts
        WHERE (relationship='Lead (business owner)' OR is_business_owner=1)
          AND nurture_score > 0
        ORDER BY nurture_score DESC LIMIT 20
        """).fetchall()
    return {"leads": [dict(r) for r in rows]}


@app.get("/api/actions")
def api_actions(status: str = "OPEN", priority: str = None, limit: int = 50):
    db.init()
    return {"actions": db.get_actions(status=status, priority=priority, limit=limit)}


@app.get("/api/calendar")
def api_calendar(days: int = 7):
    db.init()
    return {"events": db.get_upcoming_events(days=days)}


@app.get("/api/brief")
def api_brief():
    db.init()
    import daily_brief
    brief = daily_brief.generate_brief(verbose=False)
    return brief


@app.get("/", response_class=HTMLResponse)
def dashboard():
    tmpl = _HERE / "templates" / "dashboard.html"
    if tmpl.exists():
        return tmpl.read_text()
    return "<h1>Atlas</h1><p>Template not found.</p>"


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8001, reload=False)
