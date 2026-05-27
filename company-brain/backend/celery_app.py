"""Celery app + beat schedule configuration."""
from celery import Celery
from celery.schedules import crontab
from config import settings

celery = Celery(
    "company_brain",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["tasks"],
)

celery.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        # Run renewal scan every 15 minutes
        "renewal-scan-15min": {
            "task": "tasks.run_renewal_scan_task",
            "schedule": crontab(minute="*/15"),
        },
        # Refresh CLV scores every night at 2am UTC
        "clv-refresh-nightly": {
            "task": "tasks.refresh_clv_task",
            "schedule": crontab(hour=2, minute=0),
        },
        # Run full agent decision loop every hour
        "agent-loop-hourly": {
            "task": "tasks.run_agent_loop_task",
            "schedule": crontab(minute=0),
        },
    },
)
