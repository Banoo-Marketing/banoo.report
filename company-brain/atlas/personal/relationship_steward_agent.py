"""
relationship_steward_agent.py — Marriage and emotional bandwidth guardian.

Protects the Emod-Sahar relationship by monitoring workload patterns
and suggesting recovery windows. Subtle, non-invasive, emotionally intelligent.

NEVER creates email_send or email_draft actions.
Only NOTIFY or TASK_CREATE (Emod's own task list).
"""
from __future__ import annotations
import datetime as _dt
import sys
from datetime import date, datetime
from pathlib import Path

_HERE = Path(__file__).parent
_ATLAS = _HERE.parent
_CHIEF = _ATLAS.parent / "chief"

sys.path.insert(0, str(_CHIEF))
sys.path.insert(0, str(_ATLAS))

try:
    from dotenv import load_dotenv
    load_dotenv(_ATLAS.parent.parent / "company-brain" / ".env")
except ImportError:
    pass

import db


def _days_since_date_night() -> int | None:
    """Return days since last logged date night, or None if never logged."""
    ctx = db.get_strategic_context()
    last = ctx.get("last_date_night")
    if not last:
        return None
    try:
        d = datetime.fromisoformat(last[:10]).date()
        return (date.today() - d).days
    except (ValueError, TypeError):
        return None


def assess_marriage_health() -> dict:
    """
    Assess marriage health from attention log and strategic context.
    Returns risk_level: low | medium | high and a suggestion.
    """
    log = db.get_attention_log(days=7)
    overload_days = sum(1 for entry in log if entry.get("overload_flag"))
    avg_deep_work = sum(e.get("deep_work_hrs", 0) for e in log) / max(len(log), 1)

    days_since_date = _days_since_date_night()

    # Risk scoring
    risk_score = 0
    if overload_days >= 4:
        risk_score += 2
    elif overload_days >= 2:
        risk_score += 1

    if days_since_date is None or days_since_date > 21:
        risk_score += 2
    elif days_since_date > 14:
        risk_score += 1

    if avg_deep_work < 1.5 and len(log) > 0:
        risk_score += 1  # fragmented days = less capacity for relationship

    if risk_score >= 4:
        risk_level = "high"
        suggestion = (
            "Multiple high-overload days and no recent date night. "
            "Protect this weekend — plan something simple with Sahar. "
            "Even 2 hours without phones resets a lot."
        )
    elif risk_score >= 2:
        risk_level = "medium"
        suggestion = (
            f"It's been {days_since_date or '21+'} days since a date night. "
            "Consider a low-key evening this week — dinner or a walk. "
            "Sahar carries a lot with the twins right now."
        )
    else:
        risk_level = "low"
        suggestion = "Relationship bandwidth looks healthy this week. Keep it up."

    last_date_val = None
    if days_since_date is not None:
        last_date_val = str(date.today() - _dt.timedelta(days=days_since_date))

    return {
        "last_date_night": last_date_val,
        "overload_days_7d": overload_days,
        "days_since_date_night": days_since_date,
        "risk_level": risk_level,
        "suggestion": suggestion,
    }


def run_pipeline() -> dict:
    """Weekly check on marriage + emotional bandwidth health."""
    db.init()
    health = assess_marriage_health()
    risk = health["risk_level"]

    has_escalation = risk == "high"
    escalation_reason = health["suggestion"] if has_escalation else ""

    summary = (
        f"Relationship steward: {risk.upper()} risk. "
        f"Overload days this week: {health['overload_days_7d']}. "
        f"Days since date night: {health.get('days_since_date_night') or 'unknown'}. "
        f"{health['suggestion']}"
    )

    return {
        "agent_name": "relationship_steward",
        "summary": summary,
        "exceptions": [health["suggestion"]] if risk in ("medium", "high") else [],
        "has_escalation": has_escalation,
        "escalation_reason": escalation_reason,
        "health": health,
    }


if __name__ == "__main__":
    db.init()
    result = run_pipeline()
    print(f"\n  Relationship Steward\n  {'─'*48}")
    h = result["health"]
    icon = {"low": "OK", "medium": "WARN", "high": "HIGH"}.get(h["risk_level"], "?")
    print(f"  [{icon}] Risk level      : {h['risk_level'].upper()}")
    print(f"  Overload days   : {h['overload_days_7d']}/7")
    print(f"  Days since date : {h.get('days_since_date_night') or 'unknown'}")
    print(f"\n  {h['suggestion']}")
