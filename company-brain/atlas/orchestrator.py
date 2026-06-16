"""
orchestrator.py — Atlas Agent Orchestration Engine.

Sequences Planner / Executor / Evaluator agents with memory read/write.
Provides daily and weekly workflow controllers.

Usage:
  python orchestrator.py daily          # Run executor → today's tasks
  python orchestrator.py weekly         # Run planner → evaluator → reset
  python orchestrator.py planner        # Run planner only
  python orchestrator.py executor       # Run executor only
  python orchestrator.py evaluator      # Run evaluator only
  python orchestrator.py sync           # Sync memory only (no agent run)
"""
import json
import sys
from datetime import date, datetime, timezone
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
from memory_sync import sync_all, read_memory, update_state, log_completed_task, _write, TASKS, DASH

INCOME_TARGET = 15000.0


def _print_section(title: str):
    print(f"\n  {'─'*60}")
    print(f"  {title}")
    print(f"  {'─'*60}")


def _save_output(filename: str, data: dict):
    path = _HERE / "dashboard" / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, default=str))


# ── DAILY WORKFLOW ────────────────────────────────────────────────────────────

def run_daily() -> dict:
    """
    Daily workflow: sync memory → run executor → write today.json → print summary.
    Optionally runs planner first if focus is overloaded.
    """
    _print_section("ATLAS — DAILY START")

    # 1. Sync memory
    print("  Syncing memory...")
    state = sync_all()
    memory = read_memory()

    mrr = state["current_revenue"]
    gap = state["gap"]
    focus = state["focus_load"]

    print(f"  MRR: ${mrr:,.0f} | Gap: ${gap:,.0f} | Focus: {focus['status']} ({focus['active_initiatives']}/3)")

    # 2. If focus is RED, run planner first to force kill
    if focus["focus_load"]["status"] == "RED" if "focus_load" in focus else focus.get("status") == "RED":
        print("  ⚠️  Focus overloaded — running Planner first...")
        from agents.planner import run_planner
        plan = run_planner(memory)
        _save_output("planner_last.json", plan)
        print(f"  Planner: {plan.get('focus_decision', 'See planner output')}")

    # 3. Run executor
    print("  Running Executor...")
    from agents.executor import run_executor
    tasks_output = run_executor(memory)
    _save_output("executor_last.json", tasks_output)

    # 4. Write today.json
    today_json = {
        "date": date.today().isoformat(),
        "tasks": tasks_output.get("daily_tasks", []),
        "revenue_objective": tasks_output.get("revenue_objective_today", ""),
        "bottleneck": tasks_output.get("bottleneck", ""),
        "one_number": tasks_output.get("one_number_today", ""),
        "focus_check": tasks_output.get("focus_check", {}),
    }
    _write(TASKS / "today.json", today_json)

    # 5. Update state with bottleneck
    update_state({
        "last_daily_run": datetime.now(timezone.utc).isoformat(),
        "active_bottleneck": tasks_output.get("bottleneck", ""),
    })

    # 6. Print output
    _print_section("TODAY'S EXECUTION PLAN")
    print(f"\n  Revenue objective: {tasks_output.get('revenue_objective_today', '—')}")
    print(f"  One number to hit: {tasks_output.get('one_number_today', '—')}")
    print(f"\n  Today's 3 tasks:")
    for t in tasks_output.get("daily_tasks", []):
        impact_icon = {"direct": "💰", "indirect": "→", "system": "⚙️"}.get(t.get("impact", ""), "•")
        print(f"    {t.get('rank','')}. {impact_icon} {t.get('task','')}")
        print(f"       Outcome: {t.get('expected_outcome','')}")
    if tasks_output.get("bottleneck"):
        print(f"\n  ⚡ Bottleneck: {tasks_output['bottleneck']}")
    focus_check = tasks_output.get("focus_check", {})
    status = focus_check.get("status", "")
    if status in ("YELLOW", "RED"):
        print(f"\n  ⚠️  Focus {status}: {focus_check.get('action_needed', '')}")

    return tasks_output


# ── WEEKLY WORKFLOW ───────────────────────────────────────────────────────────

