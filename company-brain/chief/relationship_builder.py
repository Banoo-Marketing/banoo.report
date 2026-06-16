"""
relationship_builder.py — Builds the contact relationship graph from the
email cache using Claude to classify relationships and extract context.

For each unique sender/contact:
  - Counts emails, calculates recency, computes strength score
  - Uses Claude to determine: role, relationship type, how we met,
    obligations, nurture potential, whether they're a business owner
"""
import json
import os
import re
import sqlite3
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
import anthropic
import db

_HERE = Path(__file__).parent

# Load API keys from .env
try:
    from dotenv import load_dotenv
    load_dotenv(_HERE.parent.parent / "company-brain" / ".env")
    load_dotenv(_HERE.parent / ".env")
except ImportError:
    pass
_EMAIL_DB = _HERE.parent / "email-analyzer" / "email_cache.db"

_SYSTEM = """You are an expert relationship analyst for Emod Vafa, a marketing professional and real estate agent based in Toronto, Canada. He runs Banoo Marketing (digital marketing / lead generation for businesses). He invests in real estate and stocks, has Iranian/Persian heritage, and is involved in Toronto arts communities.

Given emails involving a specific sender, determine who they are and what Emod's relationship with them is.

IMPORTANT RULES:
- Use ALL available signals: email domain, content, subject lines, tone, language used, shared activities
- Never return null for 'name' — use display name or a reasonable guess from email address
- For 'relationship', be specific — "Acquaintance" is a last resort, not a default:
  * Personal Gmail/Yahoo → likely Close friend or Family (especially Persian names)
  * Real estate board/MLS emails → Key business partner (TRREB, OREA, etc.)
  * Financing/lending company → Key business partner or Vendor
  * Marketing/SEO service → Vendor or Lead (business owner)
  * Client emails discussing marketing services → Client (Banoo)
  * Business owner discussing their business → Lead (business owner)
  * Persian language content → likely Family or Close friend
  * Rumi/spiritual/cultural community → Close friend or Acquaintance
  * Calendar invites from personal gmail → Close friend or Family
  * Real estate transactions → Key business partner
- For 'nurture_potential': if they run a business (any kind) and could benefit from digital marketing/lead gen, score 4-8; if ideal Banoo client, score 8-10; else 0-3
- For 'is_business_owner': true if they clearly run a business (any type)
- For 'suggested_action': always suggest a specific next step, never null

Return ONLY valid JSON:
{
  "name": "Full Name (required, never null)",
  "company": "company/org name or null",
  "role": "their role/title or null",
  "relationship": "one of: Family|Close friend|Key business partner|Client (Banoo)|Lead (business owner)|Vendor|Acquaintance|Needs rekindling|Mentor/Advisor",
  "how_we_met": "one sentence on context of this relationship (never null)",
  "is_business_owner": true or false,
  "obligations": ["any pending items Emod owes them"],
  "nurture_potential": 0-10,
  "nurture_notes": "why they could benefit from Banoo's digital marketing (or null if not applicable)",
  "suggested_action": "specific next action Emod should take with this person (never null)",
  "sentiment": "positive|neutral|negative"
}"""


