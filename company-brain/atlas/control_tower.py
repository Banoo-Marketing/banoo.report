"""
control_tower.py — Atlas Control Tower: CEO Interface.

What Emod sees: exceptions + decisions only. Not reports.

Daily brief  = top 3 decisions required + risks + revenue signals
Weekly brief = workforce report + what was automated this week

Usage:
  python control_tower.py brief         # Daily brief: exceptions + decisions
  python control_tower.py weekly        # Weekly workforce + automation report
  python control_tower.py decisions     # Pending decisions only
  python control_tower.py workforce     # Agent workforce health
"""
import json
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

import anthropic
import db
from agent_monitor import run_all_agents, build_monitor_report

TOWER_SYSTEM = """You are Atlas Control Tower — the CEO exception filter.

Your job: synthesize agent outputs into what the CEO must act on today.

Filter rules:
- SURFACE: revenue risk, time-sensitive decisions, opportunities with 48h window, legal/financial deadlines, client churn signals
- SUPPRESS: routine status, metrics within range, all-clear reports, process confirmations

Output format (strict):

DECISIONS REQUIRED (max 3)
━━━━━━━━━━━━━━━━━━━━━━
1. [DECISION] What choice must be made
   Stakes: What happens if delayed
   Deadline: When

REVENUE SIGNALS
━━━━━━━━━━━━━━━
• [SIGNAL] What's happening + amount/client

RISKS
━━━━━
• [RISK] What could break + likelihood

AUTOMATED THIS RUN
━━━━━━━━━━━━━━━━━━
• [AGENT] What it handled (no action needed)

If nothing requires attention: single line → "All systems nominal. No action required."
"""

WORKFORCE_SYSTEM = """You are Atlas Control Tower — weekly workforce report generator.

Analyze agent performance data and produce a crisp CEO briefing.

Output format:

WORKFORCE HEALTH
━━━━━━━━━━━━━━━━
[Agent name] — [status] — [what it handled this week] — [issues if any]

AUTOMATION WINS THIS WEEK
━━━━━━━━━━━━━━━━━━━━━━━━━
• What was handled autonomously (with hours saved estimate)

AGENTS NEEDING ATTENTION
━━━━━━━━━━━━━━━━━━━━━━━━
• Any agent underperforming, erroring, or needing tuning

FACTORY RECOMMENDATION
━━━━━━━━━━━━━━━━━━━━━━
• New automation candidates worth building (if any)
• Agents to kill or merge (if any)
"""


def _get_live_context() -> dict:
    """Pull live data for the tower brief."""
    db.init()
    ctx = {}

    # Pending escalations from all agents
    ctx["escalations"] = db.get_pending_escalations(limit=20)

    # Active initiatives count (focus check)
    try:
        inits = db.get_initiatives("active")
        ctx["initiative_count"] = len(inits)
        ctx["initiatives"] = [
            {"name": i["name"], "roi_score": i.get("roi_score", 0), "status": i.get("status")}
            for i in inits
        ]
    except Exception:
        ctx["initiative_count"] = 0
        ctx["initiatives"] = []

    # Revenue snapshot
    try:
        streams = db.get_revenue_streams()
        ctx["monthly_revenue"] = sum(s.get("monthly_amount", 0) for s in streams)
        ctx["revenue_streams"] = len(streams)
    except Exception:
        ctx["monthly_revenue"] = 0
        ctx["revenue_streams"] = 0

    # Open high-priority actions
    try:
        actions = db.get_actions(status="OPEN", priority="HIGH", limit=10)
        ctx["high_priority_actions"] = [
            {"title": a["title"], "due_date": a.get("due_date"), "contact": a.get("contact_name")}
            for a in actions
        ]
    except Exception:
        ctx["high_priority_actions"] = []

    # Agent workforce health
    agents = db.get_agents("active")
    ctx["workforce"] = [
        {
            "name": a["name"],
            "last_run": (a.get("last_run") or "never")[:16],
            "run_count": a.get("run_count", 0),
            "exception_count": a.get("exception_count", 0),
            "frequency": a.get("frequency", "?"),
        }
        for a in agents
    ]

    return ctx


def _get_weekly_context() -> dict:
    """Pull weekly performance data for workforce report."""
    db.init()
    ctx = _get_live_context()

    # Agent output history (last 7 days)
    agents = db.get_agents("active")
    ctx["agent_history"] = {}
    for a in agents:
        history = db.get_agent_history(a["name"], limit=10)
        ctx["agent_history"][a["name"]] = history

    # Kill list candidates (agents with high exception counts)
    ctx["kill_candidates"] = [
        a for a in ctx["workforce"]
        if a["exception_count"] > 3 or (a["run_count"] > 0 and a["exception_count"] / max(a["run_count"], 1) > 0.5)
    ]

    return ctx


def generate_daily_brief(run_agents: bool = True) -> str:
    """Generate the daily control tower brief. Optionally runs agents first."""
    escalation_items = []

    if run_agents:
        print("  Running agent workforce...\n")
        results = run_all_agents()
        report = build_monitor_report(results)
        escalation_items = report.get("items", [])
        all_summaries = report.get("all_summaries", [])
    else:
        # Use stored pending escalations
        pending = db.get_pending_escalations(limit=10)
        escalation_items = [
            {
                "agent": e.get("agent_name", "?"),
                "urgency": e.get("urgency", "NORMAL"),
                "reason": e.get("escalation_reason", ""),
                "action": None,
                "summary": (e.get("output") or "")[:200]
            }
            for e in pending
        ]
        all_summaries = []

    ctx = _get_live_context()

    # Build the tower input
    tower_input = f"""Agent run complete. Synthesize into CEO brief.

ESCALATIONS FROM AGENTS ({len(escalation_items)}):
{json.dumps(escalation_items, indent=2, default=str)}

AGENT SUMMARIES:
{json.dumps(all_summaries, indent=2, default=str)}

LIVE CONTEXT:
- Active initiatives: {ctx['initiative_count']}/3 {"⚠️ AT CAPACITY" if ctx['initiative_count'] >= 3 else ""}
- Monthly revenue: ${ctx['monthly_revenue']:,.0f}
- High-priority actions: {len(ctx['high_priority_actions'])}
{json.dumps(ctx['high_priority_actions'][:5], indent=2, default=str)}

Produce the CEO brief now."""

    client = anthropic.Anthropic()
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1000,
        system=TOWER_SYSTEM,
        messages=[{"role": "user", "content": tower_input}]
    )

    return resp.content[0].text


