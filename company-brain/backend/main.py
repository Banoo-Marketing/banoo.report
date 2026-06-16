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

  Gmail OAuth:
  GET  /auth/google           → redirect to Google consent screen
  GET  /auth/google/callback  → handle OAuth callback, store token
  GET  /auth/google/status    → check if Gmail is connected
  POST /auth/google/test      → send test email
  DELETE /auth/google         → disconnect / revoke token

  Gmail actions:
  GET  /gmail/unread          → fetch + analyse unread emails for renewal signals
  POST /gmail/send/{alert_id} → send approved email (requires APPROVED status)
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Any
import json
import asyncio

from fastapi.responses import RedirectResponse
import database as db
from config import settings
import renewal_engine
import clv_engine
import agent_loop
from tasks import execute_approved_action

# Gmail modules imported lazily inside routes to avoid cryptography conflicts
def _gmail_auth():
    import gmail_auth
    return gmail_auth

def _gmail_reader():
    import gmail_reader
    return gmail_reader

def _gmail_sender():
    import gmail_sender
    return gmail_sender

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


# ── Gmail OAuth ────────────────────────────────────────────────────────────────

@app.get("/auth/google")
def google_auth_start():
    """Redirect user to Google's OAuth consent screen."""
    if not settings.google_client_id:
        raise HTTPException(
            400,
            "GOOGLE_CLIENT_ID not set. Add it to .env (get from console.cloud.google.com).",
        )
    auth_url = _gmail_auth().get_auth_url()
    return RedirectResponse(auth_url)


@app.get("/auth/google/callback")
def google_auth_callback(code: str, error: str | None = None):
    """Handle OAuth callback from Google. Stores tokens and redirects to dashboard."""
    if error:
        raise HTTPException(400, f"Google OAuth error: {error}")
    try:
        token_data = _gmail_auth().exchange_code(code)
        db.execute(
            "INSERT INTO audit_log (action_type, actor, details) VALUES ('gmail_connected', 'user', %s)",
            (json.dumps({"scopes": token_data.get("scopes", [])}),),
        )
        return RedirectResponse("http://localhost:3000?gmail=connected")
    except Exception as e:
        raise HTTPException(500, f"Token exchange failed: {e}")


@app.get("/auth/google/status")
def google_auth_status():
    """Check if Gmail is connected and working."""
    connected = _gmail_auth().is_connected()
    return {
        "connected": connected,
        "message": "Gmail connected ✅" if connected else (
            "Not connected. Visit /auth/google to connect your Gmail account."
            if settings.google_client_id
            else "Set GOOGLE_CLIENT_ID + GOOGLE_CLIENT_SECRET in .env first."
        ),
    }


@app.delete("/auth/google")
def google_auth_disconnect():
    """Revoke and delete stored Gmail token."""
    ga = _gmail_auth()
    if ga._TOKEN_FILE.exists():
        ga._TOKEN_FILE.unlink()
        db.execute(
            "INSERT INTO audit_log (action_type, actor, details) VALUES ('gmail_disconnected', 'user', '{}')",
        )
    return {"disconnected": True}


class TestEmailRequest(BaseModel):
    to: str


@app.post("/auth/google/test")
def gmail_test(body: TestEmailRequest):
    """Send a test email to verify the Gmail connection works."""
    try:
        result = _gmail_sender().send_test_email(body.to)
        return result
    except RuntimeError as e:
        raise HTTPException(400, str(e))


# ── Gmail Actions ──────────────────────────────────────────────────────────────

@app.post("/gmail/scan")
async def trigger_gmail_scan():
    """Manually trigger the Gmail inbox scan (also runs automatically every hour)."""
    import gmail_inbox_scanner
    result = gmail_inbox_scanner.run_inbox_scan()
    total_queued = result.get("renewal_signals_queued", 0) + result.get("touchbase_emails_queued", 0)
    if total_queued > 0:
        await broadcast({"type": "new_alerts", "count": total_queued})
    return result


@app.get("/gmail/unread")
def read_unread_emails(max_results: int = 50):
    """Fetch unread emails and extract renewal signals via Claude."""
    try:
        gr = _gmail_reader()
        emails = gr.get_unread_emails(max_results)
        signals = gr.extract_renewal_signals(emails)
        return {
            "emails_scanned": len(emails),
            "renewal_signals": len(signals),
            "signals": signals,
        }
    except RuntimeError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, str(e))


