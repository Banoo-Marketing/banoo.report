"""
priority.py — Atlas Priority Kernel.

Scores every agent on 5 axes: revenue impact, time leverage, risk reduction,
strategic value, urgency. Produces a total weighted score and tier that drives
execution order and resource allocation.

Usage:
  python priority.py              Show all agents ranked by score
  python priority.py <name>       Score details for one agent
"""
from __future__ import annotations
import sys
from dataclasses import dataclass
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

# ── Tunable weights ───────────────────────────────────────────────────────────

WEIGHTS = {
    "revenue":    0.30,
    "time":       0.20,
    "risk":       0.25,
    "strategic":  0.15,
    "urgency":    0.10,
}

# ── Agent baseline scores (business knowledge, not DB-driven) ─────────────────
# Keys match agent.name exactly. Unknown agents get DEFAULT_BASELINE.

_AGENT_BASELINES: dict[str, dict[str, float]] = {
    "relay":  {"revenue": 8.0, "time": 7.0, "risk": 3.0, "strategic": 6.0},
    "pulse":  {"revenue": 9.0, "time": 6.0, "risk": 7.0, "strategic": 8.0},
    "ledger": {"revenue": 8.0, "time": 5.0, "risk": 9.0, "strategic": 7.0},
    "broker": {"revenue": 6.0, "time": 4.0, "risk": 8.0, "strategic": 7.0},
    "scout":  {"revenue": 7.0, "time": 5.0, "risk": 3.0, "strategic": 9.0},
}

_DEFAULT_BASELINE: dict[str, float] = {"revenue": 5.0, "time": 5.0, "risk": 5.0, "strategic": 5.0}

# ── Frequency thresholds (mirror of scheduler.py — keep in sync) ──────────────
_FREQUENCY_THRESHOLDS: dict[str, timedelta] = {
    "daily":   timedelta(hours=20),
    "weekly":  timedelta(days=6),
    "monthly": timedelta(days=28),
}


@dataclass
class PriorityScore:
    revenue_score:   float
    time_leverage:   float
    risk_reduction:  float
    strategic_value: float
    urgency:         float
    total:           float   # weighted composite, clamped 0–10
    tier:            str     # CRITICAL | HIGH | MEDIUM | LOW
    rationale:       str     # 1-line explanation


# ── Internal helpers ──────────────────────────────────────────────────────────

def _parse_last_run(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s).replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None


def _is_overdue(agent: dict) -> bool:
    freq = (agent.get("frequency") or "weekly").lower()
    if freq == "triggered":
        return False
    threshold = _FREQUENCY_THRESHOLDS.get(freq)
    if threshold is None:
        return False
    last_run = _parse_last_run(agent.get("last_run"))
    if last_run is None:
        return True  # never run
    return datetime.now(timezone.utc) - last_run >= threshold


def _hours_until_due(agent: dict) -> float:
    """Return hours until agent is due (negative = already overdue)."""
    freq = (agent.get("frequency") or "weekly").lower()
    if freq == "triggered":
        return float("inf")
    threshold = _FREQUENCY_THRESHOLDS.get(freq)
    if threshold is None:
        return float("inf")
    last_run = _parse_last_run(agent.get("last_run"))
    if last_run is None:
        return -float("inf")  # never run → maximally overdue
    next_due = last_run + threshold
    delta = next_due - datetime.now(timezone.utc)
    return delta.total_seconds() / 3600.0


def _compute_urgency(agent: dict) -> float:
    if _is_overdue(agent):
        return 10.0
    freq = (agent.get("frequency") or "weekly").lower()
    if freq == "triggered":
        return 0.0
    threshold = _FREQUENCY_THRESHOLDS.get(freq)
    if threshold is None:
        return 0.0
    threshold_hours = threshold.total_seconds() / 3600.0
    hours_left = _hours_until_due(agent)
    if hours_left <= 0:
        return 10.0
    urgency = 10.0 * (1.0 - hours_left / threshold_hours)
    return max(0.0, min(10.0, urgency))


def _feedback_modifier(agent_name: str) -> float:
    """Return a delta to add to the raw total score based on feedback history."""
    try:
        from feedback import get_agent_performance
        perf = get_agent_performance(agent_name, days=30)
        if perf["total_actions"] < 3:
            return 0.0  # insufficient data
        approval_rate = perf["approval_rate"]
        signal_score = perf["signal_score"]
        delta = 0.0
        if approval_rate < 0.3:
            delta -= 2.0
        elif approval_rate > 0.8:
            delta += 0.5
        if signal_score < -0.3:
            delta -= 1.0
        return delta
    except Exception:
        return 0.0


def _tier(total: float) -> str:
    if total >= 8.0:
        return "CRITICAL"
    if total >= 6.0:
        return "HIGH"
    if total >= 4.0:
        return "MEDIUM"
    return "LOW"


# ── Public API ────────────────────────────────────────────────────────────────

