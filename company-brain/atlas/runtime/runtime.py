"""
Atlas event runtime — the always-on processing loop.

Flow per event:
  1. Classify (Claude) — what is this? how urgent?
  2. Route              — which agent or escalation path?
  3. Execute or escalate
  4. Persist to event log
"""
import asyncio
import importlib
import sys
from datetime import datetime, timezone
from pathlib import Path

_HERE = Path(__file__).parent.parent
sys.path.insert(0, str(_HERE.parent / "chief"))
sys.path.insert(0, str(_HERE))

from .event_model import AtlasEvent, EventType
from .event_bus import emit, process_events
from .classifier import classify_event
from .router import route_to_agent
from .memory import log_processed_event, event_stats

_URGENCY_ICONS = {
    range(1, 4): "⚪",
    range(4, 7): "🟡",
    range(7, 9): "🟠",
    range(9, 11): "🔴",
}


def _urgency_icon(u: int) -> str:
    for r, icon in _URGENCY_ICONS.items():
        if u in r:
            return icon
    return "⚪"


def _run_agent_sync(module_name: str, fn_name: str) -> str:
    """Run a native Python agent function synchronously."""
    try:
        module = importlib.import_module(module_name)
        fn = getattr(module, fn_name)
        result = fn()
        return result if isinstance(result, str) else str(result)[:500]
    except Exception as e:
        return f"error: {e}"


def _log_escalation(reason: str, event: AtlasEvent, summary: str):
    """Persist escalation to DB for Control Tower pickup."""
    try:
        import db
        db.init()
        db.log_agent_output(
            agent_name="runtime",
            output=f"[{event.type}] {summary}",
            exceptions=None,
            has_escalation=True,
            escalation_reason=reason,
        )
    except Exception:
        pass


async def _handle_event(event: AtlasEvent):
    """Process a single event through classify → route → execute/escalate → log."""
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S")

    # Step 1: Classify
    classification = await asyncio.to_thread(classify_event, event)
    urgency = classification.get("urgency", 3)
    summary = classification.get("summary", "")
    category = classification.get("category", "?")
    icon = _urgency_icon(urgency)

    print(f"  [{ts}] {icon} {event.type:<20} [{category}] u:{urgency} — {summary[:65]}")

    # Step 2: Route
    decision = route_to_agent(classification)
    action = decision["action"]

    # Step 3: Execute / Escalate / Log
    result = None

    if action == "EXECUTE":
        agent = decision["agent"]
        mod = decision["module"]
        fn = decision["fn"]
        print(f"           → {agent} running...", end=" ", flush=True)
        result = await asyncio.to_thread(_run_agent_sync, mod, fn)
        print("done")

    elif action == "ESCALATE":
        reason = decision.get("reason", summary)
        print(f"           🔴 ESCALATE → {reason[:70]}")
        await asyncio.to_thread(_log_escalation, reason, event, summary)

    # Step 4: Persist
    log_processed_event(
        event_dict=event.to_dict(),
        classification=classification,
        decision=decision,
        result=result,
    )


async def _handle_eod():
    print("\n  ╔══ ATLAS END-OF-DAY BRIEF ══════════════════════════════╗\n")
    try:
        from control_tower import generate_daily_brief
        brief = await asyncio.to_thread(generate_daily_brief, False)
        print(brief)
    except Exception as e:
        print(f"  Brief generation failed: {e}")
    stats = event_stats(hours=24)
    print(f"\n  Today: {stats['total']} events | {stats['executed']} executed | "
          f"{stats['escalated']} escalated | {stats['logged']} logged")
    print("  ╚════════════════════════════════════════════════════════╝\n")


async def _handle_eow():
    print("\n  ╔══ ATLAS END-OF-WEEK REPORT ════════════════════════════╗\n")
    try:
        from control_tower import generate_weekly_brief
        report = await asyncio.to_thread(generate_weekly_brief)
        print(report)
    except Exception as e:
        print(f"  Weekly brief failed: {e}")
    print("  ╚════════════════════════════════════════════════════════╝\n")


async def _dispatch(event: AtlasEvent):
    """Top-level dispatcher — handles system events separately from real events."""
    if event.type == EventType.END_OF_DAY:
        await _handle_eod()
    elif event.type == EventType.END_OF_WEEK:
        await _handle_eow()
    else:
        await _handle_event(event)


async def start_runtime(with_sources: bool = True, quiet: bool = False):
    """Start the Atlas event runtime. Runs indefinitely."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    if not quiet:
        print(f"\n  ╔══ ATLAS RUNTIME — {now} UTC ══╗")
        print(f"  ║  Event-driven execution engine active")
        print(f"  ║  Sources: {'email + tasks + cron' if with_sources else 'manual only'}")
        print(f"  ╚══════════════════════════════════════════╝\n")

    tasks = [asyncio.create_task(process_events(_dispatch))]

    if with_sources:
        from .sources import start_all_sources
        tasks.append(asyncio.create_task(start_all_sources()))

    try:
        await asyncio.gather(*tasks)
    except asyncio.CancelledError:
        print("\n  Atlas Runtime stopped.")