def run_weekly() -> dict:
    """
    Weekly workflow: sync → planner → evaluator → save → print report.
    """
    _print_section("ATLAS — WEEK START / REVIEW")

    # 1. Sync
    print("  Syncing memory...")
    sync_all()
    memory = read_memory()

    # 2. Planner
    print("  Running Planner...")
    from agents.planner import run_planner
    plan = run_planner(memory)
    _save_output("planner_last.json", plan)

    # 3. Evaluator
    print("  Running Evaluator...")
    from agents.evaluator import run_evaluator
    evaluation = run_evaluator(memory)
    _save_output("evaluator_last.json", evaluation)

    # 4. Update state
    update_state({
        "last_weekly_run": datetime.now(timezone.utc).isoformat(),
        "weekly_focus_score": evaluation.get("focus_report", {}).get("focus_score", 0),
        "next_week_target": evaluation.get("next_week_revenue_target", 0),
        "last_week_score": evaluation.get("week_score", 0),
    })

    # 5. Print weekly plan
    _print_section("WEEKLY PLAN")
    print(f"\n  Primary engine: {plan.get('primary_engine', {}).get('name', '—')}")
    print(f"  Secondary engine: {plan.get('secondary_engine', {}).get('name', '—')}")
    print(f"  Revenue target: ${plan.get('revenue_target_week', 0):,.0f}")
    print(f"  Constraint: {plan.get('constraint', '—')}")
    print(f"\n  Top 3 priorities:")
    for p in plan.get("top_priorities", [])[:3]:
        print(f"    {p.get('rank','')}. {p.get('name','')} — {p.get('rationale','')}")
    if plan.get("kill_list"):
        print(f"\n  Kill mandate:")
        for k in plan["kill_list"]:
            print(f"    ✕ {k.get('name','')} — {k.get('reason','')}")

    # 6. Print evaluation
    _print_section("WEEKLY REVIEW")
    rev = evaluation.get("revenue_summary", {})
    print(f"\n  Revenue produced: ${rev.get('produced', 0):,.0f} / ${rev.get('target', INCOME_TARGET):,.0f}")
    print(f"  Trend: {rev.get('trend', '—')} | {rev.get('diagnosis', '')}")
    focus_rpt = evaluation.get("focus_report", {})
    print(f"\n  Focus score: {focus_rpt.get('focus_score', 0)}/10 — {focus_rpt.get('assessment', '')}")
    print(f"  Week score: {evaluation.get('week_score', 0)}/10 — {evaluation.get('week_rating_reason', '')}")
    print(f"\n  Kill mandate:")
    for k in evaluation.get("kill_mandate", []):
        print(f"    ✕ {k.get('name','')} — {k.get('reason','')} ({k.get('hours_freed',0)}h/wk freed)")
    print(f"\n  Next week focus: {evaluation.get('next_week_primary_focus', '—')}")
    print(f"  Hard question: {evaluation.get('hard_question', '—')}")

    return {"plan": plan, "evaluation": evaluation}


# ── STANDALONE AGENT RUNS ─────────────────────────────────────────────────────

def run_planner_only() -> dict:
    sync_all()
    memory = read_memory()
    from agents.planner import run_planner
    result = run_planner(memory)
    _save_output("planner_last.json", result)
    print(json.dumps(result, indent=2))
    return result


def run_executor_only() -> dict:
    sync_all()
    memory = read_memory()
    from agents.executor import run_executor
    result = run_executor(memory)
    _save_output("executor_last.json", result)
    print(json.dumps(result, indent=2))
    return result


def run_evaluator_only() -> dict:
    sync_all()
    memory = read_memory()
    from agents.evaluator import run_evaluator
    result = run_evaluator(memory)
    _save_output("evaluator_last.json", result)
    print(json.dumps(result, indent=2))
    return result


# ── ENTRY POINT ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    args = sys.argv[1:]
    cmd = args[0] if args else "help"

    commands = {
        "daily":     (run_daily,          "Daily workflow — executor + today's tasks"),
        "weekly":    (run_weekly,          "Weekly workflow — planner + evaluator + reset"),
        "planner":   (run_planner_only,    "Planner agent only — strategic priorities + kill list"),
        "executor":  (run_executor_only,   "Executor agent only — today's 3 tasks"),
        "evaluator": (run_evaluator_only,  "Evaluator agent only — weekly review"),
        "sync":      (lambda: (sync_all(), print("Memory synced.")), "Sync memory only"),
    }

    if cmd in commands:
        fn, _ = commands[cmd]
        fn()
    else:
        print("Atlas Orchestrator")
        print()
        for k, (_, desc) in commands.items():
            print(f"  python orchestrator.py {k:<12} — {desc}")
