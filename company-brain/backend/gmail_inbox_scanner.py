"""
Gmail Inbox Scanner
────────────────────
Runs on a schedule (every hour via Celery Beat).

What it does:
  1. Reads emails from the last 24 hours
  2. Extracts renewal signals → queues renewal_email actions
  3. Matches senders to existing contacts → updates last_seen
  4. Detects contacts with no activity for 30+ days → queues touch_base actions
  5. All actions go to PENDING_APPROVAL — nothing auto-sends

Claude is used for:
  - Extracting renewal signals from email text
  - Drafting personalised touch-base emails
"""
import json
import anthropic
from datetime import datetime, timezone
import database as db
from config import settings

_client = None


def _claude():
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    return _client


# ── helpers ───────────────────────────────────────────────────────────────────

def _already_queued(action_type: str, contact_id: str) -> bool:
    row = db.fetchone(
        """SELECT id FROM action_queue
           WHERE action_type = %s AND contact_id = %s
             AND status IN ('PENDING_APPROVAL','APPROVED')
             AND created_at > NOW() - INTERVAL '7 days'""",
        (action_type, contact_id),
    )
    return row is not None


def _match_contact(email_from: str) -> dict | None:
    """Try to find a contact by email address extracted from the From header."""
    # Extract plain email from "Name <email@domain.com>" format
    addr = email_from
    if "<" in email_from:
        addr = email_from.split("<")[1].rstrip(">").strip()
    return db.fetchone("SELECT * FROM contacts WHERE email = %s", (addr,))


# ── step 1: renewal signals ───────────────────────────────────────────────────

def _process_renewal_signals(emails: list[dict]) -> list[dict]:
    """Extract renewal signals from emails and queue actions."""
    from gmail_reader import extract_renewal_signals
    signals = extract_renewal_signals(emails)
    queued = []

    for signal in signals:
        contact = _match_contact(signal.get("from", ""))
        deal = None
        if contact:
            deal = db.fetchone(
                "SELECT * FROM deals WHERE contact_id = %s AND stage = 'closed_won' ORDER BY renewal_date ASC LIMIT 1",
                (contact["id"],),
            )

        if _already_queued("renewal_email", contact["id"] if contact else "unknown"):
            continue

        payload = {
            "source": "gmail_scan",
            "signal": signal,
            "contact_id": contact["id"] if contact else None,
            "deal_id": deal["id"] if deal else None,
        }

        db.execute(
            """INSERT INTO action_queue
               (action_type, deal_id, contact_id, urgency, status, payload, suggested_message)
               VALUES ('renewal_email', %s, %s, 'HIGH', 'PENDING_APPROVAL', %s, %s)""",
            (
                deal["id"] if deal else None,
                contact["id"] if contact else None,
                json.dumps(payload),
                f"Renewal signal detected from {signal.get('from','unknown')}: {signal.get('action_needed','')}",
            ),
        )
        db.execute(
            "INSERT INTO audit_log (action_type, deal_id, actor, details) VALUES ('gmail_renewal_signal', %s, 'system', %s)",
            (deal["id"] if deal else None, json.dumps({"from": signal.get("from"), "subject": signal.get("subject")})),
        )
        queued.append(signal)
        print(f"  Renewal signal queued: {signal.get('client_name')} — {signal.get('action_needed')}")

    return queued


# ── step 2: update contact last_seen ─────────────────────────────────────────

def _update_contact_activity(emails: list[dict]) -> int:
    """Update days_since_activity for contacts we received emails from."""
    updated = 0
    for email in emails:
        contact = _match_contact(email["from"])
        if contact:
            db.execute(
                "UPDATE contacts SET days_since_activity = 0 WHERE id = %s",
                (contact["id"],),
            )
            updated += 1
    return updated


# ── step 3: detect follow-up gaps ────────────────────────────────────────────

