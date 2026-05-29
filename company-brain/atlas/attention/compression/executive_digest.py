"""
executive_digest.py — Morning / Evening / Weekly digest generator.

Max per digest: 3 priorities, 1 warning, 1 decision.
Claude API is called only when there is something notable to surface.

Usage:
  python executive_digest.py morning
  python executive_digest.py evening
  python executive_digest.py weekly
"""
from __future__ import annotations
import json
import sys
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

_HERE = Path(__file__).parent       # atlas/attention/compression/
_ATLAS = _HERE.parent.parent        # atlas/
_CHIEF = _ATLAS.parent / "chief"

sys.path.insert(0, str(_CHIEF))
sys.path.insert(0, str(_ATLAS))

try:
    from dotenv import load_dotenv
    load_dotenv(_ATLAS.parent / ".env")
except ImportError:
    pass

import db

DIGEST_SYSTEM = """You are Atlas — a calm, trustworthy executive assistant.
Deliver the digest as structured facts. No emotional framing. No urgency inflation.
Max 3 priorities. Max 1 warning. Max 1 decision required.
If nothing is urgent: output exactly "All systems nominal."
Never start with a greeting. Never use emojis."""


class DigestType(Enum):
    MORNING = "morning"
    EVENING = "evening"
    WEEKLY  = "weekly"


def _llm_synthesize(digest_type: DigestType, context: str, max_tokens: int) -> str:
    try:
        import anthropic
        client = anthropic.Anthropic()
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=max_tokens,
            system=DIGEST_SYSTEM,
            messages=[{"role": "user", "content": context}],
        )
        return resp.content[0].text.strip()
    except Exception as e:
        return f"Digest unavailable: {e}"


def generate_morning_digest() -> str:
    """Morning brief — decisions + trajectory risks + today's actions."""
    db.init()

    # Escalations
    pending = db.get_pending_escalations(limit=30)
    raw_alerts = [
        {
            "agent_name": e.get("agent_name", "?"),
            "urgency":    e.get("urgency", "NORMAL"),
            "reason":     e.get("escalation_reason", ""),
            "summary":    (e.get("output") or "")[:200],
        }
        for e in pending
    ]

    try:
        from attention.compression.notification_compressor import filter_alerts, cluster_alerts
        alerts = filter_alerts(raw_alerts, max_alerts=5)
        alerts = cluster_alerts(alerts)
    except Exception:
        alerts = raw_alerts[:5]

    # Trajectory critical/high domains
    critical_domains = []
    try:
        states = db.get_all_trajectory_states()
        critical_domains = [
            s for s in states
            if s.get("risk_level") in ("critical", "high")
        ]
    except Exception:
        pass

    # High-priority actions
    high_actions = []
    try:
        high_actions = db.get_actions(status="OPEN", priority="HIGH", limit=5)
    except Exception:
        pass

    # Nothing notable check
    if not alerts and not critical_domains and not high_actions:
        return "All systems nominal."

    context = f"""Morning digest. Date: {datetime.now(timezone.utc).strftime('%Y-%m-%d')}.

PENDING ESCALATIONS ({len(alerts)}):
{json.dumps(alerts, indent=2, default=str)}

TRAJECTORY ALERTS ({len(critical_domains)} domains at elevated risk):
{json.dumps([{"domain": s["domain"], "risk": s["risk_level"], "trend": s["trend_direction"], "score": s["trajectory_score"]} for s in critical_domains], indent=2)}

HIGH-PRIORITY ACTIONS DUE ({len(high_actions)}):
{json.dumps([{"title": a["title"], "due": a.get("deadline"), "contact": a.get("from_name")} for a in high_actions], indent=2)}

Synthesize into a morning digest. Max 3 priorities, 1 warning, 1 decision."""

    return _llm_synthesize(DigestType.MORNING, context, max_tokens=200)


def generate_evening_digest() -> str:
    """Evening summary — what happened, what's pending tomorrow."""
    db.init()

    # What ran today
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    agent_runs_today = []
    try:
        agents = db.get_agents("active")
        for a in agents:
            last_run = (a.get("last_run") or "")[:10]
            if last_run == today:
                agent_runs_today.append({"name": a["name"], "runs": a.get("run_count", 0)})
    except Exception:
        pass

    # Open high-priority actions for tomorrow
    pending_tomorrow = []
    try:
        pending_tomorrow = db.get_actions(status="OPEN", priority="HIGH", limit=3)
    except Exception:
        pass

    if not agent_runs_today and not pending_tomorrow:
        return "Quiet day. No action required."

    context = f"""Evening digest. Date: {today}.

AGENTS THAT RAN TODAY ({len(agent_runs_today)}):
{json.dumps(agent_runs_today, indent=2)}

HIGH-PRIORITY OPEN ACTIONS FOR TOMORROW ({len(pending_tomorrow)}):
{json.dumps([{"title": a["title"], "due": a.get("deadline")} for a in pending_tomorrow], indent=2)}

Summarise what was handled and what needs attention tomorrow. Max 150 tokens."""

    return _llm_synthesize(DigestType.EVENING, context, max_tokens=150)


def generate_weekly_digest() -> str:
    """Weekly overview — trajectory trends, agent performance, top signals."""
    db.init()

    # Trajectory week-over-week
    states = []
    try:
        states = db.get_all_trajectory_states()
    except Exception:
        pass

    # Feedback summary
    feedback_data = {}
    try:
        from feedback import get_feedback_summary
        feedback_data = get_feedback_summary(days=7)
    except Exception:
        pass

    # Revenue snapshot
    monthly_revenue = 0.0
    try:
        streams = db.get_revenue_streams()
        monthly_revenue = sum(s.get("monthly_revenue", 0) for s in streams)
    except Exception:
        pass

    # Pending escalations count
    pending_count = 0
    try:
        pending_count = len(db.get_pending_escalations(limit=100))
    except Exception:
        pass

    context = f"""Weekly digest.

TRAJECTORY — ALL DOMAINS:
{json.dumps([{"domain": s["domain"], "risk": s["risk_level"], "trend": s["trend_direction"], "score": s["trajectory_score"], "confidence": s["confidence_score"]} for s in states], indent=2)}

AGENT PERFORMANCE (last 7 days):
{json.dumps(feedback_data, indent=2)}

BUSINESS SNAPSHOT:
- Monthly revenue: ${monthly_revenue:,.0f}
- Pending escalations: {pending_count}

Produce weekly digest: trajectory week-over-week, top 3 wins, top 1 risk. Max 300 tokens."""

    return _llm_synthesize(DigestType.WEEKLY, context, max_tokens=300)


# ── CLI ────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    db.init()
    args = sys.argv[1:]
    cmd = args[0] if args else "morning"

    if cmd == "morning":
        result = generate_morning_digest()
        print(f"\n  Morning Digest — {datetime.now().strftime('%Y-%m-%d %H:%M')}\n  {'─'*54}")
        print(result)

    elif cmd == "evening":
        result = generate_evening_digest()
        print(f"\n  Evening Digest — {datetime.now().strftime('%Y-%m-%d %H:%M')}\n  {'─'*54}")
        print(result)

    elif cmd == "weekly":
        result = generate_weekly_digest()
        print(f"\n  Weekly Digest — {datetime.now().strftime('%Y-%m-%d')}\n  {'─'*54}")
        print(result)

    else:
        print("Usage: executive_digest.py [morning | evening | weekly]")
