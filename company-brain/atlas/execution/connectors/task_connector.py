"""
Task connector — creates and updates actions in chief.db.

This is the safest connector: all operations are local SQLite writes
with no external API calls.
"""
import sys
from pathlib import Path

_HERE = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_HERE.parent / "chief"))

try:
    from dotenv import load_dotenv
    load_dotenv(_HERE.parent.parent / "company-brain" / ".env")
except ImportError:
    pass


def create_task(title: str, priority: str = "MEDIUM",
                due_date: str = None, contact: str = None,
                notes: str = "", action_type: str = "task") -> dict:
    """
    Create an action item in chief.db.

    Returns {"success": bool, "result": str, "error": str|None}
    """
    try:
        import db
        db.init()
        action_id = db.create_action({
            "title": title,
            "action_type": action_type,
            "priority": priority.upper() if priority else "MEDIUM",
            "due_date": due_date,
            "contact_name": contact,
            "notes": notes,
            "status": "OPEN",
        })
        return {
            "success": True,
            "result": f"Task created (id={action_id}): {title}",
            "error": None,
            "action_id": action_id,
        }
    except Exception as e:
        return {"success": False, "result": "", "error": str(e)}


def update_task(action_id: int, field: str, value: str) -> dict:
    """
    Update a single field on an existing action.

    Allowed fields: status, priority, due_date, notes, suggested_next
    Returns {"success": bool, "result": str, "error": str|None}
    """
    ALLOWED_FIELDS = {"status", "priority", "due_date", "notes", "suggested_next"}
    if field not in ALLOWED_FIELDS:
        return {
            "success": False,
            "result": "",
            "error": f"Field '{field}' is not updateable. Allowed: {ALLOWED_FIELDS}",
        }
    try:
        import db, sqlite3
        db.init()
        with sqlite3.connect(db.DB_PATH) as c:
            c.execute(
                f"UPDATE actions SET {field}=?, updated_at=datetime('now') WHERE id=?",
                (value, action_id)
            )
            if c.rowcount == 0:
                return {"success": False, "result": "", "error": f"Action {action_id} not found"}
        return {
            "success": True,
            "result": f"Task #{action_id} {field} → {value}",
            "error": None,
        }
    except Exception as e:
        return {"success": False, "result": "", "error": str(e)}


def update_contact_field(email: str, field: str, value: str) -> dict:
    """
    Update a single field on a contact record.

    Allowed fields: role, company, how_we_met, suggested_action, relationship
    """
    ALLOWED_FIELDS = {"role", "company", "how_we_met", "suggested_action",
                      "relationship", "nurture_score"}
    if field not in ALLOWED_FIELDS:
        return {
            "success": False,
            "result": "",
            "error": f"Field '{field}' not updateable. Allowed: {ALLOWED_FIELDS}",
        }
    try:
        import db, sqlite3
        db.init()
        with sqlite3.connect(db.DB_PATH) as c:
            c.execute(
                f"UPDATE contacts SET {field}=?, updated_at=datetime('now') WHERE lower(email)=lower(?)",
                (value, email)
            )
            if c.rowcount == 0:
                return {"success": False, "result": "", "error": f"Contact {email!r} not found"}
        return {
            "success": True,
            "result": f"Contact {email} {field} → {value}",
            "error": None,
        }
    except Exception as e:
        return {"success": False, "result": "", "error": str(e)}
