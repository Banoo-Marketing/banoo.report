"""
Atlas Executor — runs queued actions through the correct connector.

Permission model:
  AUTO (0)    → execute immediately, no record in action_queue needed
  LOG  (1)    → execute immediately, log prominently to action_queue as executed
  APPROVE (2) → persist to action_queue as 'pending'; wait for human approval
  MANUAL (3)  → persist to action_queue as 'pending'; never auto-execute

Only execute_approved() can run APPROVE-level actions, and only after the
DB record shows status='approved'.
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

_HERE = Path(__file__).parent.parent
sys.path.insert(0, str(_HERE.parent / "chief"))
sys.path.insert(0, str(_HERE))

try:
    from dotenv import load_dotenv
    load_dotenv(_HERE.parent.parent / "company-brain" / ".env")
except ImportError:
    pass

import db
from .action_schema import AtlasAction, ActionType, PermissionLevel
from .permission_engine import apply_permission, explain_permission


def _log_feedback(action_id: int | None, outcome: str, rejection_reason: str | None = None, result: str | None = None):
    """Fire-and-forget feedback logger — never raises."""
    if not action_id:
        return
    try:
        sys.path.insert(0, str(_HERE))
        from feedback import log_feedback
        log_feedback(action_id, outcome, rejection_reason=rejection_reason, result=result)
    except Exception:
        pass


# ── Connector dispatch ────────────────────────────────────────────────────────

def _run_connector(action: AtlasAction) -> dict:
    """Route action to its connector. Returns {success, result, error}."""
    p = action.payload

    if action.action_type == ActionType.EMAIL_DRAFT:
        from .connectors.gmail_connector import create_draft
        return create_draft(
            to=p.get("to", ""),
            subject=p.get("subject", ""),
            body=p.get("body", ""),
        )

    if action.action_type == ActionType.EMAIL_SEND:
        from .connectors.gmail_connector import send_email
        # action_id must exist in DB — enforced by send_email's safety gate
        db_id = p.get("_db_id")
        if not db_id:
            return {"success": False, "result": "", "error": "Missing _db_id in payload"}
        return send_email(
            action_id=db_id,
            to=p.get("to", ""),
            subject=p.get("subject", ""),
            body=p.get("body", ""),
        )

    if action.action_type == ActionType.CALENDAR_CREATE:
        from .connectors.calendar_connector import create_event
        return create_event(
            title=p.get("title", ""),
            start=p.get("start", ""),
            end=p.get("end", ""),
            description=p.get("description", ""),
            location=p.get("location", ""),
        )

    if action.action_type == ActionType.TASK_CREATE:
        from .connectors.task_connector import create_task
        return create_task(
            title=p.get("title", ""),
            priority=p.get("priority", "MEDIUM"),
            due_date=p.get("due_date"),
            contact=p.get("contact"),
            notes=p.get("notes", ""),
        )

    if action.action_type == ActionType.TASK_UPDATE:
        from .connectors.task_connector import update_task
        return update_task(
            action_id=p.get("id"),
            field=p.get("field", ""),
            value=p.get("value", ""),
        )

    if action.action_type == ActionType.CRM_UPDATE:
        from .connectors.task_connector import update_contact_field
        return update_contact_field(
            email=p.get("email", ""),
            field=p.get("field", ""),
            value=p.get("value", ""),
        )

    if action.action_type == ActionType.NOTIFY:
        # Internal only — just log it
        msg = p.get("message", "")
        print(f"  [notify] {msg}")
        return {"success": True, "result": f"Notified: {msg}", "error": None}

    return {"success": False, "result": "", "error": f"Unknown action_type: {action.action_type!r}"}


# ── Core execution functions ──────────────────────────────────────────────────

def run_action(action: AtlasAction) -> dict:
    """
    Execute a single action immediately (bypasses queue).
    Only call this for AUTO/LOG level actions — never for APPROVE/MANUAL.
    """
    if action.permission_level >= PermissionLevel.APPROVE:
        return {
            "success": False,
            "result": "",
            "error": f"run_action() cannot execute APPROVE/MANUAL actions. Use execute_approved().",
        }
    try:
        result = _run_connector(action)
    except Exception as e:
        result = {"success": False, "result": "", "error": str(e)}

    return result


def submit_action(action: AtlasAction) -> dict:
    """
    Submit an action through the full pipeline:
    - Compute permission level
    - AUTO/LOG → execute immediately
    - APPROVE/MANUAL → persist to action_queue as 'pending'

    Returns {"queued": bool, "executed": bool, "db_id": int|None,
             "result": str, "permission_level": int}
    """
    db.init()
    apply_permission(action)
    level = action.permission_level
    icon = action.level_icon()
    label = action.level_label()

    # AUTO or LOG: run now
    if level <= PermissionLevel.LOG:
        result = run_action(action)
        # Log to queue as executed for audit trail
        db_id = db.queue_action({
            "action_type": action.action_type,
            "permission_level": level,
            "payload": action.payload,
            "source_agent": action.source_agent,
            "rationale": action.rationale,
            "status": "executed" if result["success"] else "failed",
        })
        if result["success"]:
            db.mark_action_executed(db_id, result.get("result", ""))
            _log_feedback(db_id, "executed", result=result.get("result", ""))
        else:
            db.mark_action_failed(db_id, result.get("error", ""))
            _log_feedback(db_id, "failed")

        status = "executed" if result["success"] else "failed"
        print(f"  {icon} [{label}] {action.describe()} → {status}")
        return {
            "queued": False, "executed": True, "db_id": db_id,
            "result": result.get("result", ""),
            "error": result.get("error"),
            "permission_level": level,
        }

    # APPROVE or MANUAL: queue for human
    db_id = db.queue_action({
        "action_type": action.action_type,
        "permission_level": level,
        "payload": action.payload,
        "source_agent": action.source_agent,
        "rationale": action.rationale,
        "status": "pending",
    })
    reason = explain_permission(action)
    print(f"  {icon} [{label}] {action.describe()} → queued (id={db_id}, reason: {reason})")
    return {
        "queued": True, "executed": False, "db_id": db_id,
        "result": f"Queued for approval (id={db_id})",
        "error": None,
        "permission_level": level,
    }


def execute_approved(action_id: int) -> dict:
    """
    Execute an action that has been approved by Emod.
    Verifies the DB record is status='approved' before proceeding.
    """
    db.init()
    record = db.get_queued_action(action_id)
    if not record:
        return {"success": False, "error": f"Action {action_id} not found"}

    status = record.get("status")
    if status == "executed":
        return {"success": True, "result": "Already executed", "error": None}
    if status != "approved":
        return {"success": False, "error": f"Action {action_id} status is '{status}', not 'approved'"}

    try:
        payload = json.loads(record["payload"]) if isinstance(record["payload"], str) else record["payload"]
        # Inject DB id so gmail send_email can verify approval
        payload["_db_id"] = action_id

        action = AtlasAction(
            action_type=record["action_type"],
            permission_level=record["permission_level"],
            payload=payload,
            source_agent=record.get("source_agent", ""),
            rationale=record.get("rationale", ""),
        )

        result = _run_connector(action)
        if result["success"]:
            db.mark_action_executed(action_id, result.get("result", ""))
            _log_feedback(action_id, "executed", result=result.get("result", ""))
            print(f"  ✓ Executed action {action_id}: {result.get('result','')}")
        else:
            db.mark_action_failed(action_id, result.get("error", ""))
            _log_feedback(action_id, "failed")
            print(f"  ✗ Action {action_id} failed: {result.get('error','')}")

        return result

    except Exception as e:
        db.mark_action_failed(action_id, str(e))
        _log_feedback(action_id, "failed")
        return {"success": False, "result": "", "error": str(e)}


def process_queue() -> dict:
    """
    Process all pending actions in the queue:
    - AUTO/LOG items that are still 'pending': execute immediately
    - APPROVE items: list for human review (do not execute)
    - MANUAL items: list only, never touch

    Returns summary of what was executed vs pending approval.
    """
    db.init()
    pending = db.get_pending_actions(limit=100)

    executed = []
    needs_approval = []
    manual_only = []

    for record in pending:
        if record["status"] != "pending":
            continue

        level = record["permission_level"]
        desc = f"[{record['action_type']}] {record.get('rationale','')[:60]}"

        if level <= PermissionLevel.LOG:
            # All records here have status='pending' (filtered above) — execute directly
            result = _execute_record_directly(record)
            executed.append({"id": record["id"], "desc": desc, "result": result})

        elif level == PermissionLevel.APPROVE:
            needs_approval.append({"id": record["id"], "desc": desc})

        else:  # MANUAL
            manual_only.append({"id": record["id"], "desc": desc})

    return {
        "executed": len(executed),
        "needs_approval": len(needs_approval),
        "manual_only": len(manual_only),
        "executed_items": executed,
        "pending_approval": needs_approval,
        "manual_items": manual_only,
    }


def _execute_record_directly(record: dict) -> dict:
    """Execute a DB record as an action (for AUTO/LOG items in process_queue)."""
    try:
        payload = json.loads(record["payload"]) if isinstance(record["payload"], str) else record["payload"]
        action = AtlasAction(
            action_type=record["action_type"],
            permission_level=record["permission_level"],
            payload=payload,
            source_agent=record.get("source_agent", ""),
        )
        result = run_action(action)
        if result["success"]:
            db.mark_action_executed(record["id"], result.get("result", ""))
            _log_feedback(record["id"], "executed", result=result.get("result", ""))
        else:
            db.mark_action_failed(record["id"], result.get("error", ""))
            _log_feedback(record["id"], "failed")
        return result
    except Exception as e:
        db.mark_action_failed(record["id"], str(e))
        _log_feedback(record["id"], "failed")
        return {"success": False, "error": str(e)}
