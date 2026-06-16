"""
global_optimizer.py — Atlas Global Decision Engine.

Uses priority scores + feedback to make system-level decisions:
promote high-value agents (increase frequency), suppress low-value ones
(decrease frequency), and flag kill candidates for human review.

Rules:
  PROMOTE:  signal_score > 0.7 AND approval_rate > 0.8 AND total_actions >= 5
  SUPPRESS: approval_rate < 0.35 AND total_actions >= 5
            OR priority score < 4.0
  KILL:     approval_rate < 0.2 AND total_actions >= 10 AND signal_score < -0.5

Never auto-kills. Kill candidates are listed only — human must approve via
'atlas factory kill <name>'.

Usage:
  python global_optimizer.py plan     Show optimization plan (no changes)
  python global_optimizer.py apply    Apply the plan (adjusts frequencies)
  python global_optimizer.py explain  English system state summary
"""
import sys
from datetime import datetime, timezone
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
from priority import score_all_agents, get_system_allocation
from feedback import get_agent_performance, get_feedback_summary

# ── Frequency ladder ──────────────────────────────────────────────────────────
_LADDER = ["monthly", "weekly", "daily"]


def _promote_frequency(current: str) -> str | None:
    """Step frequency up the ladder. Returns None if already at top or triggered."""
    if current not in _LADDER:
        return None  # triggered or unknown
    idx = _LADDER.index(current)
    if idx >= len(_LADDER) - 1:
        return None  # already daily
    return _LADDER[idx + 1]


def _suppress_frequency(current: str) -> str | None:
    """Step frequency down the ladder. Returns None if already at bottom or triggered."""
    if current not in _LADDER:
        return None
    idx = _LADDER.index(current)
    if idx <= 0:
        return None  # already monthly
    return _LADDER[idx - 1]


# ── Core functions ────────────────────────────────────────────────────────────

def compute_optimization_plan(dry_run: bool = False) -> dict:
    """
    Analyze roster + feedback + priority scores.
    dry_run=True: same output, never writes to DB (apply_optimization_plan does writing).
    Returns {promote, suppress, kill, no_change, summary}.
    """
    db.init()
    agents = db.get_agents("active")
    scored_map = {a["name"]: ps for a, ps in score_all_agents()}

    promote = []
    suppress = []
    kill = []
    no_change = []

    for agent in agents:
        name = agent["name"]
        freq = (agent.get("frequency") or "weekly").lower()
        ps = scored_map.get(name)
        perf = get_agent_performance(name, days=30)

        total_actions = perf["total_actions"]
        approval_rate = perf["approval_rate"]
        signal_score = perf["signal_score"]

        # Kill check (human-approve-only)
        if total_actions >= 10 and approval_rate < 0.2 and signal_score < -0.5:
            kill.append((
                name,
                f"Chronic under-performance: {approval_rate:.0%} approval, "
                f"signal {signal_score:+.2f}, {total_actions} actions",
            ))
            continue

        # Suppress check
        suppress_reason = None
        if total_actions >= 5 and approval_rate < 0.35:
            suppress_reason = f"Low approval rate ({approval_rate:.0%} over {total_actions} actions)"
        elif ps and ps.total < 4.0:
            suppress_reason = f"Low priority score ({ps.total:.1f})"

        if suppress_reason and freq != "triggered":
            new_freq = _suppress_frequency(freq)
            if new_freq:
                suppress.append((name, suppress_reason, new_freq))
                continue
            # already at minimum — fall through to no_change

        # Promote check
        if total_actions >= 5 and approval_rate > 0.8 and signal_score > 0.7:
            new_freq = _promote_frequency(freq)
            if new_freq:
                promote.append((
                    name,
                    f"High performance: {approval_rate:.0%} approval, signal {signal_score:+.2f}",
                    new_freq,
                ))
                continue

        no_change.append(name)

    # Build summary
    lines = []
    if not promote and not suppress and not kill:
        lines.append("System is stable. No frequency adjustments recommended.")
    else:
        if promote:
            lines.append(f"{len(promote)} agent(s) ready to promote: {', '.join(n for n,*_ in promote)}.")
        if suppress:
            lines.append(f"{len(suppress)} agent(s) recommended for frequency reduction: {', '.join(n for n,*_ in suppress)}.")
        if kill:
            lines.append(f"{len(kill)} agent(s) flagged for human kill-review: {', '.join(n for n,_ in kill)}.")
    lines.append(f"{len(no_change)} agent(s) unchanged.")

    return {
        "promote":   promote,
        "suppress":  suppress,
        "kill":      kill,
        "no_change": no_change,
        "summary":   " ".join(lines),
        "dry_run":   dry_run,
    }


