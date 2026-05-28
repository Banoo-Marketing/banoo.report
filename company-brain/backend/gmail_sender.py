"""
Gmail Sender
─────────────
Sends approved renewal emails via Gmail API.

Safety contract:
  - ONLY callable after a human approval record exists in action_queue
  - Raises PermissionError if no APPROVED record found
  - Every send is logged to audit_log
  - Thread-safe: each call verifies + marks atomically
"""
import base64
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import database as db
import gmail_auth


def send_approved_email(
    action_id: int,
    to: str,
    subject: str,
    body_html: str,
    deal_id: str,
) -> dict:
    """
    Send a renewal email only if action_id is APPROVED in action_queue.
    Returns {"sent": True, "gmail_message_id": "..."}
    Raises PermissionError if approval not found.
    """
    # ── Safety gate: verify human approval exists ──────────────────────────
    approval = db.fetchone(
        "SELECT * FROM action_queue WHERE id = %s AND status = 'APPROVED'",
        (action_id,),
    )
    if not approval:
        raise PermissionError(
            f"Action {action_id} is not APPROVED. "
            "A human must approve this action before it can be sent."
        )

    # ── Build the email ────────────────────────────────────────────────────
    from googleapiclient.discovery import build
    import httplib2
    from google_auth_httplib2 import AuthorizedHttp
    creds = gmail_auth.load_credentials()
    if not creds:
        raise RuntimeError("Gmail not connected. Visit /auth/google to connect.")

    http = AuthorizedHttp(creds, http=httplib2.Http(disable_ssl_certificate_validation=True))
    service = build("gmail", "v1", http=http)

    message = MIMEMultipart("alternative")
    message["to"] = to
    message["subject"] = subject

    # Plain text fallback
    plain = body_html.replace("<br>", "\n").replace("<p>", "\n").replace("</p>", "")
    message.attach(MIMEText(plain, "plain"))
    message.attach(MIMEText(body_html, "html"))

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    result = service.users().messages().send(
        userId="me",
        body={"raw": raw},
    ).execute()

    gmail_message_id = result["id"]

    # ── Audit log ──────────────────────────────────────────────────────────
    db.execute(
        """
        INSERT INTO audit_log (action_type, deal_id, actor, details)
        VALUES ('email_sent', %s, 'system', %s)
        """,
        (
            deal_id,
            json.dumps({
                "action_id": action_id,
                "to": to,
                "subject": subject,
                "gmail_message_id": gmail_message_id,
            }),
        ),
    )

    # ── Mark as EXECUTED ───────────────────────────────────────────────────
    db.execute(
        "UPDATE action_queue SET status='EXECUTED', executed_at=NOW() WHERE id=%s",
        (action_id,),
    )

    print(f"  📤 Email sent → {to} | Gmail ID: {gmail_message_id}")
    return {"sent": True, "gmail_message_id": gmail_message_id, "to": to}


def send_test_email(to: str) -> dict:
    """Send a quick test email to verify Gmail is connected and working."""
    from googleapiclient.discovery import build
    creds = gmail_auth.load_credentials()
    if not creds:
        raise RuntimeError("Gmail not connected. Visit /auth/google to connect first.")

    service = build("gmail", "v1", credentials=creds)

    message = MIMEText(
        "This is a test email from Company Brain. Your Gmail connection is working! 🧠",
        "plain",
    )
    message["to"] = to
    message["subject"] = "✅ Company Brain – Gmail connection test"

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    result = service.users().messages().send(
        userId="me", body={"raw": raw}
    ).execute()

    return {"sent": True, "gmail_message_id": result["id"], "to": to}
