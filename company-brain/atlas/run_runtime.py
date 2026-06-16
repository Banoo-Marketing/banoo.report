"""
run_runtime.py — Atlas Event Runtime entry point.

Usage:
  python run_runtime.py                      Start full runtime (email + cron + tasks)
  python run_runtime.py --no-sources         Start loop only (accepts manual events)
  python run_runtime.py emit <TYPE> [json]   Emit a single test event and process it
  python run_runtime.py status               Show event log stats (last 24h)
  python run_runtime.py log [n]              Show last N processed events
"""
import asyncio
import json
import sys
from pathlib import Path

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE.parent / "chief"))
sys.path.insert(0, str(_HERE))

try:
    from dotenv import load_dotenv
    load_dotenv(_HERE.parent.parent / "company-brain" / ".env")
    load_dotenv(_HERE / ".env")
except ImportError:
    pass

from runtime.event_model import AtlasEvent, EventType, EventSource, EventPriority
from runtime.event_bus import emit
from runtime.runtime import start_runtime, _dispatch
from runtime.memory import event_stats, get_recent_events, get_escalations


async def emit_single(event_type: str, payload: dict = None, priority: str = EventPriority.MEDIUM):
    """Emit one event, process it, and exit."""
    event = AtlasEvent(
        type=event_type.upper(),
        source=EventSource.MANUAL,
        payload=payload or {},
        priority=priority,
    )
    print(f"\n  Emitting: {event_type.upper()}")
    await _dispatch(event)


def cmd_status():
    stats = event_stats(hours=24)
    print(f"\n  Atlas Runtime — Last 24h\n  {'─'*40}")
    print(f"  Total events : {stats['total']}")
    print(f"  Executed     : {stats['executed']}")
    print(f"  Escalated    : {stats['escalated']}")
    print(f"  Logged only  : {stats['logged']}")
    if stats["by_type"]:
        print(f"\n  By type:")
        for t, n in list(stats["by_type"].items())[:8]:
            print(f"    {t:<24} {n}")
    if stats["by_category"]:
        print(f"\n  By category:")
        for c, n in list(stats["by_category"].items())[:6]:
            print(f"    {c:<18} {n}")
    esc = get_escalations(hours=24)
    if esc:
        print(f"\n  Escalations ({len(esc)}):")
        for e in esc[:5]:
            d = e.get("decision", {})
            ev = e.get("event", {})
            print(f"    🔴 [{ev.get('type','?')}] {d.get('reason','')[:70]}")


def cmd_log(n: int = 20):
    events = get_recent_events(hours=72)[-n:]
    print(f"\n  Event Log — last {len(events)} entries\n  {'─'*60}")
    for e in events:
        ev = e.get("event", {})
        cl = e.get("classification", {})
        de = e.get("decision", {})
        ts = e.get("processed_at", "")[:16]
        action = de.get("action", "?")
        icon = {"EXECUTE": "✓", "ESCALATE": "🔴", "LOG_ONLY": "·"}.get(action, "?")
        print(f"  {icon} {ts} {ev.get('type','?'):<22} {cl.get('summary','')[:50]}")


if __name__ == "__main__":
    args = sys.argv[1:]

    if not args:
        asyncio.run(start_runtime(with_sources=True))

    elif args[0] == "--no-sources":
        asyncio.run(start_runtime(with_sources=False))

    elif args[0] == "emit":
        if len(args) < 2:
            print("Usage: run_runtime.py emit <EVENT_TYPE> [json_payload]")
            sys.exit(1)
        payload = {}
        if len(args) > 2:
            try:
                payload = json.loads(args[2])
            except json.JSONDecodeError:
                payload = {"raw": args[2]}
        asyncio.run(emit_single(args[1], payload))

    elif args[0] == "status":
        cmd_status()

    elif args[0] == "log":
        n = int(args[1]) if len(args) > 1 else 20
        cmd_log(n)

    else:
        print(__doc__)
