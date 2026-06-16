"""Celery task definitions."""
from celery_app import celery
import renewal_engine
import clv_engine
import agent_loop


@celery.task(name="tasks.run_renewal_scan_task", bind=True, max_retries=3)
def run_renewal_scan_task(self):
    """Scan for upcoming renewals and queue email drafts for approval."""
    try:
        results = renewal_engine.run_renewal_scan()
        return {"queued": len(results), "items": results}
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)


@celery.task(name="tasks.refresh_clv_task", bind=True, max_retries=2)
def refresh_clv_task(self):
    """Recalculate CLV scores for all contacts."""
    try:
        count = clv_engine.refresh_all_clv()
        return {"updated_contacts": count}
    except Exception as exc:
        raise self.retry(exc=exc, countdown=120)


@celery.task(name="tasks.run_agent_loop_task", bind=True, max_retries=3)
def run_agent_loop_task(self):
    """Run the AI decision loop across all active deals."""
    try:
        actions = agent_loop.run_full_scan()
        return {"actions_queued": len(actions)}
    except Exception as exc:
        raise self.retry(exc=exc, countdown=120)


@celery.task(name="tasks.scan_gmail_inbox_task", bind=True, max_retries=2)
def scan_gmail_inbox_task(self):
    """Scan Gmail inbox for renewal signals and follow-up gaps. Queues actions for approval."""
    try:
        import gmail_inbox_scanner
        result = gmail_inbox_scanner.run_inbox_scan()
        return result
    except Exception as exc:
        raise self.retry(exc=exc, countdown=300)


@celery.task(name="tasks.execute_approved_action", bind=True, max_retries=2)
def execute_approved_action(self, action_id: int):
    """
    Execute a human-approved action from the queue.
    Currently logs + marks as executed. Wire up Gmail sender here for emails.
    """
    import database as db
    import json

    action = db.fetchone(
        "SELECT * FROM action_queue WHERE id = %s AND status = 'APPROVED'",
        (action_id,),
    )
    if not action:
        return {"error": f"Action {action_id} not found or not approved"}

    try:
        payload = action["payload"] if isinstance(action["payload"], dict) else json.loads(action["payload"])

        # TODO: Wire up actual execution per action type:
        # if action["action_type"] == "renewal_email": gmail_sender.send(...)
        # if action["action_type"] == "assign_task":   hubspot.create_task(...)

        db.execute(
            "UPDATE action_queue SET status='EXECUTED', executed_at=NOW() WHERE id=%s",
            (action_id,),
        )
        db.execute(
            "INSERT INTO audit_log (action_type, deal_id, actor, details) VALUES (%s,%s,'system',%s)",
            ("action_executed", action["deal_id"], json.dumps({"action_id": action_id, "type": action["action_type"]})),
        )
        return {"executed": action_id, "type": action["action_type"]}

    except Exception as exc:
        db.execute(
            "UPDATE action_queue SET status='FAILED', error_message=%s WHERE id=%s",
            (str(exc), action_id),
        )
        raise self.retry(exc=exc, countdown=60)