def apply_optimization_plan(plan: dict) -> dict:
    """
    Apply the optimization plan — adjusts agent frequencies in DB.
    Never kills agents. Kill candidates are recommendations only.
    """
    db.init()
    applied = []
    skipped = []

    for name, reason, new_freq in plan.get("promote", []):
        agent = db.get_agent(name)
        if not agent:
            skipped.append(f"{name}: not found in DB")
            continue
        db.update_agent_frequency(name, new_freq)
        applied.append(f"PROMOTE {name}: {agent.get('frequency','?')} → {new_freq} ({reason})")

    for name, reason, new_freq in plan.get("suppress", []):
        agent = db.get_agent(name)
        if not agent:
            skipped.append(f"{name}: not found in DB")
            continue
        db.update_agent_frequency(name, new_freq)
        applied.append(f"SUPPRESS {name}: {agent.get('frequency','?')} → {new_freq} ({reason})")

    for name, reason in plan.get("kill", []):
        skipped.append(f"KILL {name}: recommendation only — run 'atlas factory kill {name}' to confirm")

    return {"applied": applied, "skipped": skipped}


def explain_system_state() -> str:
    """
    One-paragraph English summary of current system state.
    String-built from DB data — no LLM API call.
    """
    db.init()
    agents = db.get_agents("active")
    scored = score_all_agents()
    scored_map = {a["name"]: ps for a, ps in scored}
    alloc = get_system_allocation()
    feedback = get_feedback_summary(days=7)

    n_agents = len(agents)
    n_run_now = len(alloc["run_now"])
    n_suppress = len(alloc["suppress"])

    parts = [f"Atlas is running {n_agents} active agents."]

    # Top agents
    high_agents = [a["name"] for a, ps in scored[:2] if ps.tier in ("CRITICAL", "HIGH")]
    if high_agents:
        parts.append(f"Highest-priority: {', '.join(high_agents)}.")

    # Run-now
    if n_run_now:
        parts.append(f"{n_run_now} agent(s) are overdue and ready to run: {', '.join(alloc['run_now'])}.")

    # Feedback signals
    over = feedback.get("over_triggering", [])
    if over:
        agent_names = [a["agent"] for a in over]
        parts.append(f"Over-triggering detected: {', '.join(agent_names)} (high rejection rate).")

    best = feedback.get("best_agents", [])
    if best:
        parts.append(f"Best performing: {best[0]['agent']} ({best[0]['approval_rate']:.0%} approval).")

    # Suppress
    if n_suppress:
        parts.append(f"{n_suppress} agent(s) suppressed (low score or over-triggering): {', '.join(alloc['suppress'])}.")

    if len(parts) == 1:
        parts.append("All agents within normal operating parameters.")

    return " ".join(parts)


# ── CLI ───────────────────────────────────────────────────────────────────────

def print_plan(plan: dict):
    print(f"\n  Atlas Optimization Plan\n  {'─'*56}")
    print(f"  {plan['summary']}\n")
    if plan["promote"]:
        print(f"  ↑ PROMOTE ({len(plan['promote'])}):")
        for name, reason, new_freq in plan["promote"]:
            print(f"    {name}: → {new_freq}  ({reason})")
    if plan["suppress"]:
        print(f"\n  ↓ SUPPRESS ({len(plan['suppress'])}):")
        for name, reason, new_freq in plan["suppress"]:
            print(f"    {name}: → {new_freq}  ({reason})")
    if plan["kill"]:
        print(f"\n  ✕ KILL CANDIDATES (human review required):")
        for name, reason in plan["kill"]:
            print(f"    {name}: {reason}")
            print(f"    → Run: atlas factory kill {name}")
    if plan["no_change"]:
        print(f"\n  ✓ No change: {', '.join(plan['no_change'])}")


if __name__ == "__main__":
    db.init()
    args = sys.argv[1:]
    cmd = args[0] if args else "plan"

    if cmd == "plan":
        plan = compute_optimization_plan(dry_run=True)
        print_plan(plan)

    elif cmd == "apply":
        plan = compute_optimization_plan()
        print_plan(plan)
        if plan["promote"] or plan["suppress"]:
            confirm = input("\n  Apply these changes? (yes/no): ").strip().lower()
            if confirm == "yes":
                result = apply_optimization_plan(plan)
                for line in result["applied"]:
                    print(f"  ✓ {line}")
                for line in result["skipped"]:
                    print(f"  · {line}")
            else:
                print("  Cancelled.")
        else:
            print("  Nothing to apply.")

    elif cmd == "explain":
        print(f"\n  {explain_system_state()}")

    else:
        print("Usage: global_optimizer.py [plan | apply | explain]")
