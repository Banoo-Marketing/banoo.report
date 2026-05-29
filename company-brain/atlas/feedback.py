"""
feedback.py — Atlas Feedback Loop.

After any action is executed, rejected, or failed: logs the outcome into
feedback_log so Atlas can track which agents are performing well and which
are over- or under-triggering.

Signal classification:
  executed                              → positive
  rejected + reason contains 'personal' → neutral (right idea, needs polish)
  rejected + no reason                  → negative (agent over-triggered)
  failed                                → negative

Usage:
  python feedback.py status            System-wide performance (last 7 days)
  python feedback.py agent <name>      Breakdown for one agent
  python feedback.py tune              Tuning recommendations
"""
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

_HERE = Path(__file__).parent
_CHIEF = _HERE.parent / "chief"

sys.path.insert(0, str(_CHIEF))
sys.path.insert(0, str(_HERE))

try:
    from dotenv import load_dotenv
    load_dotenv(_HERE.parent.parent / "company-brain" / ".env")
    load_dotenv(_HERE / ".env")
except ImportError:
    pass

import db


def _classify_signal(outcome: str, rejection_reason: str | None) -> str:
    if outcome == "executed":
        return "positive"
    if outcome == "rejected":
        reason = (rejection_reason or "").lower()
        if "personal" in reason or "personalise" in reason or "polish" in reason:
            return "neutral"
        return "negative"
    if outcome == "failed":
        return "negative"
    return "neutral"


def log_feedback(
    action_id: int,
    outcome: str,
    rejection_reason: str | None = None,
    result: str | None = None,
) -> int:
    """
    Insert a feedback row for an action. Safe to call from executor — never raises.

    outcome: executed | rejected | failed
    Returns new feedback_log row id, or -1 on error.
    """
    try:
        db.init()
        action = db.get_queued_action(action_id)
        if not action:
            return -1

        signal = _classify_signal(outcome, rejection_reason)
        return db.insert_feedback({
            "action_id": action_id,
            "action_type": action.get("action_type", ""),
            "source_agent": action.get("source_agent", ""),
            "outcome": outcome,
            "rejection_reason": rejection_reason or "",
            "execution_result": (result or "")[:500],
            "permission_level": action.get("permission_level", 2),
            "signal": signal,
        })
    except Exception:
        return -1


def get_agent_performance(agent_name: str, days: int = 30) -> dict:
    """
    Return performance metrics for a single agent over the last N days.

    {total_actions, executed, rejected, failed,
     approval_rate: float, signal_score: float (-1 to +1)}
    """
    rows = db.get_feedback_for_agent(agent_name, days=days)

    total = len(rows)
    if total == 0:
        return {
            "agent_name": agent_name,
            "total_actions": 0,
            "executed": 0,
            "rejected": 0,
            "failed": 0,
            "approval_rate": 0.0,
            "signal_score": 0.0,
        }

    executed = sum(1 for r in rows if r["outcome"] == "executed")
    rejected = sum(1 for r in rows if r["outcome"] == "rejected")
    failed = sum(1 for r in rows if r["outcome"] == "failed")

    positive = sum(1 for r in rows if r["signal"] == "positive")
    negative = sum(1 for r in rows if r["signal"] == "negative")
    # neutral counts as 0

    approval_rate = executed / total
    signal_score = (positive - negative) / total  # -1 to +1

    return {
        "agent_name": agent_name,
        "total_actions": total,
        "executed": executed,
        "rejected": rejected,
        "failed": failed,
        "approval_rate": round(approval_rate, 3),
        "signal_score": round(signal_score, 3),
    }


def get_feedback_summary(days: int = 7) -> dict:
    """
    System-wide feedback summary.

    Returns {total, by_outcome, best_agents, worst_agents, over_triggering, under_triggering}
    """
    rows = db.get_all_feedback(days=days)
    if not rows:
        return {"total": 0, "by_outcome": {}, "best_agents": [], "worst_agents": [], "over_triggering": [], "under_triggering": []}

    total = len(rows)
    by_outcome: dict[str, int] = {}
    by_agent: dict[str, list] = {}

    for r in rows:
        outcome = r.get("outcome", "unknown")
        by_outcome[outcome] = by_outcome.get(outcome, 0) + 1
        agent = r.get("source_agent") or "unknown"
        by_agent.setdefault(agent, []).append(r)

    agent_scores = []
    for agent, agent_rows in by_agent.items():
        n = len(agent_rows)
        executed = sum(1 for x in agent_rows if x["outcome"] == "executed")
        rejected = sum(1 for x in agent_rows if x["outcome"] == "rejected")
        positive = sum(1 for x in agent_rows if x["signal"] == "positive")
        negative = sum(1 for x in agent_rows if x["signal"] == "negative")
        approval_rate = executed / n
        signal_score = (positive - negative) / n
        agent_scores.append({
            "agent": agent,
            "total": n,
            "executed": executed,
            "rejected": rejected,
            "approval_rate": round(approval_rate, 3),
            "signal_score": round(signal_score, 3),
        })

    agent_scores.sort(key=lambda x: x["signal_score"], reverse=True)
    best_agents = [a for a in agent_scores if a["signal_score"] >= 0.5][:3]
    worst_agents = [a for a in reversed(agent_scores) if a["signal_score"] < 0][:3]
    over_triggering = [a for a in agent_scores if a["approval_rate"] < 0.4 and a["total"] >= 3]
    under_triggering = [a for a in agent_scores if a["total"] < 2 and a["approval_rate"] > 0.8]

    return {
        "total": total,
        "days": days,
        "by_outcome": by_outcome,
        "best_agents": best_agents,
        "worst_agents": worst_agents,
        "over_triggering": over_triggering,
        "under_triggering": under_triggering,
    }