def generate_weekly_brief() -> str:
    """Generate weekly workforce + automation report."""
    ctx = _get_weekly_context()

    try:
        from feedback import get_feedback_summary
        feedback_data = get_feedback_summary(days=7)
    except Exception:
        feedback_data = {}

    workforce_input = f"""Weekly workforce review. Produce CEO briefing.

WORKFORCE DATA:
{json.dumps(ctx['workforce'], indent=2)}

AGENT RUN HISTORY (last 7 days):
{json.dumps({k: v[:3] for k, v in ctx['agent_history'].items()}, indent=2, default=str)}

KILL CANDIDATES:
{json.dumps(ctx.get('kill_candidates', []), indent=2)}

PENDING ESCALATIONS (unreviewed):
{json.dumps(ctx['escalations'][:10], indent=2, default=str)}

AGENT PERFORMANCE FEEDBACK (last 7 days):
{json.dumps(feedback_data, indent=2)}

BUSINESS CONTEXT:
- Monthly revenue: ${ctx['monthly_revenue']:,.0f}
- Active initiatives: {ctx['initiative_count']}/3

Produce the weekly workforce report now."""

    client = anthropic.Anthropic()
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1500,
        system=WORKFORCE_SYSTEM,
        messages=[{"role": "user", "content": workforce_input}]
    )
    return resp.content[0].text


def show_pending_decisions():
    """Print all escalations that need a human decision."""
    db.init()
    pending = db.get_pending_escalations()

    critical = [e for e in pending if e.get("urgency") == "CRITICAL"]
    high = [e for e in pending if e.get("urgency") == "HIGH"]
    normal = [e for e in pending if e.get("urgency") not in ("CRITICAL", "HIGH")]

    total = len(pending)
    if total == 0:
        print("\n  No decisions required. All clear.")
        return

    print(f"\n  Pending Decisions ({total})\n  {'═'*60}")

    for group, label, icon in [(critical, "CRITICAL", "🔴"), (high, "HIGH", "🟡"), (normal, "NORMAL", "🔵")]:
        if group:
            print(f"\n  {icon} {label} ({len(group)})")
            for e in group:
                print(f"\n  [{e.get('agent_name','?')}] {e.get('escalation_reason','')}")
                print(f"  Output: {(e.get('output') or '')[:120]}...")
                print(f"  Ran: {(e.get('ran_at') or '')[:16]}")
                print(f"  ID: {e.get('id')} — mark reviewed: atlas tower resolve {e.get('id')}")


def show_workforce():
    """Print current workforce roster + health."""
    db.init()
    active = db.get_agents("active")
    killed = db.get_agents("killed")

    print(f"\n  Agent Workforce — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC")
    print(f"  {len(active)} active | {len(killed)} killed\n  {'═'*60}")

    for a in active:
        runs = a.get("run_count", 0)
        exc = a.get("exception_count", 0)
        last = (a.get("last_run") or "never")[:16]
        freq = a.get("frequency", "?")
        error_rate = (exc / runs * 100) if runs > 0 else 0

        if error_rate > 50 or exc > 3:
            health = "🔴"
        elif error_rate > 20 or exc > 1:
            health = "🟡"
        else:
            health = "🟢"

        atype = "◆" if a.get("agent_type") == "native" else "◇"
        print(f"  {health} {atype} {a['name']:<18} [{freq:>8}] runs:{runs:>3} exc:{exc:>2} last:{last}")
        if a.get("purpose"):
            print(f"     {a['purpose'][:70]}")

    if killed:
        print(f"\n  Killed ({len(killed)}):")
        for a in killed:
            print(f"    ✕ {a['name']:<18} — {(a.get('kill_reason') or '')[:50]}")


if __name__ == "__main__":
    db.init()
    args = sys.argv[1:]
    cmd = args[0] if args else "brief"

    if cmd == "brief":
        run_now = "--skip-run" not in args
        brief = generate_daily_brief(run_agents=run_now)
        print(f"\n  ╔══ ATLAS CONTROL TOWER — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC ══╗\n")
        print(brief)
        print(f"\n  ╚{'═'*60}╝")

    elif cmd == "weekly":
        report = generate_weekly_brief()
        print(f"\n  ╔══ ATLAS WEEKLY WORKFORCE REPORT — {datetime.now(timezone.utc).strftime('%Y-%m-%d')} ══╗\n")
        print(report)
        print(f"\n  ╚{'═'*60}╝")

    elif cmd == "decisions":
        show_pending_decisions()

    elif cmd == "workforce":
        show_workforce()

    elif cmd == "resolve" and len(args) > 1:
        try:
            eid = int(args[1])
            db.mark_escalation_reviewed(eid)
            print(f"  Escalation {eid} marked as reviewed.")
        except ValueError:
            print(f"  Invalid ID: {args[1]}")

    else:
        print("Usage: control_tower.py [brief [--skip-run] | weekly | decisions | workforce | resolve <id>]")
