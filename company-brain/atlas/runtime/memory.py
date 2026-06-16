"""
Atlas runtime memory — event-sourced log of every processed event.

Every event + its classification + decision is appended here.
The Control Tower reads this to generate briefs.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

_HERE = Path(__file__).parent.parent
_EVENT_LOG = _HERE / "memory" / "event_log.json"
_MAX_EVENTS = 2000


def log_processed_event(event_dict: dict, classification: dict, decision: dict,
                         result: str | None = None):
    """Append a processed event to the event log."""
    _EVENT_LOG.parent.mkdir(exist_ok=True)
    entry = {
        "event": event_dict,
        "classification": classification,
        "decision": {k: v for k, v in decision.items()},
        "result": result,
        "processed_at": datetime.now(timezone.utc).isoformat(),
    }

    existing = _read_log()
    existing.append(entry)
    # Trim to max size
    _EVENT_LOG.write_text(json.dumps(existing[-_MAX_EVENTS:], indent=2, default=str))


def _read_log() -> list:
    if not _EVENT_LOG.exists():
        return []
    try:
        return json.loads(_EVENT_LOG.read_text())
    except (json.JSONDecodeError, OSError):
        return []


def get_recent_events(hours: int = 24) -> list[dict]:
    """Return events from the last N hours."""
    from datetime import timedelta
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    return [
        e for e in _read_log()
        if e.get("processed_at", "") >= cutoff
    ]


def get_escalations(hours: int = 24) -> list[dict]:
    """Return only escalated events from the last N hours."""
    return [
        e for e in get_recent_events(hours)
        if e.get("decision", {}).get("action") == "ESCALATE"
    ]


def event_stats(hours: int = 24) -> dict:
    events = get_recent_events(hours)
    actions = [e.get("decision", {}).get("action", "LOG_ONLY") for e in events]
    return {
        "total": len(events),
        "executed": actions.count("EXECUTE"),
        "escalated": actions.count("ESCALATE"),
        "logged": actions.count("LOG_ONLY"),
        "by_type": _count_by(events, lambda e: e["event"]["type"]),
        "by_category": _count_by(events, lambda e: e["classification"].get("category", "?")),
    }


def _count_by(events: list, key_fn) -> dict:
    counts: dict = {}
    for e in events:
        try:
            k = key_fn(e)
            counts[k] = counts.get(k, 0) + 1
        except Exception:
            pass
    return dict(sorted(counts.items(), key=lambda x: -x[1]))
