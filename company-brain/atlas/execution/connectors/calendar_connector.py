"""
Calendar connector — creates Google Calendar events.

Note: Google Calendar write requires the 'calendar.events' OAuth scope.
The current token was issued with 'calendar.readonly' only.

Until the token is re-issued with write scope, create_event() will
return a clear error rather than silently failing or writing to a
wrong calendar. Logging the intended event to chief.db is the safe fallback.
"""
import sys
from pathlib import Path

_HERE = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_HERE.parent / "chief"))
sys.path.insert(0, str(_HERE.parent.parent / "backend"))

try:
    from dotenv import load_dotenv
    load_dotenv(_HERE.parent.parent / "company-brain" / ".env")
except ImportError:
    pass

_REQUIRED_SCOPE = "https://www.googleapis.com/auth/calendar.events"


def _has_write_scope() -> bool:
    """Check if the current token has calendar write permissions."""
    try:
        import gmail_auth
        creds = gmail_auth.load_credentials()
        if not creds:
            return False
        scopes = getattr(creds, "scopes", None) or []
        return _REQUIRED_SCOPE in scopes or "https://www.googleapis.com/auth/calendar" in scopes
    except Exception:
        return False


def create_event(title: str, start: str, end: str,
                 description: str = "", location: str = "") -> dict:
    """
    Create a Google Calendar event.

    If the token lacks calendar write scope, logs the intended event
    to chief.db as a TASK instead and returns a descriptive error.

    start/end: ISO 8601 datetime strings (e.g. "2026-06-01T10:00:00-04:00")
    Returns {"success": bool, "result": str, "error": str|None}
    """
    if not _has_write_scope():
        # Safe fallback: create a task so the event isn't lost
        try:
            import db
            db.init()
            db.create_action({
                "title": f"[CALENDAR] {title}",
                "action_type": "calendar",
                "priority": "MEDIUM",
                "due_date": start[:10] if start else None,
                "notes": f"Intended calendar event: {title}\nStart: {start}\nEnd: {end}\n{description}",
                "status": "OPEN",
            })
        except Exception:
            pass

        return {
            "success": False,
            "result": f"Event logged as task: '{title}' on {start[:10] if start else '?'}",
            "error": (
                "Calendar write scope not available. "
                "Re-authenticate with calendar.events scope to enable calendar writes. "
                "Event has been saved as a task in chief.db instead."
            ),
        }

    try:
        from googleapiclient.discovery import build
        import httplib2
        from google_auth_httplib2 import AuthorizedHttp
        import gmail_auth

        creds = gmail_auth.load_credentials()
        http = AuthorizedHttp(creds, http=httplib2.Http(disable_ssl_certificate_validation=True))
        service = build("calendar", "v3", http=http)

        event_body = {
            "summary": title,
            "description": description,
            "location": location,
            "start": {"dateTime": start, "timeZone": "America/Toronto"},
            "end":   {"dateTime": end,   "timeZone": "America/Toronto"},
        }
        created = service.events().insert(
            calendarId="primary",
            body=event_body
        ).execute()

        return {
            "success": True,
            "result": f"Event created: {created.get('htmlLink','?')}",
            "error": None,
            "event_id": created.get("id"),
        }
    except Exception as e:
        return {"success": False, "result": "", "error": str(e)}