def _get_emails_for_contact(email_addr: str, limit: int = 20) -> list[dict]:
    """Read emails from the email analyzer cache for a given sender."""
    if not _EMAIL_DB.exists():
        return []
    conn = sqlite3.connect(_EMAIL_DB)
    conn.row_factory = sqlite3.Row
    try:
        # Match sender email (handle "Name <email>" format)
        rows = conn.execute("""
        SELECT gmail_id, sender, subject, date_str, date_ts, body_text
        FROM emails
        WHERE lower(sender) LIKE ?
        ORDER BY date_ts DESC
        LIMIT ?
        """, (f"%{email_addr.lower()}%", limit)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def _get_all_senders(min_count: int = 2) -> list[tuple[str, int, str, str]]:
    """Return (email, count, first_date, last_date) for all senders with >= min_count emails."""
    if not _EMAIL_DB.exists():
        return []
    conn = sqlite3.connect(_EMAIL_DB)
    try:
        rows = conn.execute("""
        SELECT sender, COUNT(*) as cnt,
               MIN(date_str) as first_date, MAX(date_str) as last_date,
               MAX(date_ts) as last_ts
        FROM emails
        WHERE sender NOT LIKE '%noreply%'
          AND sender NOT LIKE '%no-reply%'
          AND sender NOT LIKE '%donotreply%'
          AND sender NOT LIKE '%notifications@%'
          AND sender NOT LIKE '%mailer@%'
          AND sender NOT LIKE '%newsletter@%'
          AND sender NOT LIKE '%support@%'
          AND sender NOT LIKE '%info@%'
        GROUP BY lower(sender)
        HAVING cnt >= ?
        ORDER BY cnt DESC
        """, (min_count,)).fetchall()
        return [(r[0], r[1], r[2], r[3], r[4]) for r in rows]
    finally:
        conn.close()


def _extract_email_addr(from_header: str) -> str:
    """Extract plain email from 'Name <email@domain.com>' format."""
    m = re.search(r'<([^>]+)>', from_header)
    if m:
        return m.group(1).lower().strip()
    return from_header.lower().strip()


def _extract_name(from_header: str) -> str:
    """Extract display name from 'Name <email@domain.com>' format."""
    m = re.match(r'^(.+?)\s*<', from_header)
    if m:
        name = m.group(1).strip().strip('"').strip("'")
        if name:
            return name
    # Fallback: use local part of email
    addr = _extract_email_addr(from_header)
    local = addr.split("@")[0]
    return local.replace(".", " ").replace("_", " ").title()


def _strength_score(count: int, last_ts: int) -> float:
    """Score 0-10 based on email frequency and recency."""
    now = datetime.now(timezone.utc).timestamp()
    days_ago = (now - last_ts) / 86400 if last_ts else 9999
    recency = max(0, 10 - days_ago / 36.5)  # full score if today, 0 if >1 year
    frequency = min(10, count / 5)           # 50+ emails = max frequency score
    return round((recency * 0.6 + frequency * 0.4), 2)


def _analyse_contact(from_header: str, count: int, emails: list[dict]) -> dict:
    """Use Claude to classify and profile a contact from their emails."""
    email_addr = _extract_email_addr(from_header)
    name = _extract_name(from_header)

    sample = []
    for e in emails[:10]:
        sample.append({
            "subject": e.get("subject", ""),
            "date": e.get("date_str", "")[:10],
            "preview": (e.get("body_text") or e.get("snippet", ""))[:300],
        })

    prompt = f"""Analyse Emod Vafa's relationship with this email contact.

Contact: {from_header}
Email address: {email_addr}
Total emails in inbox from/to them: {count}
Sample emails (newest first):
{json.dumps(sample, indent=2)}

Based on the email domain, content, subject lines, and tone, classify this person and their relationship to Emod. Return JSON only."""

    client = anthropic.Anthropic()
    for attempt in range(3):
        try:
            resp = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=512,
                system=[{"type": "text", "text": _SYSTEM, "cache_control": {"type": "ephemeral"}}],
                messages=[{"role": "user", "content": prompt}],
            )
            text = resp.content[0].text.strip()
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
                text = text.rsplit("```", 1)[0]
            result = json.loads(text.strip())
            result["email"] = email_addr
            result["name"] = result.get("name") or name
            result["email_count"] = count
            return result
        except (json.JSONDecodeError, Exception) as e:
            if attempt == 2:
                return {
                    "email": email_addr, "name": name, "company": None,
                    "role": None, "relationship": "Acquaintance",
                    "how_we_met": None, "is_business_owner": False,
                    "obligations": [], "nurture_potential": 0,
                    "nurture_notes": None, "suggested_action": None,
                    "sentiment": "neutral", "email_count": count,
                }
            time.sleep(2 ** attempt)


def build_relationship_graph(
    min_email_count: int = 2,
    max_contacts: int = 200,
    verbose: bool = True,
) -> dict:
    """
    Main entry point. Builds relationship profiles for all significant contacts.
    Returns summary stats.
    """
    db.init()
    senders = _get_all_senders(min_count=min_email_count)[:max_contacts]

    if not senders:
        return {"error": "No emails in cache. Run: python ../email-analyzer/main.py fetch first."}

    if verbose:
        print(f"Building relationship graph for {len(senders)} contacts...")

    processed = 0
    for from_header, count, first_date, last_date, last_ts in senders:
        email_addr = _extract_email_addr(from_header)

        # Skip if recently updated
        existing = db.get_contact(email_addr)
        if existing and existing.get("updated_at", "") > "2026-01-01":
            processed += 1
            if verbose:
                print(f"  [{processed}/{len(senders)}] Skip (cached): {email_addr}", end="\r")
            continue

        emails = _get_emails_for_contact(email_addr)
        strength = _strength_score(count, last_ts or 0)

        if verbose:
            print(f"  [{processed+1}/{len(senders)}] Analysing: {email_addr[:40]:40} ({count} emails)", end="\r")

        try:
            profile = _analyse_contact(from_header, count, emails)
        except Exception as e:
            print(f"\n  Warning: failed to analyse {email_addr}: {e}")
            profile = {"email": email_addr, "name": _extract_name(from_header)}

        db.upsert_contact({
            **profile,
            "strength": strength,
            "email_count": count,
            "first_contact": first_date,
            "last_contact": last_date,
            # Normalize Claude's field names to DB column names
            "nurture_score": profile.get("nurture_potential") or profile.get("nurture_score", 0),
            "is_business_owner": 1 if profile.get("is_business_owner") else 0,
        })
        processed += 1
        time.sleep(0.3)  # rate limit Claude calls

    if verbose:
        print(f"\nDone. {processed} contacts profiled.")

    st = db.stats()
    return {"contacts_built": processed, "total_in_db": st["contacts"]}
