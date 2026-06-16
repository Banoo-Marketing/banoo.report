"""
Pulse — Client health monitoring sub-agent for Atlas.
Tracks active Banoo clients, flags churn risk, drafts check-in emails.
"""
import json
import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path

_HERE = Path(__file__).parent
_CHIEF = _HERE.parent / "chief"
_EMAIL_DB = _HERE.parent / "email-analyzer" / "email_cache.db"

try:
    from dotenv import load_dotenv
    load_dotenv(_HERE.parent.parent / "company-brain" / ".env")
    load_dotenv(_HERE.parent / ".env")
except ImportError:
    pass

import anthropic

PULSE_SYSTEM = """You are Pulse, the client health sub-agent for Atlas (Chief of Staff to Emod Vafa).

You monitor the health of Banoo Marketing's client relationships.

Active Banoo clients:
1. Gerry Poirier / AngeLink (gerry.poirier@angelink.com)
   - Services: Google Ads, digital marketing strategy
   - Status: Board budget approval pending, campaign kickoff scheduled
   - Key contacts also: Braden Bontempo @ Google (braden.bontempo@google.com)

2. Razi Rokhsefat / 416 Flowers (razi@416-flowers.com)
   - Services: SEO, Zoho email warmup, Mixpanel, blog, PR feature
   - Status: Active, needs retainer formalization
   - Vendor: Optiblack/Vishal Rewari for Mixpanel implementation

3. Pro Insulation Contracting (customerservice@proinsulationcontracting.com)
   - Services: Recurring digital marketing, web campaigns
   - Status: At-risk — pattern of meeting cancellations, Apr 15 meeting flagged

Other Banoo relationships to monitor:
- Brad Krieger / North Road Digital (brad@northroaddigital.ca) — clients absorbed, wants catch-up
- Talles Faria / Lodestar Digital (tfaria@lodestarmedia.ca) — programmatic ads collaboration
- Andrea Moore / Azira (andrea@azira.com) — DSP campaigns, billing needs attention
- Liam Bailey / ClickTech (liam.bailey@clicktech.com) — Microsoft/Bing Ads partnership pending

Client health scoring:
🟢 HEALTHY: Recent communication, active deliverables, payments current
🟡 WATCH: Reduced engagement, delayed responses, stalled deliverables
🔴 AT RISK: No recent contact, payments overdue, cancellation pattern, scope creep
💀 CHURNED: No response in 60+ days, contract ended

Your output for each client:
- Health score with emoji
- Last contact date
- Active deliverables status
- Risk factors
- Recommended action (draft check-in email if needed)
- Revenue at risk estimate if applicable"""


def _get_client_emails(client_email: str, limit: int = 20) -> list[dict]:
    if not _EMAIL_DB.exists():
        return []
    with sqlite3.connect(_EMAIL_DB) as c:
        c.row_factory = sqlite3.Row
        rows = c.execute("""
            SELECT sender, subject, date_str, date_ts, body_text
            FROM emails
            WHERE lower(sender) LIKE ? OR lower(recipients) LIKE ?
            ORDER BY date_ts DESC LIMIT ?
        """, (f"%{client_email.lower()}%", f"%{client_email.lower()}%", limit)).fetchall()
    return [dict(r) for r in rows]


def _get_all_client_emails(limit_per_client: int = 15) -> dict:
    clients = {
        "AngeLink (Gerry Poirier)": "gerry.poirier@angelink.com",
        "416 Flowers (Razi)": "razi@416-flowers.com",
        "Pro Insulation": "customerservice@proinsulationcontracting.com",
        "North Road Digital (Brad)": "brad@northroaddigital.ca",
        "Lodestar/Talles": "tfaria@lodestarmedia.ca",
        "Azira/Andrea": "andrea@azira.com",
    }
    result = {}
    for name, email in clients.items():
        emails = _get_client_emails(email, limit_per_client)
        if emails:
            result[name] = {
                "email": email,
                "thread_count": len(emails),
                "last_contact": emails[0]["date_str"] if emails else None,
                "recent_subjects": [e["subject"] for e in emails[:5]],
                "latest_preview": (emails[0].get("body_text") or "")[:300] if emails else "",
            }
        else:
            result[name] = {
                "email": email,
                "thread_count": 0,
                "last_contact": None,
                "recent_subjects": [],
                "latest_preview": "NO EMAILS IN CACHE",
            }
    return result


def _get_client_actions() -> list[dict]:
    import sys
    sys.path.insert(0, str(_CHIEF))
    import db
    all_actions = db.get_actions(status="OPEN", limit=100)
    client_keywords = [
        "gerry", "angelink", "razi", "416 flowers", "insulation", "campaign",
        "google ads", "seo", "client", "retainer", "azira", "lodestar",
        "brad", "northroad", "clicktech", "liam"
    ]
    return [a for a in all_actions if any(
        kw in (a.get("title") or "").lower() or kw in (a.get("from_name") or "").lower()
        for kw in client_keywords
    )]


