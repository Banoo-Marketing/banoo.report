"""
scheduler.py — Atlas Agent Scheduler.

Determines which agents are due to run based on their registered frequency
and last_run timestamp, then runs them via agent_monitor.

Frequency rules:
  daily     → due if last_run is NULL or > 20 hours ago
  weekly    → due if last_run is NULL or > 6 days ago
  monthly   → due if last_run is NULL or > 28 days ago
  triggered → never auto-run (manual only)

Usage:
  python scheduler.py status            Show due/not-due status for all agents
  python scheduler.py run               Run all due agents now (one-shot)
  python scheduler.py run --dry         Show what would run without executing
  python scheduler.py loop [--interval N]  Start continuous loop (default: 30 min)
"""
import sys
import time
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

# How long before each frequency is considered due
_FREQUENCY_THRESHOLDS = {
    "daily":   timedelta(hours=20),
    "weekly":  timedelta(days=6),
    "monthly": timedelta(days=28),
}


def _parse_last_run(last_run_str: str | None) -> datetime | None:
    """Parse last_run string from DB into UTC datetime, or None."""
    if not last_run_str:
        return None
    try:
        # DB stores as 'YYYY-MM-DD HH:MM:SS' (sqlite datetime())
        return datetime.fromisoformat(last_run_str).replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None


def is_due(agent: dict) -> bool:
    """
    Return True if this agent should run now.

    triggered agents are never auto-run.
    NULL last_run → always due (agent has never run).
    """
    freq = (agent.get("frequency") or "weekly").lower()

    if freq == "triggered":
        return False

    threshold = _FREQUENCY_THRESHOLDS.get(freq)
    if threshold is None:
        return False  # unknown frequency → skip

    last_run = _parse_last_run(agent.get("last_run"))
    if last_run is None:
        return True  # never run → always due

    return datetime.now(timezone.utc) - last_run >= threshold


def next_run_str(agent: dict) -> str:
    """Human-readable string for when agent is next due."""
    freq = (agent.get("frequency") or "weekly").lower()
    if freq == "triggered":
        return "manual only"

    threshold = _FREQUENCY_THRESHOLDS.get(freq)
    if threshold is None:
        return "unknown frequency"

    last_run = _parse_last_run(agent.get("last_run"))
    if last_run is None:
        return "now (never run)"

    next_due = last_run + threshold
    now = datetime.now(timezone.utc)
    if next_due <= now:
        return "now (overdue)"

    delta = next_due - now
    hours = int(delta.total_seconds() // 3600)
    minutes = int((delta.total_seconds() % 3600) // 60)
    if hours >= 24:
        days = hours // 24
        return f"in {days}d {hours % 24}h"
    if hours > 0:
        return f"in {hours}h {minutes}m"
    return f"in {minutes}m"


def run_due_agents(dry_run: bool = False) -> dict:
    """
    Find all active agents that are due and run them.

    dry_run=True: print what would run but don't execute.
    Returns: {ran: [names], skipped: [names], escalations: int, errors: [names]}
    """
    db.init()
    agents = db.get_agents("active")
    due = [a for a in agents if is_due(a)]
    skipped = [a["name"] for a in agents if not is_due(a)]

    if not due:
        return {"ran": [], "skipped": skipped, "escalations": 0, "errors": []}

    if dry_run:
        print(f"  [dry-run] Would run {len(due)} agent(s):")
        for a in due:
            print(f"    • {a['name']} [{a.get('frequency','?')}] last:{(a.get('last_run') or 'never')[:16]}")
        return {"ran": [], "skipped": skipped, "escalations": 0, "errors": [], "dry_run": True}

    from agent_monitor import run_agent, build_monitor_report

    ran = []
    errors = []
    results = []
    for agent in due:
        triage = run_agent(agent)
        results.append(triage)
        if triage.get("agent_name") and "error" not in triage.get("summary", "").lower()[:20]:
            ran.append(agent["name"])
        else:
            errors.append(agent["name"])

    report = build_monitor_report(results)
    return {
        "ran": ran,
        "skipped": skipped,
        "escalations": report.get("escalations", 0),
        "errors": errors,
        "report": report,
    }


def show_status():
    """Print due/not-due status table for all active agents."""
    db.init()
    agents = db.get_agents("active")
    if not agents:
        print("\n  No active agents. Run: atlas factory register")
        return

    print(f"\n  Agent Schedule Status — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC\n  {'─'*62}")
    for a in agents:
        due = is_due(a)
        freq = a.get("frequency", "?")
        last = (a.get("last_run") or "never")[:16]
        next_r = next_run_str(a)
        runs = a.get("run_count", 0)
        icon = "🟢 DUE    " if due else "⚪ waiting"
        print(f"  {icon}  {a['name']:<10} [{freq:>8}]  last:{last}  next:{next_r}  runs:{runs}")


def schedule_loop(interval_minutes: int = 30):
    """
    Continuous scheduler loop. Checks and runs due agents every N minutes.
    Prints a heartbeat line every iteration. Ctrl+C for clean shutdown.
    """
    print(f"\n  Atlas Scheduler started — checking every {interval_minutes} minutes")
    print(f"  Press Ctrl+C to stop.\n")

    try:
        while True:
            now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
            result = run_due_agents()
            ran = result.get("ran", [])
            esc = result.get("escalations", 0)

            if ran:
                print(f"  [{now}] Ran: {', '.join(ran)} | Escalations: {esc}")
            else:
                print(f"  [{now}] ♥ heartbeat — no agents due")

            time.sleep(interval_minutes * 60)

    except KeyboardInterrupt:
        print("\n  Scheduler stopped.")


if __name__ == "__main__":
    db.init()
    args = sys.argv[1:]
    cmd = args[0] if args else "status"

    if cmd == "status":
        show_status()

    elif cmd == "run":
        dry = "--dry" in args
        print(f"\n  Scheduler: {'dry run — ' if dry else ''}checking due agents...\n")
        result = run_due_agents(dry_run=dry)
        if not dry:
            ran = result.get("ran", [])
            esc = result.get("escalations", 0)
            errs = result.get("errors", [])
            print(f"\n  Ran: {ran or 'none'}")
            if esc:
                print(f"  Escalations: {esc} — run 'atlas tower decisions' to review")
            if errs:
                print(f"  Errors: {errs}")

    elif cmd == "loop":
        interval = 30
        for a in args[1:]:
            if a.startswith("--interval"):
                try:
                    interval = int(a.split("=")[-1]) if "=" in a else int(args[args.index(a) + 1])
                except (ValueError, IndexError):
                    pass
        schedule_loop(interval_minutes=interval)

    else:
        print("Usage: scheduler.py [status | run [--dry] | loop [--interval N]]")
