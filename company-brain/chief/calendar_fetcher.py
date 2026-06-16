"""
calendar_fetcher.py — Fetches Google Calendar events and stores them in chief.db.
Uses the same OAuth token as Gmail.
"""
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
import db

_HERE = Path(__file__).parent
_TOKEN_FILE = _HERE.parent / ".gmail_token.json"


def _build_service():
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    import httplib2
    from google_auth_httplib2 import AuthorizedHttp

    if not _TOKEN_FILE.exists():
        raise RuntimeError("Gmail token not found. Connect Gmail first.")

    token_data = json.loads(_TOKEN_FILE.read_text())
    creds = Credentials(
        token=token_data.get("token"),
        refresh_token=token_data.get("refresh_token"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=token_data.get("client_id", ""),
        client_secret=token_data.get("client_secret", ""),
        scopes=token_data.get("scopes", []),
    )
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())

    http = AuthorizedHttp(creds, http=httplib2.Http(disable_ssl_certificate_validation=True))
    return build("calendar", "v3", http=http)


def fetch_calendar(
    days_back: int = 365,
    days_ahead: int = 90,
    verbose: bool = True,
) -> dict:
    """Fetch calendar events and store in chief.db."""
    db.init()

    try:
        service = _build_service()
    except Exception as e:
        if verbose:
            print(f"  Calendar: could not connect ({e})")
            print("  Note: Calendar requires 'calendar.readonly' OAuth scope.")
            print("  To enable: re-run OAuth with calendar scope added.")
        return {"error": str(e), "fetched": 0}

    now = datetime.now(timezone.utc)
    time_min = (now - timedelta(days=days_back)).isoformat()
    time_max = (now + timedelta(days=days_ahead)).isoformat()

    if verbose:
        print(f"Fetching calendar events ({days_back}d back, {days_ahead}d ahead)...")

    fetched = 0
    page_token = None

    while True:
        try:
            kwargs = {
                "calendarId": "primary",
                "timeMin": time_min,
                "timeMax": time_max,
                "maxResults": 250,
                "singleEvents": True,
                "orderBy": "startTime",
            }
            if page_token:
                kwargs["pageToken"] = page_token

            result = service.events().list(**kwargs).execute()
            events = result.get("items", [])

            for event in events:
                attendees = []
                for a in event.get("attendees", []):
                    attendees.append({
                        "email": a.get("email", ""),
                        "name": a.get("displayName", ""),
                        "status": a.get("responseStatus", ""),
                    })

                start = event.get("start", {})
                end = event.get("end", {})
                start_time = start.get("dateTime") or start.get("date", "")
                end_time = end.get("dateTime") or end.get("date", "")
                is_recurring = 1 if event.get("recurringEventId") else 0

                db.upsert_event({
                    "event_id": event["id"],
                    "title": event.get("summary", "(no title)"),
                    "start_time": start_time,
                    "end_time": end_time,
                    "attendees": attendees,
                    "description": event.get("description", "")[:500],
                    "location": event.get("location", ""),
                    "is_recurring": is_recurring,
                })
                fetched += 1

            page_token = result.get("nextPageToken")
            if not page_token:
                break
        except Exception as e:
            if verbose:
                print(f"\n  Calendar fetch error: {e}")
            break

    if verbose:
        print(f"Fetched {fetched} calendar events.")
    return {"fetched": fetched}
