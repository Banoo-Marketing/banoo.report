"""
Relay — Email drafting & inbox management sub-agent for Atlas.
Reads Emod's inbox, identifies what needs replies, drafts in his voice.
Nothing sends without approval.
"""
import json
import sqlite3
from datetime import datetime, timezone
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

RELAY_SYSTEM = """You are Relay, the email sub-agent for Atlas (Chief of Staff to Emod Vafa).

Your job: read Emod's inbox, decide what needs a reply, draft it perfectly.

About Emod:
- Founder of Banoo Marketing (Toronto digital marketing agency)
- Licensed REALTOR® (Forest Hill Real Estate, Yorkville)
- Iranian/Persian heritage, bilingual English/Farsi
- Direct, professional tone in business emails
- Warm and personal with family, friends, community
- Currently in Iran using VPN

Email voice rules:
- Business emails: concise, confident, action-oriented. No filler phrases.
- Client emails: professional warmth. Always include a clear next step.
- Real estate: formal, precise. Include REALTOR® context when relevant.
- Personal/family: natural, warm, brief.
- Hiring/applicants: clear expectations, respectful of their time.

Signatures to use:
- Business: "Best,\\nEmod Vafa\\nBanoo Marketing\\nemod@banoo.marketing"
- Real estate: "Best regards,\\nEmod Vafa | REALTOR®\\nForest Hill Real Estate Inc., Brokerage"
- Personal: "Emod"

For each email that needs a reply, output:
1. FROM / SUBJECT / URGENCY (HIGH/MEDIUM/LOW)
2. WHAT THEY WANT (one sentence)
3. DRAFT REPLY (ready to send)
4. RECOMMENDED ACTION: SEND AS-IS | EMOD TO REVIEW | EMOD TO PERSONALISE
5. SIGNATURE: which one to use

Skip: automated emails, newsletters, calendar notifications, bank alerts,
marketing, job board notifications. Focus on humans waiting for Emod."""


def _get_recent_human_emails(limit: int = 20) -> list[dict]:
    if not _EMAIL_DB.exists():
        return []
    with sqlite3.connect(_EMAIL_DB) as c:
        c.row_factory = sqlite3.Row
        rows = c.execute("""
            SELECT sender, subject, date_str, date_ts, body_text
            FROM emails
            WHERE sender NOT LIKE '%noreply%'
              AND sender NOT LIKE '%no-reply%'
              AND sender NOT LIKE '%notification%'
              AND sender NOT LIKE '%calendar-notification%'
              AND sender NOT LIKE '%alerts%'
              AND sender NOT LIKE '%newsletter%'
              AND sender NOT LIKE '%linkedin%'
              AND sender NOT LIKE '%google%'
              AND sender NOT LIKE '%amazon%'
              AND sender NOT LIKE '%audible%'
              AND sender NOT LIKE '%porkbun%'
              AND sender NOT LIKE '%questrade%'
              AND sender NOT LIKE '%rbc%'
              AND sender NOT LIKE '%samsung%'
              AND sender NOT LIKE '%ikea%'
              AND sender NOT LIKE '%passiv%'
              AND length(body_text) > 80
            ORDER BY date_ts DESC
            LIMIT ?
        """, (limit,)).fetchall()
    return [dict(r) for r in rows]


def _get_flagged_threads() -> list[dict]:
    """Get emails from known contacts with open actions."""
    import sys
    sys.path.insert(0, str(_CHIEF))
    import db
    actions = db.get_actions(status="OPEN", limit=30)
    flagged = []
    seen = set()
    for a in actions:
        email = a.get("from_email", "")
        if email and email not in seen:
            seen.add(email)
            flagged.append({
                "email": email,
                "name": a.get("from_name", ""),
                "pending_action": a.get("title", ""),
            })
    return flagged


def run_inbox_scan(limit: int = 20) -> str:
    """Scan inbox and draft replies. Returns formatted report for Emod's review."""
    emails = _get_recent_human_emails(limit)
    if not emails:
        return "Relay: No recent human emails found in cache."

    flagged = _get_flagged_threads()
    flagged_emails = {f["email"].lower() for f in flagged}

    # Annotate emails from contacts with open actions
    for e in emails:
        sender_lower = e.get("sender", "").lower()
        e["has_open_action"] = any(fe in sender_lower for fe in flagged_emails)

    client = anthropic.Anthropic()
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=3000,
        system=[{"type": "text", "text": RELAY_SYSTEM, "cache_control": {"type": "ephemeral"}}],
        messages=[{
            "role": "user",
            "content": f"""Review these {len(emails)} recent emails from real people.
Contacts with open action items (prioritise these): {json.dumps([f['email'] for f in flagged], indent=2)}

Emails:
{json.dumps([{
    'sender': e['sender'],
    'subject': e['subject'],
    'date': e['date_str'],
    'body_preview': (e.get('body_text') or '')[:400],
    'has_open_action': e.get('has_open_action', False)
} for e in emails], indent=2)}

Identify which need replies and draft them."""
        }],
    )
    return resp.content[0].text


def run_thread_summary(contact_email: str) -> str:
    """Summarise the full email thread with a specific contact."""
    if not _EMAIL_DB.exists():
        return "No email cache found."

    with sqlite3.connect(_EMAIL_DB) as c:
        c.row_factory = sqlite3.Row
        rows = c.execute("""
            SELECT sender, subject, date_str, body_text
            FROM emails
            WHERE lower(sender) LIKE ? OR lower(recipients) LIKE ?
            ORDER BY date_ts DESC LIMIT 20
        """, (f"%{contact_email.lower()}%", f"%{contact_email.lower()}%")).fetchall()

    if not rows:
        return f"No emails found for {contact_email}"

    emails = [dict(r) for r in rows]
    client = anthropic.Anthropic()
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=RELAY_SYSTEM,
        messages=[{
            "role": "user",
            "content": f"""Summarise the full email history with {contact_email}.
What is the relationship, what has been discussed, what is unresolved, what does Emod owe them or vice versa?

Emails (newest first):
{json.dumps([{
    'sender': e['sender'],
    'subject': e['subject'],
    'date': e['date_str'],
    'body': (e.get('body_text') or '')[:500]
} for e in emails], indent=2)}"""
        }],
    )
    return resp.content[0].text


def run_draft_reply(contact_email: str, instruction: str = "") -> str:
    """Draft a specific reply to a contact, optionally with instructions."""
    summary = run_thread_summary(contact_email)
    client = anthropic.Anthropic()
    instruction_text = f"\nSpecific instruction: {instruction}" if instruction else ""
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=RELAY_SYSTEM,
        messages=[{
            "role": "user",
            "content": f"""Draft a reply to {contact_email}.

Thread summary:
{summary}
{instruction_text}

Write the email ready to send. Include subject line."""
        }],
    )
    return resp.content[0].text


if __name__ == "__main__":
    import sys
    args = sys.argv[1:]
    if not args or args[0] == "scan":
        n = int(args[1]) if len(args) > 1 else 20
        print("\n  Relay: Scanning inbox for emails needing replies...\n")
        print("  " + "─" * 60)
        print(run_inbox_scan(n))
    elif args[0] == "thread" and len(args) > 1:
        print(f"\n  Relay: Thread summary for {args[1]}\n")
        print(run_thread_summary(args[1]))
    elif args[0] == "draft" and len(args) > 1:
        instruction = args[2] if len(args) > 2 else ""
        print(f"\n  Relay: Drafting reply to {args[1]}\n")
        print(run_draft_reply(args[1], instruction))
    else:
        print("Usage: relay.py [scan [n]] | [thread <email>] | [draft <email> [instruction]]")
