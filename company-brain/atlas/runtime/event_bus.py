"""
Atlas event bus — async queue with thread-safe emit for external sources.
"""
import asyncio
from typing import Callable
from .event_model import AtlasEvent

_queue: asyncio.Queue | None = None


def _get_queue() -> asyncio.Queue:
    global _queue
    if _queue is None:
        _queue = asyncio.Queue()
    return _queue


async def emit(event: AtlasEvent):
    """Emit from async context."""
    await _get_queue().put(event)


def emit_sync(event: AtlasEvent):
    """Thread-safe emit from non-async context (e.g. webhooks, cron)."""
    try:
        loop = asyncio.get_running_loop()
        asyncio.run_coroutine_threadsafe(_get_queue().put(event), loop)
    except RuntimeError:
        asyncio.run(emit(event))


async def process_events(handler: Callable):
    """Main consumer loop — runs forever, processes one event at a time."""
    q = _get_queue()
    while True:
        event: AtlasEvent = await q.get()
        try:
            await handler(event)
        except Exception as e:
            print(f"  [bus] Handler error on {event.type}: {e}")
        finally:
            q.task_done()


def queue_size() -> int:
    return _get_queue().qsize() if _queue else 0
