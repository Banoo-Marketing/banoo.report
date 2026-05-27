"""
Gmail Reader
─────────────
Reads unread emails from the connected Gmail account.
Extracts renewal signals using Claude API.
Privacy: only snippets/metadata processed; raw body never stored > 30 days.
"""
import base64
import anthropic
import json
import gmail_auth
from config import settings

RENEWAL_KEYWORDS = [
    "renew", "renewal", "expire", "expiry", "contract end",
    "subscription", "annual", "contract renewal", "end of term",
]


def get_gmail_service():
    from googleapiclient.discovery import build
    creds = gmail_auth.load_credentials()
    if not creds:
        raise RuntimeError("Gmail not connected. Visit /auth/google to connect.")
    return build("gmail", "v1", credentials=creds)


def get_unread_emails(max_results: int = 50) -> list[dict]:
    """Fetch unread emails from the last 7 days."""
    service = get_gmail_service()

    results = service.users().messages().list(
        userId="me",
        q="is:unread newer_than:7d",
        maxResults=max_results,
    ).execute()

    messages = []
    for msg_ref in results.get("messages", []):
        try:
            full = service.users().messages().get(
                userId="me", id=msg_ref["id"], format="full"
            ).execute()

            payload = full.get("payload", {})
            headers = {h["name"]: h["value"] for h in payload.get("headers", [])}

            # Extract plain text body (first 500 chars only for privacy)
            body = ""
            if "parts" in payload:
                for part in payload["parts"]:
                    if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
                        raw = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="replace")
                        body = raw[:500]
                        break
            elif payload.get("body", {}).get("data"):
                raw = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="replace")
                body = raw[:500]

            messages.append({
                "id": msg_ref["id"],
                "from": headers.get("From", ""),
                "subject": headers.get("Subject", "(no subject)"),
                "date": headers.get("Date", ""),
                "body_preview": body,
                "snippet": full.get("snippet", ""),
            })
        except Exception as e:
            print(f"  ⚠️  Skipped message {msg_ref['id']}: {e}")

    return messages


def extract_renewal_signals(emails: list[dict]) -> list[dict]:
    """
    Filter emails with renewal keywords, then use Claude to extract structured data.
    Returns only emails with actual renewal info.
    """
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    signals = []

    for email in emails:
        text = (email["subject"] + " " + email["body_preview"]).lower()
        if not any(kw in text for kw in RENEWAL_KEYWORDS):
            continue

        prompt = f"""
Extract renewal information from this email. Return ONLY valid JSON:
{{
  "has_renewal": true or false,
  "client_name": "company or person name, or null",
  "renewal_date": "YYYY-MM-DD or null",
  "action_needed": "one sentence description or null"
}}

Email subject: {email["subject"]}
Email body: {email["body_preview"]}
""".strip()

        try:
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=200,
                messages=[{"role": "user", "content": prompt}],
            )
            signal = json.loads(response.content[0].text)
            if signal.get("has_renewal"):
                signal["email_id"] = email["id"]
                signal["from"] = email["from"]
                signal["subject"] = email["subject"]
                signals.append(signal)
        except Exception as e:
            print(f"  ⚠️  Signal extraction failed for email {email['id']}: {e}")

    return signals
