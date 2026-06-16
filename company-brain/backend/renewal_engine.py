"""
Renewal Engine
─────────────
1. Scans deals for upcoming renewals (30 / 14 / 7 days out)
2. Checks if a renewal action was already queued (dedup)
3. Drafts a personalised email via Claude API
4. Queues the action for human approval – NEVER auto-sends
"""
from datetime import date, timedelta
from typing import Any
import json
import anthropic
import database as db
from config import settings


def get_upcoming_renewals(days_ahead: int = 30) -> list[dict]:
    """Return all closed_won deals with renewal_date within `days_ahead` days."""
    today = date.today()
    future = today + timedelta(days=days_ahead)

    rows = db.fetchall(
        """
        SELECT d.*, c.name AS contact_name, c.email AS contact_email,
               c.industry, c.clv_tier
        FROM deals d
        LEFT JOIN contacts c ON c.id = d.contact_id
        WHERE d.renewal_date BETWEEN %s AND %s
          AND d.stage = 'closed_won'
        ORDER BY d.renewal_date ASC
        """,
        (today, future),
    )

    for deal in rows:
        delta = (deal["renewal_date"] - today).days
        deal["days_to_renewal"] = delta
        deal["urgency"] = (
            "HIGH" if delta <= 7 else
            "MEDIUM" if delta <= 14 else
            "LOW"
        )

    return rows


def already_queued(deal_id: str) -> bool:
    """Return True if a renewal_email action is already pending or approved for this deal."""
    row = db.fetchone(
        """
        SELECT id FROM action_queue
        WHERE deal_id = %s
          AND action_type = 'renewal_email'
          AND status IN ('PENDING_APPROVAL', 'APPROVED', 'EXECUTED')
        LIMIT 1
        """,
        (deal_id,),
    )
    return row is not None


def draft_renewal_email(deal: dict[str, Any]) -> dict[str, str]:
    """
    Use Claude to draft a short, personalised renewal email.
    Returns {"subject": "...", "body": "..."}.
    """
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    prompt = f"""
You are a sales assistant helping draft renewal emails for a B2B SaaS company.

Draft a warm, professional renewal email for this client:
- Contact: {deal.get("contact_name", "Valued Customer")}
- Company: {deal.get("company", "your company")}
- Product/Deal: {deal.get("name", "your subscription")}
- Renewal date: {deal.get("renewal_date")}
- Contract value: ${deal.get("amount", 0):,.2f}
- Industry: {deal.get("industry", "Unknown")}
- Client tier: {deal.get("clv_tier", "STANDARD")}
- Days to renewal: {deal.get("days_to_renewal", "?")}

Rules:
- Maximum 150 words in the body
- Use first name only for the greeting
- Reference the value/outcome the client likely got (infer from industry)
- One clear CTA: book a 15-min call or reply to confirm renewal
- No generic filler phrases like "I hope this email finds you well"
- Match urgency: HIGH = friendly urgency, LOW = warm early outreach

Return ONLY valid JSON, no markdown, no explanation:
{{"subject": "...", "body": "..."}}
""".strip()

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=600,
        messages=[{"role": "user", "content": prompt}],
    )

    return json.loads(response.content[0].text)


def queue_renewal_action(deal: dict, drafted_email: dict) -> int:
    """Insert into action_queue for human review. Returns the new queue item id."""
    db.execute(
        """
        INSERT INTO action_queue
            (action_type, deal_id, contact_id, payload, urgency, reason, status)
        VALUES
            ('renewal_email', %s, %s, %s, %s, %s, 'PENDING_APPROVAL')
        """,
        (
            deal["id"],
            deal.get("contact_id"),
            json.dumps({
                "to": deal.get("contact_email"),
                "contact_name": deal.get("contact_name"),
                "company": deal.get("company"),
                "subject": drafted_email.get("subject"),
                "body": drafted_email.get("body"),
                "deal_name": deal.get("name"),
                "amount": float(deal.get("amount", 0)),
                "renewal_date": str(deal.get("renewal_date")),
            }),
            deal["urgency"],
            f"Renewal in {deal['days_to_renewal']} days – no action queued yet",
        ),
    )

    # Audit log
    db.execute(
        """
        INSERT INTO audit_log (action_type, deal_id, actor, details)
        VALUES ('renewal_email_queued', %s, 'system', %s)
        """,
        (deal["id"], json.dumps({"days_to_renewal": deal["days_to_renewal"]})),
    )

    row = db.fetchone(
        "SELECT id FROM action_queue WHERE deal_id=%s AND action_type='renewal_email' "
        "ORDER BY created_at DESC LIMIT 1",
        (deal["id"],),
    )
    return row["id"] if row else -1


def run_renewal_scan() -> list[dict]:
    """
    Full scan: find renewals → skip if already queued → draft → queue.
    Called by Celery beat task every 15 minutes.
    Returns list of newly queued action summaries.
    """
    deals = get_upcoming_renewals(days_ahead=30)
    queued = []

    for deal in deals:
        if already_queued(deal["id"]):
            continue

        try:
            drafted = draft_renewal_email(deal)
            action_id = queue_renewal_action(deal, drafted)
            queued.append({
                "action_id": action_id,
                "deal_id": deal["id"],
                "company": deal["company"],
                "days_to_renewal": deal["days_to_renewal"],
                "urgency": deal["urgency"],
            })
            print(f"  📧 Queued renewal email for {deal['company']} (action #{action_id})")
        except Exception as e:
            print(f"  ⚠️  Failed to queue renewal for deal {deal['id']}: {e}")

    return queued
