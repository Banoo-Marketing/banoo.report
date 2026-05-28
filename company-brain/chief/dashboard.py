"""
dashboard.py — FastAPI read-only web dashboard for the Chief of Staff.
Run: python dashboard.py   → http://localhost:8001
"""
import json
import sqlite3
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import db

app = FastAPI(title="Chief of Staff", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET"])

_HERE = Path(__file__).parent


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/stats")
def api_stats():
    db.init()
    st = db.stats()
    email_db = _HERE.parent / "email-analyzer" / "email_cache.db"
    if email_db.exists():
        with sqlite3.connect(email_db) as c:
            st["emails_total"] = c.execute("SELECT COUNT(*) FROM emails").fetchone()[0]
            st["emails_processed"] = c.execute("SELECT COUNT(*) FROM processing").fetchone()[0]
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
    return "<h1>Chief of Staff</h1><p>Template not found.</p>"


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8001)
