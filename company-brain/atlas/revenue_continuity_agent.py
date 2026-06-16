"""
revenue_continuity_agent.py — Silent client churn prevention.

Identifies quiet clients and generates lightweight strategic check-ins.
NOT aggressive sales — relationship maintenance and trust continuity.
Max 3 LLM outreach calls per run.
"""
from __future__ import annotations
import sys
from datetime import date, datetime
from pathlib import Path

_HERE = Path(__file__).parent   # atlas/
_CHIEF = _HERE.parent / "chief"

sys.path.insert(0, str(_CHIEF))
sys.path.insert(0, str(_HERE))

try:
    from dotenv import load_dotenv
    load_dotenv(_HERE.parent.parent / "company-brain" / ".env")
except ImportError:
    pass

import db

_MAX_OUTREACH = 3
_MIN_DAYS_QUIET = 30
_MIN_RELATIONSHIP_SCORE = 6.0


def _days_since(date_str: str | None) -> int | None:
    if not date_str:
        return None
    try:
        d = datetime.fromisoformat(str(date_str)[:10]).date()
        return (date.today() - d).days
    except (ValueError, TypeError):
        return None


def find_quiet_clients(days: int = 30) -> list[dict]:
    """
    Return contacts with no recent contact above relationship_score threshold.
    Checks relationship_memory table.
    """
    db.init()
    quiet = []

    try:
        contacts = db.get_relationships(type="client")
        for c in contacts:
            d = _days_since(c.get("last_contact"))
            score = c.get("relationship_score", 0)
            if score >= _MIN_RELATIONSHIP_SCORE and (d is None or d >= days):
                quiet.append({
                    "name": c["name"],
                    "organization": c.get("organization", ""),
                    "notes": c.get("notes", ""),
                    "days_quiet": d,
                    "score": score,
                    "source": "relationship_memory",
                })
    except Exception:
        pass

    quiet.sort(key=lambda x: (x.get("days_quiet") or 999), reverse=True)
    return quiet


def generate_touchpoint(contact: dict) -> str:
    """
    Generate one contextual, non-sales outreach. Uses Claude API.
    References client's business context and history.
    """
    try:
        import anthropic
        client = anthropic.Anthropic()

        days_quiet = contact.get("days_quiet")
        time_note = f"{days_quiet} days" if days_quiet else "some time"
        org = contact.get("organization") or ""
        notes = contact.get("notes") or ""

        prompt = f"""Draft a brief, genuine check-in message from Emod Vafa to {contact['name']}.

Context:
- Client at: {org or 'their company'}
- Background: {notes[:250] or 'marketing client'}
- Last contact: {time_note} ago

Requirements:
- 3-4 sentences only
- Tone: warm, peer-to-peer, NOT salesy
- Mention one specific marketing idea or observation relevant to their business
  (e.g., a CRM cleanup opportunity, seasonal campaign, retention push, or automation)
- Feel like "I thought of you" not "I want your business"
- Sign off as Emod
- Plain text, no subject line"""

        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=180,
            messages=[{"role": "user", "content": prompt}]
        )
        return resp.content[0].text.strip()
    except Exception as e:
        return f"[Touchpoint generation failed: {e}]"


def run_pipeline() -> dict:
    """Returns triage dict with quiet clients and touchpoint drafts."""
    db.init()
    quiet = find_quiet_clients(days=_MIN_DAYS_QUIET)

    exceptions = []
    touchpoints = []

    for contact in quiet[:_MAX_OUTREACH]:
        draft = generate_touchpoint(contact)
        touchpoints.append({
            "name": contact["name"],
            "organization": contact.get("organization", ""),
            "days_quiet": contact.get("days_quiet"),
            "draft": draft,
        })
        if contact.get("score", 0) >= 8 and (contact.get("days_quiet") or 0) >= 60:
            exceptions.append(
                f"High-value client {contact['name']} silent for "
                f"{contact.get('days_quiet','?')} days (score {contact.get('score',0):.0f}/10)"
            )

    total_quiet = len(quiet)
    summary = (
        f"Revenue continuity: {total_quiet} quiet client(s) identified. "
        f"Touchpoints drafted for {len(touchpoints)}: "
        f"{', '.join(t['name'] for t in touchpoints) or 'none'}."
    )

    return {
        "agent_name": "revenue_continuity",
        "summary": summary,
        "exceptions": exceptions,
        "has_escalation": len(exceptions) > 0,
        "escalation_reason": "; ".join(exceptions),
        "touchpoints": touchpoints,
    }


if __name__ == "__main__":
    db.init()
    result = run_pipeline()
    print(f"\n  Revenue Continuity Agent\n  {'─'*50}")
    print(f"  {result['summary']}")
    for t in result.get("touchpoints", []):
        days = t.get("days_quiet")
        print(f"\n  [{t['name']} — {t.get('organization','')} — {days or '?'} days quiet]")
        print(f"  {t['draft']}")