def score_agent(agent: dict) -> PriorityScore:
    """Compute full PriorityScore for a single agent dict."""
    name = agent.get("name", "")
    baseline = _AGENT_BASELINES.get(name, _DEFAULT_BASELINE)

    revenue  = baseline["revenue"]
    time_lev = baseline["time"]
    risk     = baseline["risk"]
    strat    = baseline["strategic"]
    urgency  = _compute_urgency(agent)

    raw_total = (
        revenue  * WEIGHTS["revenue"] +
        time_lev * WEIGHTS["time"] +
        risk     * WEIGHTS["risk"] +
        strat    * WEIGHTS["strategic"] +
        urgency  * WEIGHTS["urgency"]
    )

    modifier = _feedback_modifier(name)
    total = max(0.0, min(10.0, raw_total + modifier))
    tier = _tier(total)

    # Build rationale
    overdue = _is_overdue(agent)
    freq = agent.get("frequency", "?")
    parts = []
    if tier == "CRITICAL":
        parts.append("top priority")
    if overdue:
        parts.append("overdue")
    if risk >= 8.0:
        parts.append("high risk coverage")
    if revenue >= 8.0:
        parts.append("direct revenue")
    if modifier < -1.0:
        parts.append("penalised for over-triggering")
    rationale = f"{tier} — {', '.join(parts) or freq}"

    return PriorityScore(
        revenue_score=revenue,
        time_leverage=time_lev,
        risk_reduction=risk,
        strategic_value=strat,
        urgency=urgency,
        total=round(total, 2),
        tier=tier,
        rationale=rationale,
    )


def score_all_agents() -> list[tuple[dict, PriorityScore]]:
    """Load all active agents, score each, return sorted by total DESC."""
    db.init()
    agents = db.get_agents("active")
    scored = [(a, score_agent(a)) for a in agents]
    scored.sort(key=lambda x: x[1].total, reverse=True)
    return scored


def get_execution_order() -> list[str]:
    """Return all active agent names sorted by priority score (highest first)."""
    return [a["name"] for a, _ in score_all_agents()]


def get_system_allocation() -> dict:
    """
    Categorize agents into execution buckets.

    run_now:   CRITICAL tier OR overdue
    run_today: HIGH tier, due within 24h
    defer:     MEDIUM/LOW, not urgent
    suppress:  score < 3.0 OR approval_rate < 0.3 (with ≥3 actions)
    """
    db.init()
    scored = score_all_agents()

    run_now = []
    run_today = []
    defer = []
    suppress = []

    for agent, ps in scored:
        name = agent["name"]

        # Check suppress condition (feedback-driven)
        try:
            from feedback import get_agent_performance
            perf = get_agent_performance(name, days=30)
            if perf["total_actions"] >= 3 and perf["approval_rate"] < 0.3:
                suppress.append(name)
                continue
        except Exception:
            pass

        if ps.total < 3.0:
            suppress.append(name)
        elif _is_overdue(agent) or ps.tier == "CRITICAL":
            run_now.append(name)
        elif ps.tier == "HIGH" and _hours_until_due(agent) <= 24.0:
            run_today.append(name)
        else:
            defer.append(name)

    return {
        "run_now":   run_now,
        "run_today": run_today,
        "defer":     defer,
        "suppress":  suppress,
    }


def _print_ranked_table():
    scored = score_all_agents()
    print(f"\n  Atlas Priority Kernel — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC")
    print(f"  {'─'*72}")
    print(f"  {'RANK':<5} {'AGENT':<10} {'TIER':<10} {'TOTAL':>5}  {'REV':>4} {'TIME':>4} {'RISK':>4} {'STRAT':>5} {'URG':>4}  RATIONALE")
    print(f"  {'─'*72}")
    for i, (agent, ps) in enumerate(scored, 1):
        tier_icon = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "⚪"}.get(ps.tier, "?")
        print(
            f"  {i:<5} {agent['name']:<10} {tier_icon}{ps.tier:<9} {ps.total:>5.1f}"
            f"  {ps.revenue_score:>4.1f} {ps.time_leverage:>4.1f} {ps.risk_reduction:>4.1f}"
            f" {ps.strategic_value:>5.1f} {ps.urgency:>4.1f}  {ps.rationale}"
        )


if __name__ == "__main__":
    db.init()
    args = sys.argv[1:]
    if args:
        agent_row = db.get_agent(args[0])
        if not agent_row:
            print(f"  Agent '{args[0]}' not found.")
        else:
            ps = score_agent(agent_row)
            print(f"\n  Priority Score: {agent_row['name']}")
            print(f"  {'─'*40}")
            print(f"  Revenue score  : {ps.revenue_score}")
            print(f"  Time leverage  : {ps.time_leverage}")
            print(f"  Risk reduction : {ps.risk_reduction}")
            print(f"  Strategic value: {ps.strategic_value}")
            print(f"  Urgency        : {ps.urgency}")
            print(f"  Total          : {ps.total}  [{ps.tier}]")
            print(f"  Rationale      : {ps.rationale}")
    else:
        _print_ranked_table()
