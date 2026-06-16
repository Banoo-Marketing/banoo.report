"""
relationship_agent.py — Relationship Intelligence Agent.

Analyzes relationship_memory, detects decay, generates contextual outreach.
Runs daily. Caps LLM outreach calls at 3 per run (highest decay first).
"""
from __future__ import annotations
import sys
from datetime import datetime, timezone, date
from pathlib import Path

_HERE = Path(__file__).parent        # atlas/relationships/
_ATLAS = _HERE.parent                 # atlas/
_CHIEF = _ATLAS.parent / "chief"

sys.path.insert(0, str(_CHIEF))
sys.path.insert(0, str(_ATLAS))

try:
    from dotenv import load_dotenv
    load_dotenv(_ATLAS.parent.parent / "company-brain" / ".env")
except ImportError:
    pass

import db

_MAX_OUTREACH = 3   # LLM calls per run
_DECAY_THRESHOLD = 0.7


def _days_since(date_str: str | None) -> float | None:
    if not date_str:
        return None
    try:
        d = datetime.fromisoformat(date_str[:10]).date()
        return (date.today() - d).days
    except (ValueError, TypeError):
        return None


def detect_decay(days: int = 30) -> list[dict]:
    """
    Compute risk_of_decay for all relationships and return those past their cadence.
    Updates risk_of_decay in DB for every relationship.
    """
    db.init()
    relationships = db.get_relationships(limit=200)
    decaying = []

    for rel in relationships:
        cadence = rel.get("cadence_days") or 30
        days_since = _days_since(rel.get("last_contact"))

        if days_since is None:
            # Never contacted — maximum decay
            risk = 1.0
        else:
            risk = min(1.0, days_since / cadence)

        db.update_relationship_decay(rel["name"], risk)
        rel["risk_of_decay"] = risk
        rel["days_since_contact"] = days_since

        if risk >= 0.5:
            decaying.append(rel)

    decaying.sort(key=lambda r: r["risk_of_decay"], reverse=True)
    return decaying


def generate_outreach(rel: dict) -> str:
    """
    Generate contextual, human-feeling outreach for one relationship.
    References notes and organization. NOT generic. Plain text only.
    """
    try:
        import anthropic
        client = anthropic.Anthropic()

        rel_type = rel.get("type", "contact")
        org = rel.get("organization") or ""
        notes = rel.get("notes") or ""
        days_since = rel.get("days_since_contact")

        time_note = f"{int(days_since)} days ago" if days_since else "a while ago"

        prompt = f"""Draft a brief, personal outreach message from Emod Vafa to {rel['name']}.

Context:
- Relationship type: {rel_type}
- Organization: {org or 'not listed'}
- Notes/history: {notes[:300] or 'no prior notes'}
- Last contacted: {time_note}
- Relationship warmth score: {rel.get('warmth_score', 5)}/10

Requirements:
- 3-5 sentences max
- Feel like a genuine human check-in, NOT a sales pitch
- Reference something specific from the context above (not generic)
- Tone: warm, low-pressure, relationship-oriented
- Sign off as Emod
- Plain text, no HTML, no subject line"""

        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}]
        )
        return resp.content[0].text.strip()
    except Exception as e:
        return f"[Outreach generation failed: {e}]"


def run_pipeline() -> dict:
    """
    Main agent entry point. Returns standard triage dict.
    """
    db.init()
    decaying = detect_decay()
    high_risk = [r for r in decaying if r["risk_of_decay"] >= _DECAY_THRESHOLD]

    exceptions = []
    outreach_drafts = []

    # Generate outreach for top N at highest risk
    for rel in high_risk[:_MAX_OUTREACH]:
        draft = generate_outreach(rel)
        outreach_drafts.append({
            "name": rel["name"],
            "type": rel.get("type"),
            "risk": rel["risk_of_decay"],
            "draft": draft,
        })
        if rel.get("type") in ("client", "family") and rel["risk_of_decay"] >= 0.85:
            exceptions.append(
                f"{rel['name']} ({rel.get('type','contact')}) — "
                f"relationship decay {rel['risk_of_decay']:.0%}, "
                f"last contact {rel.get('days_since_contact','?')} days ago"
            )

    total_decaying = len([r for r in decaying if r["risk_of_decay"] >= _DECAY_THRESHOLD])
    summary = (
        f"Relationship scan: {len(decaying)} contacts tracked. "
        f"{total_decaying} at high decay risk. "
        f"Outreach drafted for {len(outreach_drafts)}: "
        f"{', '.join(d['name'] for d in outreach_drafts) or 'none'}."
    )

    has_escalation = len(exceptions) > 0
    escalation_reason = "; ".join(exceptions) if exceptions else ""

    return {
        "agent_name": "relationship",
        "summary": summary,
        "exceptions": exceptions,
        "has_escalation": has_escalation,
        "escalation_reason": escalation_reason,
        "outreach_drafts": outreach_drafts,
    }


if __name__ == "__main__":
    db.init()
    result = run_pipeline()
    print(f"\n  Relationship Agent\n  {'─'*50}")
    print(f"  {result['summary']}")
    if result["outreach_drafts"]:
        print(f"\n  Outreach Drafts:")
        for d in result["outreach_drafts"]:
            print(f"\n  [{d['name']} — {d['type']} — decay {d['risk']:.0%}]")
            print(f"  {d['draft']}")