def _draft_touchbase(contact: dict) -> str:
    """Use Claude to draft a personalised touch-base email."""
    prompt = f"""Draft a short, warm, professional touch-base email to a client we haven't contacted in a while.

Contact name: {contact['name']}
Company: {contact.get('company', 'their company')}
Industry: {contact.get('industry', 'unknown')}
CLV tier: {contact.get('clv_tier', 'unknown')}
Days since last activity: {contact.get('days_since_activity', '30+')}

Rules:
- 3-5 sentences max
- Friendly, not pushy
- Ask one open-ended question about their business
- No made-up specifics
- Return ONLY the email body, no subject line
"""
    response = _claude().messages.create(
        model="claude-sonnet-4-6",
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text.strip()


def _process_followup_gaps(threshold_days: int = 30) -> list[dict]:
    """Find contacts with no recent action activity and draft touch-base emails."""
    stale = db.fetchall(
        """SELECT c.*,
                  COALESCE(
                    EXTRACT(DAY FROM NOW() - MAX(aq.created_at))::int,
                    EXTRACT(DAY FROM NOW() - c.created_at)::int
                  ) AS days_inactive
           FROM contacts c
           LEFT JOIN action_queue aq ON aq.contact_id = c.id
           WHERE c.clv_tier IN ('PLATINUM', 'GOLD')
           GROUP BY c.id
           HAVING COALESCE(MAX(aq.created_at), c.created_at) < NOW() - INTERVAL '%s days'
           ORDER BY c.clv_score DESC
           LIMIT 10""",
        (threshold_days,),
    )
    queued = []

    for contact in stale:
        if _already_queued("touch_base", contact["id"]):
            continue

        try:
            body = _draft_touchbase(contact)
        except Exception as e:
            print(f"  Draft failed for {contact['name']}: {e}")
            continue

        urgency = "HIGH" if contact.get("clv_tier") == "PLATINUM" else "MEDIUM"

        db.execute(
            """INSERT INTO action_queue
               (action_type, contact_id, urgency, status, payload, suggested_message)
               VALUES ('touch_base', %s, %s, 'PENDING_APPROVAL', %s, %s)""",
            (
                contact["id"],
                urgency,
                json.dumps({"days_inactive": contact.get("days_since_activity"), "clv_tier": contact.get("clv_tier")}),
                body,
            ),
        )
        db.execute(
            "INSERT INTO audit_log (action_type, actor, details) VALUES ('touchbase_queued', 'system', %s)",
            (json.dumps({"contact": contact["name"], "days_inactive": contact.get("days_since_activity")}),),
        )
        queued.append({"contact": contact["name"], "tier": contact.get("clv_tier"), "days": contact.get("days_since_activity")})
        print(f"  Touch-base queued: {contact['name']} ({contact.get('clv_tier')}, {contact.get('days_since_activity')}d inactive)")

    return queued


# ── main entry point ──────────────────────────────────────────────────────────

def run_inbox_scan(hours_back: int = 24) -> dict:
    """
    Full inbox scan pipeline. Called by Celery Beat every hour.
    Returns summary of what was queued.
    """
    if not settings.google_client_id or not settings.google_client_secret:
        return {"skipped": "Gmail not configured"}

    import gmail_auth
    if not gmail_auth.is_connected():
        return {"skipped": "Gmail not connected"}

    print(f"[Gmail Scanner] Starting inbox scan (last {hours_back}h)...")

    # Fetch recent emails
    from gmail_reader import get_unread_emails
    try:
        emails = get_unread_emails(max_results=50)
    except Exception as e:
        return {"error": f"Gmail fetch failed: {e}"}

    print(f"[Gmail Scanner] {len(emails)} emails fetched")

    renewal_queued = _process_renewal_signals(emails)
    contacts_updated = _update_contact_activity(emails)
    touchbase_queued = _process_followup_gaps(threshold_days=30)

    summary = {
        "emails_scanned": len(emails),
        "renewal_signals_queued": len(renewal_queued),
        "contacts_updated": contacts_updated,
        "touchbase_emails_queued": len(touchbase_queued),
        "touchbase_details": touchbase_queued,
        "scanned_at": datetime.now(timezone.utc).isoformat(),
    }

    print(f"[Gmail Scanner] Done — {len(renewal_queued)} renewals, {len(touchbase_queued)} touch-bases queued")
    return summary
