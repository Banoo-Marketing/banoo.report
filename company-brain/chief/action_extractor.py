"""
action_extractor.py — Scans emails for tasks, follow-ups, promises, and decisions.
Uses Claude to extract structured action items and stores them in chief.db.
"""
import json
import re
import sqlite3
import time
from pathlib import Path
import anthropic
import db

_HERE = Path(__file__).parent
_EMAIL_DB = _HERE.parent / "email-analyzer" / "email_cache.db"

try:
    from dotenv import load_dotenv
    load_dotenv(_HERE.parent.parent / "company-brain" / ".env")
    load_dotenv(_HERE.parent / ".env")
except ImportError:
    pass

_SYSTEM = """You are an expert at extracting action items from emails.

For each email, identify: tasks asked of me, follow-ups I need to send,
promises/commitments I made, and decisions I need to make.

Return ONLY valid JSON:
{
  "actions": [
    {
      "title": "Clear, specific action title (max 80 chars)",
      "action_type": "task|followup|promise|decision",
      "priority": "HIGH|MEDIUM|LOW",
      "deadline": "YYYY-MM-DD or null",
      "suggested_next": "One sentence on the best next step"
    }
  ]
}

Return empty actions array if no clear action items exist.
Priority rules:
- HIGH: explicit deadlines, urgent language, important contacts
- MEDIUM: requests without deadline, follow-ups owed
- LOW: nice-to-have, informational"""


def _get_unscanned_emails(limit: int = 500) -> list[dict]:
    """Get emails not yet scanned for actions."""
    if not _EMAIL_DB.exists():
        return []
    existing_ids = set()
    try:
        with sqlite3.connect(db.DB_PATH) as c:
            rows = c.execute("SELECT DISTINCT gmail_id FROM actions WHERE gmail_id != ''").fetchall()
            existing_ids = {r[0] for r in rows}
    except Exception:
        pass

    conn = sqlite3.connect(_EMAIL_DB)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute("""
        SELECT e.gmail_id, e.sender, e.subject, e.date_str, e.body_text
        FROM emails e
        LEFT JOIN processing p ON p.gmail_id = e.gmail_id
        WHERE p.gmail_id IS NOT NULL   -- only processed emails
        ORDER BY e.date_ts DESC
        LIMIT ?
        """, (limit * 3,)).fetchall()
        emails = [dict(r) for r in rows if r["gmail_id"] not in existing_ids]
        return emails[:limit]
    finally:
        conn.close()


def _extract_actions_batch(emails: list[dict]) -> list[dict]:
    """Send a batch of emails to Claude and extract action items."""
    client = anthropic.Anthropic()
    batch_input = []
    for e in emails:
        batch_input.append({
            "gmail_id": e["gmail_id"],
            "from": e.get("sender", ""),
            "subject": e.get("subject", ""),
            "date": e.get("date_str", "")[:10],
            "body": (e.get("body_text") or e.get("snippet", ""))[:600],
        })

    prompt = f"""Extract action items from these {len(emails)} emails. For each email with action items, list them.

Emails:
{json.dumps(batch_input, indent=2)}

Return JSON with actions grouped by gmail_id:
{{
  "by_email": {{
    "gmail_id_1": {{ "from": "...", "actions": [...] }},
    "gmail_id_2": {{ "from": "...", "actions": [] }}
  }}
}}"""

    for attempt in range(3):
        try:
            resp = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=2048,
                system=[{"type": "text", "text": _SYSTEM, "cache_control": {"type": "ephemeral"}}],
                messages=[{"role": "user", "content": prompt}],
            )
            text = resp.content[0].text.strip()
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
                text = text.rsplit("```", 1)[0]
            return json.loads(text.strip())
        except Exception as e:
            if attempt == 2:
                return {"by_email": {}}
            time.sleep(2 ** attempt)


def _extract_sender_name(from_header: str) -> str:
    m = re.match(r'^(.+?)\s*<', from_header)
    if m:
        return m.group(1).strip().strip('"')
    return from_header.split("@")[0].replace(".", " ").title()


def extract_actions(max_emails: int = 200, verbose: bool = True) -> dict:
    """
    Scan emails for action items and store in chief.db.
    Returns summary of actions found.
    """
    db.init()
    emails = _get_unscanned_emails(limit=max_emails)

    if not emails:
        if verbose:
            print("No new emails to scan for actions.")
        return {"actions_found": 0}

    if verbose:
        print(f"Scanning {len(emails)} emails for action items...")

    total_actions = 0
    batch_size = 15

    for i in range(0, len(emails), batch_size):
        batch = emails[i: i + batch_size]
        batch_num = i // batch_size + 1
        total_batches = (len(emails) + batch_size - 1) // batch_size

        if verbose:
            print(f"  Batch {batch_num}/{total_batches}...", end="\r")

        try:
            result = _extract_actions_batch(batch)
            by_email = result.get("by_email", {})

            for email in batch:
                gid = email["gmail_id"]
                email_result = by_email.get(gid, {})
                actions = email_result.get("actions", [])

                for action in actions:
                    if not action.get("title"):
                        continue
                    db.add_action({
                        "title": action["title"],
                        "from_email": _extract_sender_name(email.get("sender", "")),
                        "from_name": _extract_sender_name(email.get("sender", "")),
                        "gmail_id": gid,
                        "deadline": action.get("deadline"),
                        "priority": action.get("priority", "MEDIUM"),
                        "action_type": action.get("action_type", "task"),
                        "suggested_next": action.get("suggested_next", ""),
                    })
                    total_actions += 1

        except Exception as e:
            if verbose:
                print(f"\n  Batch {batch_num} failed: {e}")
        time.sleep(0.5)

    if verbose:
        print(f"\nFound {total_actions} action items across {len(emails)} emails.")
    return {"actions_found": total_actions, "emails_scanned": len(emails)}
