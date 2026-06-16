"""
Gmail connector — creates drafts and sends approved emails via Gmail API.

Safety contract:
  - create_draft():  always safe, creates a draft only, nothing is sent
  - send_email():    only callable from executor AFTER action is APPROVED in DB
                     raises PermissionError if called without approval record

Uses the same gmail_auth credentials as the rest of the system.
"""
import base64
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

_HERE = Path(__file__).parent.parent.parent          # → atlas/
_REPO = _HERE.parent.parent                          # → banoo.report/
sys.path.insert(0, str(_REPO / "company-brain" / "chief"))
sys.path.insert(0, str(_REPO / "company-brain" / "backend"))
sys.path.insert(0, str(_HERE.parent / "chief"))      # fallback

try:
    from dotenv import load_dotenv
    load_dotenv(_HERE.parent.parent / "company-brain" / ".env")
except ImportError:
    pass


def _build_gmail_service():
    """Build authenticated Gmail API service. Returns service or raises."""
    try:
        from googleapiclient.discovery import build
        import httplib2
        from google_auth_httplib2 import AuthorizedHttp
        import gmail_auth

        creds = gmail_auth.load_credentials()
        if not creds:
            raise RuntimeError("Gmail not connected. Run: chief gmail-auth")

        http = AuthorizedHttp(creds, http=httplib2.Http(disable_ssl_certificate_validation=True))
        return build("gmail", "v1", http=http)
    except ImportError as e:
        raise RuntimeError(f"Gmail API libraries not installed: {e}")


def _build_message(to: str, subject: str, body: str) -> dict:
    """Build a raw MIME email message body."""
    msg = MIMEMultipart("alternative")
    msg["to"] = to
    msg["subject"] = subject
    plain = body.replace("<br>", "\n").replace("<p>", "\n").replace("</p>", "")
    msg.attach(MIMEText(plain, "plain"))
    msg.attach(MIMEText(body, "html"))
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    return {"raw": raw}


def create_draft(to: str, subject: str, body: str) -> dict:
    """
    Create a Gmail draft. Does NOT send. Safe to call automatically.

    Returns {"success": True, "result": "draft_id", "error": None}
    """
    try:
        service = _build_gmail_service()
        msg_body = _build_message(to, subject, body)
        draft = service.users().drafts().create(
            userId="me",
            body={"message": msg_body}
        ).execute()
        draft_id = draft.get("id", "?")
        return {
            "success": True,
            "result": f"Draft created (id={draft_id}). Review in Gmail before sending.",
            "error": None,
            "draft_id": draft_id,
        }
    except Exception as e:
        return {"success": False, "result": "", "error": str(e)}


def send_email(action_id: int, to: str, subject: str, body: str) -> dict:
    """
    Send an email. ONLY callable after action_id is APPROVED in action_queue.

    Raises PermissionError if approval record is not present.
    Returns {"success": True, "result": "gmail_message_id", "error": None}
    """
    # ── Safety gate: verify approval in DB ────────────────────────────────
    import db
    db.init()
    action = db.get_queued_action(action_id)
    if not action or action.get("status") != "approved":
        raise PermissionError(
            f"Action {action_id} is not approved. "
            "Emod must approve this action before it can be sent."
        )

    try:
        service = _build_gmail_service()
        msg_body = _build_message(to, subject, body)
        result = service.users().messages().send(
            userId="me",
            body=msg_body
        ).execute()
        gmail_id = result.get("id", "?")
        return {
            "success": True,
            "result": f"Email sent (gmail_id={gmail_id})",
            "error": None,
            "gmail_message_id": gmail_id,
        }
    except PermissionError:
        raise
    except Exception as e:
        return {"success": False, "result": "", "error": str(e)}
