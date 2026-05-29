"""
attention_engine.py — Cognitive bandwidth protector.

Tracks daily interruption patterns, computes focus score,
and advises when to suppress low-value alerts.

Usage:
  python attention_engine.py status
  python attention_engine.py log [--hours N] [--switches N] [--interruptions N]
"""
from __future__ import annotations
import sys
from datetime import date
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

_OVERLOAD_INTERRUPTION_THRESHOLD = 8   # interruptions/day
_OVERLOAD_SWITCH_THRESHOLD = 10        # task switches/day
_HIGH_FOCUS_MIN_HOURS = 3.0            # deep work hours = good day


def log_daily_attention(
    interruptions: int = 0,
    task_switches: int = 0,
    deep_work_hrs: float = 0,
    agent_alerts: int = 0,
    notes: str = "",
):
    """Log today's attention metrics. Overwrites today's entry if it exists."""
    db.init()
    overload = (
        interruptions >= _OVERLOAD_INTERRUPTION_THRESHOLD or
        task_switches >= _OVERLOAD_SWITCH_THRESHOLD
    )
    db.log_attention({
        "date": str(date.today()),
        "interruptions": interruptions,
        "task_switches": task_switches,
        "deep_work_hrs": deep_work_hrs,
        "agent_alerts": agent_alerts,
        "overload_flag": overload,
        "notes": notes,
    })


def get_focus_score(days: int = 7) -> float:
    """
    0-10 score: 10 = full focus, 0 = total fragmentation.
    Formula: weighted by deep_work_hrs and penalised by overload_flag and switches.
    """
    db.init()
    log = db.get_attention_log(days=days)
    if not log:
        return 5.0  # neutral default when no data

    n = len(log)
    avg_deep = sum(e.get("deep_work_hrs", 0) for e in log) / n
    avg_switches = sum(e.get("task_switches", 0) for e in log) / n
    overload_days = sum(1 for e in log if e.get("overload_flag"))

    # Base score from deep work (max 4 hrs = score 10)
    focus_base = min(10.0, (avg_deep / 4.0) * 10.0)
    # Penalty from switches (10+ switches/day = -3 penalty)
    switch_penalty = min(3.0, avg_switches / 10.0 * 3.0)
    # Penalty from overload days
    overload_penalty = (overload_days / n) * 3.0

    score = focus_base - switch_penalty - overload_penalty
    return round(max(0.0, min(10.0, score)), 1)


def is_overloaded(days: int = 3) -> bool:
    """True if majority of recent days had overload_flag set."""
    db.init()
    log = db.get_attention_log(days=days)
    if not log:
        return False
    overload_count = sum(1 for e in log if e.get("overload_flag"))
    return overload_count >= max(1, len(log) // 2)


def get_recommendation() -> str:
    """One-line focus recommendation based on recent patterns."""
    score = get_focus_score(days=7)
    overloaded = is_overloaded(days=3)

    if overloaded or score < 3.0:
        return "HIGH FRAGMENTATION — block 3h deep work tomorrow morning, disable non-critical notifications."
    elif score < 5.0:
        return "Moderate fragmentation — cluster agent alerts to 2x/day, protect morning hours."
    elif score < 7.0:
        return "Reasonable focus — maintain current rhythm, watch for context-switch creep."
    else:
        return "Strong focus week — protect this pattern."


def should_suppress_alerts() -> bool:
    """True if system should hold non-critical notifications (user is in focus mode)."""
    return is_overloaded(days=1)


def _print_status():
    db.init()
    score = get_focus_score()
    overloaded = is_overloaded()
    rec = get_recommendation()
    log = db.get_attention_log(days=7)

    print(f"\n  Atlas Attention Engine — {date.today()}\n  {'─'*52}")
    print(f"  Focus score (7d) : {score:.1f}/10")
    print(f"  Overload now     : {'YES' if overloaded else 'no'}")
    print(f"  Days logged      : {len(log)}")
    if log:
        avg_deep = sum(e.get("deep_work_hrs", 0) for e in log) / len(log)
        avg_sw = sum(e.get("task_switches", 0) for e in log) / len(log)
        print(f"  Avg deep work    : {avg_deep:.1f}h/day")
        print(f"  Avg task switches: {avg_sw:.0f}/day")
    print(f"\n  Recommendation: {rec}")


if __name__ == "__main__":
    db.init()
    args = sys.argv[1:]
    cmd = args[0] if args else "status"

    if cmd == "status":
        _print_status()

    elif cmd == "log":
        hours = 0.0
        switches = 0
        interruptions = 0
        for i, a in enumerate(args[1:], 1):
            if a == "--hours" and i < len(args):
                try:
                    hours = float(args[i])
                except (ValueError, IndexError):
                    pass
            elif a == "--switches" and i < len(args):
                try:
                    switches = int(args[i])
                except (ValueError, IndexError):
                    pass
            elif a == "--interruptions" and i < len(args):
                try:
                    interruptions = int(args[i])
                except (ValueError, IndexError):
                    pass
        log_daily_attention(interruptions=interruptions, task_switches=switches, deep_work_hrs=hours)
        print(f"  Logged: {hours}h deep work, {switches} switches, {interruptions} interruptions.")
        _print_status()

    else:
        print("Usage: attention_engine.py [status | log [--hours N] [--switches N] [--interruptions N]]")
