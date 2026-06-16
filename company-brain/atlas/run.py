#!/usr/bin/env python3
"""
run.py — Atlas entry point.

Usage:
  python run.py daily          # Morning: sync, executor, today's tasks
  python run.py weekly         # Sprint: planner + evaluator + review
  python run.py planner        # Strategic priorities + kill list (JSON)
  python run.py executor       # Today's 3 tasks (JSON)
  python run.py evaluator      # Weekly review (JSON)
  python run.py sync           # Sync SQLite → JSON memory files only
  python run.py status         # Quick status snapshot
"""
import sys
import json
from pathlib import Path

_HERE = Path(__file__).parent

try:
    from dotenv import load_dotenv
    load_dotenv(_HERE.parent.parent / "company-brain" / ".env")
    load_dotenv(_HERE / ".env")
except ImportError:
    pass

sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_HERE.parent / "chief"))


def cmd_status():
    """Quick status — no agent call, just memory snapshot."""
    from memory_sync import sync_all
    state = sync_all()
    mrr = state["current_revenue"]
    gap = state["gap"]
    focus = state["focus_load"]
    status_icon = {"GREEN": "🟢", "YELLOW": "🟡", "RED": "🔴"}.get(focus["status"], "⚪")
    print(f"""
  ┌─ Atlas Status ─────────────────────────────────────────┐
  │  MRR:      ${mrr:>10,.0f}  /  ${state['target_revenue']:,.0f} target        │
  │  Gap:      ${gap:>10,.0f}  to close                       │
  │  Focus:    {status_icon} {focus['active_initiatives']}/3 initiatives active               │
  │  Energy:   {state.get('energy_level',0)}/10   Focus score: {state.get('weekly_focus_score',0)}/10            │
  │  Contacts: {state.get('contacts_total',0):<6}  Open actions: {state.get('open_actions',0):<6}              │
  └────────────────────────────────────────────────────────┘""")


def main():
    args = sys.argv[1:]
    cmd = args[0] if args else "status"

    if cmd == "status":
        cmd_status()

    elif cmd == "sync":
        from memory_sync import sync_all
        state = sync_all()
        print(f"  Memory synced — MRR: ${state['current_revenue']:,.0f} | Gap: ${state['gap']:,.0f}")

    elif cmd == "daily":
        from orchestrator import run_daily
        run_daily()

    elif cmd == "weekly":
        from orchestrator import run_weekly
        run_weekly()

    elif cmd == "planner":
        from orchestrator import run_planner_only
        run_planner_only()

    elif cmd == "executor":
        from orchestrator import run_executor_only
        run_executor_only()

    elif cmd == "evaluator":
        from orchestrator import run_evaluator_only
        run_evaluator_only()

    else:
        print(__doc__)


if __name__ == "__main__":
    main()