class SendEmailRequest(BaseModel):
    to: str
    subject: str
    body: str
    deal_id: str


@app.post("/gmail/send/{action_id}")
async def send_approved_email(action_id: int, body: SendEmailRequest):
    """Send an approved email (requires APPROVED status in action_queue)."""
    try:
        result = _gmail_sender().send_approved_email(
            action_id=action_id,
            to=body.to,
            subject=body.subject,
            body_html=body.body,
            deal_id=body.deal_id,
        )
        await broadcast({"type": "email_sent", "action_id": action_id, "to": body.to})
        return result
    except PermissionError as e:
        raise HTTPException(403, str(e))
    except RuntimeError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, str(e))


# ── SEMrush ───────────────────────────────────────────────────────────────────

@app.get("/semrush/domain/{domain}")
def semrush_domain(domain: str):
    from semrush_connector import get_domain_overview, get_top_keywords
    try:
        overview = get_domain_overview(domain)
        keywords = get_top_keywords(domain, limit=10)
        return {"overview": overview, "top_keywords": keywords}
    except Exception as e:
        raise HTTPException(400, str(e))

@app.post("/semrush/enrich/{contact_id}")
def semrush_enrich_contact(contact_id: str):
    from semrush_connector import get_client_seo_health
    try:
        return get_client_seo_health(contact_id)
    except Exception as e:
        raise HTTPException(400, str(e))

@app.post("/semrush/enrich-all")
def semrush_enrich_all():
    from semrush_connector import enrich_all_contacts
    try:
        results = enrich_all_contacts()
        return {"enriched": len(results), "results": results}
    except Exception as e:
        raise HTTPException(400, str(e))


# ── Stripe ────────────────────────────────────────────────────────────────────

@app.get("/stripe/health")
def stripe_health():
    from stripe_connector import get_mrr
    try:
        return get_mrr()
    except Exception as e:
        raise HTTPException(400, str(e))

@app.post("/stripe/sync")
async def stripe_sync():
    from stripe_connector import sync_all
    try:
        result = sync_all()
        if result.get("failed_payments"):
            await broadcast({"type": "new_alerts", "count": result["failed_payments"]})
        return result
    except Exception as e:
        raise HTTPException(400, str(e))

@app.get("/stripe/subscriptions")
def stripe_subscriptions():
    from stripe_connector import get_subscription_health
    try:
        return {"subscriptions": get_subscription_health()}
    except Exception as e:
        raise HTTPException(400, str(e))


# ── X / Twitter ───────────────────────────────────────────────────────────────

@app.post("/x/draft-win-tweet/{deal_id}")
async def draft_win_tweet(deal_id: str):
    from x_connector import draft_and_queue_win_tweet
    try:
        result = draft_and_queue_win_tweet(deal_id)
        await broadcast({"type": "new_alerts", "count": 1})
        return result
    except Exception as e:
        raise HTTPException(400, str(e))

@app.post("/x/post/{action_id}")
async def post_approved_tweet(action_id: int):
    from x_connector import execute_approved_tweet
    try:
        result = execute_approved_tweet(action_id)
        return result
    except PermissionError as e:
        raise HTTPException(403, str(e))
    except Exception as e:
        raise HTTPException(400, str(e))

@app.post("/x/scan-wins")
async def scan_deal_wins():
    """Draft tweets for all recently closed deals that don't have a tweet queued."""
    import database as db
    from x_connector import draft_and_queue_win_tweet
    deals = db.fetchall(
        "SELECT id FROM deals WHERE stage='closed_won' ORDER BY created_at DESC LIMIT 5"
    )
    queued = []
    for d in deals:
        existing = db.fetchone(
            "SELECT id FROM action_queue WHERE deal_id=%s AND action_type='post_tweet' AND status IN ('PENDING_APPROVAL','APPROVED','EXECUTED')",
            (d["id"],)
        )
        if not existing:
            try:
                result = draft_and_queue_win_tweet(d["id"])
                queued.append(result)
            except Exception as e:
                print(f"  Tweet draft failed for {d['id']}: {e}")
    if queued:
        await broadcast({"type": "new_alerts", "count": len(queued)})
    return {"queued": len(queued), "drafts": queued}