def should_tune_agent(agent_name: str) -> str | None:
    """
    Return a tuning recommendation string if agent needs improvement, else None.
    """
    perf = get_agent_performance(agent_name, days=30)
    total = perf["total_actions"]
    if total < 3:
        return None  # not enough data

    approval_rate = perf["approval_rate"]
    signal_score = perf["signal_score"]

    if approval_rate < 0.3:
        return (
            f"{agent_name}: HIGH rejection rate ({perf['rejected']}/{total} rejected). "
            "Agent is over-triggering — tighten escalation_rules or raise permission threshold."
        )
    if approval_rate < 0.5:
        return (
            f"{agent_name}: Low approval rate ({approval_rate:.0%}). "
            "Review recent rejections and refine agent prompt to reduce false positives."
        )
    if signal_score < -0.3:
        return (
            f"{agent_name}: Negative signal score ({signal_score:+.2f}). "
            "High failure or rejection rate — review recent outputs and adjust scope."
        )
    return None


def _print_summary(days: int = 7):
    summary = get_feedback_summary(days=days)
    total = summary["total"]
    print(f"\n  Atlas Feedback — Last {days} days\n  {'─'*56}")
    if total == 0:
        print("  No feedback recorded yet. Actions logged after execution appear here.")
        return

    print(f"  Total actions : {total}")
    for outcome, n in sorted(summary["by_outcome"].items()):
        icon = {"executed": "✓", "rejected": "✗", "failed": "!"}.get(outcome, "·")
        print(f"  {icon} {outcome:<12}: {n}")

    if summary["best_agents"]:
        print(f"\n  Best performing agents:")
        for a in summary["best_agents"]:
            print(f"    ↑ {a['agent']:<12} approval={a['approval_rate']:.0%}  score={a['signal_score']:+.2f}  ({a['total']} actions)")

    if summary["worst_agents"]:
        print(f"\n  Needs attention:")
        for a in summary["worst_agents"]:
            print(f"    ↓ {a['agent']:<12} approval={a['approval_rate']:.0%}  score={a['signal_score']:+.2f}  ({a['total']} actions)")

    if summary["over_triggering"]:
        print(f"\n  Over-triggering (high rejection):")
        for a in summary["over_triggering"]:
            print(f"    ⚠ {a['agent']}: {a['rejected']}/{a['total']} rejected")


def _print_agent(agent_name: str):
    perf = get_agent_performance(agent_name, days=30)
    print(f"\n  Agent: {agent_name} (last 30 days)\n  {'─'*44}")
    if perf["total_actions"] == 0:
        print("  No actions recorded for this agent.")
        return
    print(f"  Total actions : {perf['total_actions']}")
    print(f"  Executed      : {perf['executed']}")
    print(f"  Rejected      : {perf['rejected']}")
    print(f"  Failed        : {perf['failed']}")
    print(f"  Approval rate : {perf['approval_rate']:.0%}")
    print(f"  Signal score  : {perf['signal_score']:+.2f}  (−1=all bad, +1=all good)")
    rec = should_tune_agent(agent_name)
    if rec:
        print(f"\n  ⚠ Recommendation: {rec}")
    else:
        print(f"\n  ✓ Agent performing well — no tuning needed.")


def _print_tune():
    db.init()
    agents = db.get_agents("active")
    printed = 0
    print(f"\n  Agent Tuning Recommendations\n  {'─'*50}")
    for a in agents:
        rec = should_tune_agent(a["name"])
        if rec:
            print(f"\n  ⚠ {rec}")
            printed += 1
    if printed == 0:
        print("  All agents performing well. No tuning recommendations.")


if __name__ == "__main__":
    db.init()
    args = sys.argv[1:]
    cmd = args[0] if args else "status"

    if cmd == "status":
        days = int(args[1]) if len(args) > 1 else 7
        _print_summary(days=days)

    elif cmd == "agent":
        if len(args) < 2:
            print("Usage: feedback.py agent <name>")
        else:
            _print_agent(args[1])

    elif cmd == "tune":
        _print_tune()

    else:
        print("Usage: feedback.py [status [days] | agent <name> | tune]")