def run_client_health_scan() -> str:
    """Full client health report across all active accounts."""
    client_data = _get_all_client_emails()
    actions = _get_client_actions()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    client = anthropic.Anthropic()
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=3000,
        system=[{"type": "text", "text": PULSE_SYSTEM, "cache_control": {"type": "ephemeral"}}],
        messages=[{
            "role": "user",
            "content": f"""Today is {today}. Run a full Banoo client health scan.

Client email data:
{json.dumps(client_data, indent=2)}

Open client-related actions:
{json.dumps([{
    'title': a['title'],
    'priority': a['priority'],
    'from': a.get('from_name'),
    'next': a.get('suggested_next')
} for a in actions], indent=2)}

For each client:
1. Health status (🟢/🟡/🔴/💀)
2. What's working
3. What's at risk
4. Recommended action
5. Draft a check-in email if 🟡 or 🔴

Then give a summary: total MRR at risk, highest-priority client action."""
        }],
    )
    return resp.content[0].text


def run_client_report(client_name_or_email: str) -> str:
    """Deep dive on a single client."""
    emails = _get_client_emails(client_name_or_email, limit=20)

    if not emails:
        # Try name-based lookup in DB
        import sys
        sys.path.insert(0, str(_CHIEF))
        import db, sqlite3 as sq
        with sq.connect(db.DB_PATH) as c:
            c.row_factory = sq.Row
            row = c.execute("""
                SELECT * FROM contacts
                WHERE lower(name) LIKE ? OR lower(email) LIKE ?
                ORDER BY strength DESC LIMIT 1
            """, (f"%{client_name_or_email.lower()}%", f"%{client_name_or_email.lower()}%")).fetchone()
            if row:
                return f"Found contact but no emails in cache for {dict(row)['name']}.\nSuggested action: {dict(row).get('suggested_action','')}"
        return f"No client data found for: {client_name_or_email}"

    client = anthropic.Anthropic()
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        system=PULSE_SYSTEM,
        messages=[{
            "role": "user",
            "content": f"""Give a full client health report for: {client_name_or_email}

Full email history ({len(emails)} emails, newest first):
{json.dumps([{
    'sender': e['sender'],
    'subject': e['subject'],
    'date': e['date_str'],
    'body': (e.get('body_text') or '')[:400]
} for e in emails], indent=2)}

Include:
1. Relationship timeline
2. Services being delivered
3. Current health status
4. Outstanding deliverables or promises
5. Risk factors
6. Draft check-in email if needed
7. Estimated MRR / engagement value"""
        }],
    )
    return resp.content[0].text


def run_churn_risk() -> str:
    """Identify which clients are most at risk of churning."""
    client_data = _get_all_client_emails(limit_per_client=10)
    client = anthropic.Anthropic()
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1500,
        system=PULSE_SYSTEM,
        messages=[{
            "role": "user",
            "content": f"""Based on this client email data, identify churn risk.

Rank clients from highest to lowest churn risk. For each at-risk client:
- Risk level (HIGH/MEDIUM/LOW)
- Reason
- What to do in the next 48 hours to prevent churn
- Draft a 3-sentence re-engagement email

Client data:
{json.dumps(client_data, indent=2)}"""
        }],
    )
    return resp.content[0].text


def run_draft_client_checkin(client_name_or_email: str, context: str = "") -> str:
    """Draft a client check-in email."""
    emails = _get_client_emails(client_name_or_email, limit=5)
    thread_context = ""
    if emails:
        thread_context = f"\nRecent thread:\n" + "\n".join(
            f"- [{e['date_str']}] {e['subject']}" for e in emails[:5]
        )

    client = anthropic.Anthropic()
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=800,
        system=PULSE_SYSTEM,
        messages=[{
            "role": "user",
            "content": f"""Draft a client check-in email for: {client_name_or_email}
{thread_context}
{f'Additional context: {context}' if context else ''}

Write a natural, non-desperate check-in email in Emod's voice.
Include a clear reason to reconnect and a soft call to action.
Subject line + body. Ready to send after Emod's approval."""
        }],
    )
    return resp.content[0].text


if __name__ == "__main__":
    import sys
    args = sys.argv[1:]
    cmd = args[0] if args else "scan"

    if cmd == "scan":
        print("\n  Pulse: Client health scan\n")
        print("  " + "─" * 60)
        print(run_client_health_scan())
    elif cmd == "churn":
        print("\n  Pulse: Churn risk analysis\n")
        print(run_churn_risk())
    elif cmd == "report" and len(args) > 1:
        print(f"\n  Pulse: Client report — {args[1]}\n")
        print(run_client_report(args[1]))
    elif cmd == "checkin" and len(args) > 1:
        context = args[2] if len(args) > 2 else ""
        print(f"\n  Pulse: Check-in draft for {args[1]}\n")
        print(run_draft_client_checkin(args[1], context))
    else:
        print("Usage: pulse.py [scan | churn | report <client> | checkin <client> [context]]")
