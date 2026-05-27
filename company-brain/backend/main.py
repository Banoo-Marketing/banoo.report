"""
Company Brain – FastAPI Application
─────────────────────────────────────
Endpoints:
  GET  /health
  GET  /alerts               → pending action_queue items
  POST /alerts/{id}/approve  → approve + trigger execution
  POST /alerts/{id}/reject   → reject with reason
  GET  /deals                → all deals with contact info
  GET  /deals/{id}           → single deal + coaching tip
  GET  /contacts/top         → top 20% by CLV
  POST /scan/renewals        → manually trigger renewal scan
  POST /scan/agent           → manually trigger agent decision loop
  WS   /ws/alerts            → real-time WebSocket push to dashboard
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Any
import json
import asyncio

import database as db
from config import settings
import renewal_engine
import clv_engine
import agent_loop
from tasks import execute_approved_action

app = FastAPI(
    title="Company Brain API",
    version="1.0.0",
    description="AI-powered B2B sales co-pilot",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── WebSocket connection registry ────────────────────────────────────────────

_ws_clients: list[WebSocket] = []


@app.websocket("/ws/alerts")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    _ws_clients.append(websocket)
    try:
        while True:
            await asyncio.sleep(30)
            await websocket.send_text(json.dumps({"type": "ping"}))
    except WebSocketDisconnect:
        _ws_clients.remove(websocket)


async def broadcast(payload: dict[str, Any]) -> None:
    dead = []
    for ws in _ws_clients:
        try:
            await ws.send_text(json.dumps(payload))
        except Exception:
            dead.append(ws)
    for ws in dead:
        _ws_clients.remove(ws)


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "version": "1.0.0"}


# ── Alerts (Action Queue) ────────────────────────────────────────────────────

@app.get("/alerts")
def get_alerts(status: str = Query("PENDING_APPROVAL")):
    """Return action_queue items filtered by status."""
    rows = db.fetchall(
        """
        SELECT aq.*, d.name AS deal_name, d.amount, d.company,
               c.name AS contact_name, c.email AS contact_email, c.clv_tier
        FROM action_queue aq
        LEFT JOIN deals d ON d.id = aq.deal_id
        LEFT JOIN contacts c ON c.id = aq.contact_id
        WHERE aq.status = %s
        ORDER BY
          CASE aq.urgency WHEN 'HIGH' THEN 1 WHEN 'MEDIUM' THEN 2 ELSE 3 END,
          aq.created_at DESC
        """,
        (status,),
    )
    return {"alerts": rows, "count": len(rows)}


@app.get("/alerts/stats")
def alert_stats():
    """Dashboard summary counts."""
    rows = db.fetchall(
        "SELECT status, COUNT(*) AS cnt FROM action_queue GROUP BY status"
    )
    return {r["status"]: r["cnt"] for r in rows}


class ApproveRequest(BaseModel):
    user_id: str = "dashboard_user"


class RejectRequest(BaseModel):
    user_id: str = "dashboard_user"
    reason: str = ""


@app.post("/alerts/{alert_id}/approve")
async def approve_alert(alert_id: int, body: ApproveRequest):
    existing = db.fetchone("SELECT * FROM action_queue WHERE id=%s", (alert_id,))
    if not existing:
        raise HTTPException(404, "Alert not found")
    if existing["status"] != "PENDING_APPROVAL":
        raise HTTPException(400, f"Alert is already {existing['status']}")

    db.execute(
        "UPDATE action_queue SET status='APPROVED', approved_by=%s, approved_at=NOW() WHERE id=%s",
        (body.user_id, alert_id),
    )

    # Fire async execution task
    execute_approved_action.delay(alert_id)

    # Notify connected dashboards
    await broadcast({"type": "alert_approved", "alert_id": alert_id})

    return {"status": "approved", "alert_id": alert_id}


@app.post("/alerts/{alert_id}/reject")
async def reject_alert(alert_id: int, body: RejectRequest):
    existing = db.fetchone("SELECT * FROM action_queue WHERE id=%s", (alert_id,))
    if not existing:
        raise HTTPException(404, "Alert not found")

    db.execute(
        """UPDATE action_queue
           SET status='REJECTED', rejected_by=%s, reject_reason=%s
           WHERE id=%s""",
        (body.user_id, body.reason, alert_id),
    )
    await broadcast({"type": "alert_rejected", "alert_id": alert_id})
    return {"status": "rejected", "alert_id": alert_id}


# ── Deals ─────────────────────────────────────────────────────────────────────

@app.get("/deals")
def get_deals(stage: str | None = None, limit: int = 50):
    query = """
        SELECT d.*, c.name AS contact_name, c.email AS contact_email,
               c.clv_tier, c.industry
        FROM deals d
        LEFT JOIN contacts c ON c.id = d.contact_id
        {where}
        ORDER BY d.renewal_date ASC NULLS LAST, d.amount DESC
        LIMIT %s
    """
    if stage:
        rows = db.fetchall(query.format(where="WHERE d.stage=%s"), (stage, limit))
    else:
        rows = db.fetchall(query.format(where=""), (limit,))
    return {"deals": rows, "count": len(rows)}


@app.get("/deals/{deal_id}")
def get_deal(deal_id: str):
    deal = db.fetchone(
        """
        SELECT d.*, c.name AS contact_name, c.email AS contact_email,
               c.clv_tier, c.industry, c.clv_score
        FROM deals d
        LEFT JOIN contacts c ON c.id = d.contact_id
        WHERE d.id = %s
        """,
        (deal_id,),
    )
    if not deal:
        raise HTTPException(404, "Deal not found")

    # Pull pending actions for this deal
    actions = db.fetchall(
        "SELECT * FROM action_queue WHERE deal_id=%s ORDER BY created_at DESC LIMIT 5",
        (deal_id,),
    )
    deal["pending_actions"] = actions
    return deal


# ── Contacts ──────────────────────────────────────────────────────────────────

@app.get("/contacts/top")
def top_contacts():
    top = clv_engine.get_top_clients(pct=0.20)
    return {"contacts": top, "count": len(top)}


@app.get("/contacts/{contact_id}/nurture")
def get_nurture_suggestion(contact_id: str):
    contact = db.fetchone("SELECT * FROM contacts WHERE id=%s", (contact_id,))
    if not contact:
        raise HTTPException(404, "Contact not found")
    suggestion = clv_engine.suggest_nurture_action(contact)
    return {"contact_id": contact_id, "suggestion": suggestion}


# ── Manual Scan Triggers ──────────────────────────────────────────────────────

@app.post("/scan/renewals")
async def trigger_renewal_scan():
    """Manually kick off a renewal scan (also runs automatically every 15min)."""
    results = renewal_engine.run_renewal_scan()
    if results:
        await broadcast({"type": "new_alerts", "count": len(results)})
    return {"queued": len(results), "items": results}


@app.post("/scan/agent")
async def trigger_agent_scan():
    """Manually kick off the AI decision loop across all active deals."""
    actions = agent_loop.run_full_scan()
    if actions:
        await broadcast({"type": "new_alerts", "count": len(actions)})
    return {"actions_queued": len(actions), "actions": actions}


@app.post("/deals/{deal_id}/analyse")
async def analyse_deal(deal_id: str):
    """Run agent decision loop for a single deal on demand."""
    try:
        decision = agent_loop.decide_action(deal_id)
        if decision.get("action") not in ("NO_ACTION", "no_action"):
            await broadcast({"type": "new_alerts", "count": 1})
        return decision
    except ValueError as e:
        raise HTTPException(404, str(e))


# ── Audit Log ─────────────────────────────────────────────────────────────────

@app.get("/audit")
def get_audit_log(deal_id: str | None = None, limit: int = 100):
    if deal_id:
        rows = db.fetchall(
            "SELECT * FROM audit_log WHERE deal_id=%s ORDER BY created_at DESC LIMIT %s",
            (deal_id, limit),
        )
    else:
        rows = db.fetchall(
            "SELECT * FROM audit_log ORDER BY created_at DESC LIMIT %s",
            (limit,),
        )
    return {"logs": rows, "count": len(rows)}
