"""
Atlas event sources — polls real-world data and emits events into the bus.

Sources:
  - Gmail: new emails every 5 minutes
  - Overdue tasks: check every hour
  - Cron: END_OF_DAY at 21:00 UTC (5pm Toronto EDT), END_OF_WEEK Friday 22:00 UTC
"""
import asyncio
import sqlite3
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

_HERE = Path(__file__).parent.parent
sys.path.insert(0, str(_HERE.parent / "chief"))
sys.path.insert(0, str(_HERE))

from .event_model import AtlasEvent, EventType, EventSource, EventPriority
from .event_bus import emit

_EMAIL_DB = _HERE.parent / "email-analyzer" / "email_cache.db"

# Track watermarks so we don't re-emit the same events
_last_email_ts: int = 0
_last_overdue_check: str = ""


async def poll_new_emails(interval: int = 300):
    """Emit EMAIL_RECEIVED events for any emails newer than last seen."""
    global _last_email_ts
    await asyncio.sleep(10)  # warm-up delay

    # Bootstrap watermark to current max so we don't flood on startup
    if _EMAIL_DB.exists() and _last_email_ts == 0:
        try:
            with sqlite3.connect(_EMAIL_DB) as c:
                row = c.execute("SELECT MAX(date_ts) FROM emails").fetchone()
                _last_email_ts = row[0] or 0
        except Exception:
            pass

    while True:
        await asyncio.sleep(interval)
        if not _EMAIL_DB.exists():
            continue
        try:
            with sqlite3.connect(_EMAIL_DB) as c:
                rows = c.execute("""
                    SELECT id, sender, subject, date_ts, body_text
                    FROM emails
                    WHERE date_ts > ?
                    ORDER BY date_ts ASC LIMIT 20
                """, (_last_email_ts,)).fetchall()

            for row in rows:
                _last_email_ts = max(_last_email_ts, row[3])
                body = (row[4] or "")[:400]
                await emit(AtlasEvent(
                    type=EventType.EMAIL_RECEIVED,
                    source=EventSource.GMAIL,
                    payload={
                        "sender": row[1],
                        "subject": row[2],
                        "body_preview": body,
                        "email_id": row[0],
                    },
                    priority=EventPriority.MEDIUM,
                ))

        except Exception as e:
            print(f"  [source:email] {e}")


async def poll_overdue_tasks(interval: int = 3600):
    """Emit TASK_OVERDUE for any open action past its due date."""
    global _last_overdue_check
    await asyncio.sleep(30)

    while True:
        await asyncio.sleep(interval)
        today = datetime.now(timezone.utc).date().isoformat()
        if _last_overdue_check == today:
            continue
        _last_overdue_check = today

        try:
            import db
            db.init()
            actions = db.get_actions(status="OPEN", limit=100)
            for a in actions:
                due = a.get("due_date") or a.get("deadline")
                if due and due < today:
                    priority = EventPriority.HIGH if a.get("priority") == "HIGH" else EventPriority.MEDIUM
                    await emit(AtlasEvent(
                        type=EventType.TASK_OVERDUE,
                        source=EventSource.SYSTEM,
                        payload={
                            "title": a.get("title", "?"),
                            "due_date": due,
                            "days_overdue": (
                                datetime.now(timezone.utc).date()
                                - datetime.fromisoformat(due).date()
                            ).days,
                            "action_id": a.get("id"),
                        },
                        priority=priority,
                    ))
        except Exception as e:
            print(f"  [source:tasks] {e}")


async def cron_scheduler():
    """Fire END_OF_DAY and END_OF_WEEK events on schedule."""
    _fired_today: set = set()

    while True:
        await asyncio.sleep(60)
        now = datetime.now(timezone.utc)
        today = now.date().isoformat()

        # END_OF_DAY: 21:00 UTC = 5pm Toronto EDT
        eod_key = f"EOD-{today}"
        if now.hour == 21 and now.minute < 2 and eod_key not in _fired_today:
            _fired_today.add(eod_key)
            await emit(AtlasEvent(
                type=EventType.END_OF_DAY,
                source=EventSource.SYSTEM,
                payload={"date": today, "day": now.strftime("%A")},
                priority=EventPriority.MEDIUM,
            ))

        # END_OF_WEEK: Friday 22:00 UTC
        eow_key = f"EOW-{today}"
        if now.weekday() == 4 and now.hour == 22 and now.minute < 2 and eow_key not in _fired_today:
            _fired_today.add(eow_key)
            await emit(AtlasEvent(
                type=EventType.END_OF_WEEK,
                source=EventSource.SYSTEM,
                payload={"week_ending": today},
                priority=EventPriority.MEDIUM,
            ))

        # Prune old fired keys (keep last 14 days)
        cutoff = (now.date() - timedelta(days=14)).isoformat()
        _fired_today -= {k for k in _fired_today if k.split("-", 1)[-1] < cutoff}


async def start_all_sources():
    """Start all event source pollers concurrently."""
    await asyncio.gather(
        poll_new_emails(),
        poll_overdue_tasks(),
        cron_scheduler(),
    )
