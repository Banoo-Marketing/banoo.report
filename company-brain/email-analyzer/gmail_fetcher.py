"""
gmail_fetcher.py — Fetches emails from Gmail API with pagination, batching,
                   rate-limit handling, and exponential backoff.

Reads up to LOOKBACK_DAYS of email history (default 10 years).
All results are cached in SQLite so re-runs are instant.
"""
import base64
import time
import json
import re
from datetime import datetime, timezone, timedelta
from email import policy
from email.parser import BytesParser
import config
import cache

# Gmail API quota: 250 units/user/second. messages.list = 5 units, get = 5 units.
# We stay safely under by sleeping between batches.
_RATE_SLEEP = 0.1   # seconds between API calls
_BACKOFF_BASE = 2   # exponential backoff base


def _build_service():
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    import httplib2
    from google_auth_httplib2 import AuthorizedHttp

    if not config.TOKEN_FILE.exists():
        raise RuntimeError(
            "Gmail token not found. Run the Company Brain OAuth flow first:\n"
            "  GET http://localhost:8000/auth/google"
        )

    token_data = json.loads(config.TOKEN_FILE.read_text())
    creds = Credentials(
        token=token_data.get("token"),
        refresh_token=token_data.get("refresh_token"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=config.GOOGLE_CLIENT_ID,
        client_secret=config.GOOGLE_CLIENT_SECRET,
        scopes=token_data.get("scopes", []),
    )
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        token_data["token"] = creds.token
        config.TOKEN_FILE.write_text(json.dumps(token_data))

    http = AuthorizedHttp(creds, http=httplib2.Http(disable_ssl_certificate_validation=True))
    return build("gmail", "v1", http=http)


def _with_backoff(fn, max_retries: int = 5):
    """Call fn() with exponential backoff on transient errors."""
    for attempt in range(max_retries):
        try:
            return fn()
        except Exception as e:
            msg = str(e)
            if "429" in msg or "rateLimitExceeded" in msg or "userRateLimitExceeded" in msg:
                wait = (_BACKOFF_BASE ** attempt) + 1
                print(f"  Rate limited. Waiting {wait}s (attempt {attempt+1}/{max_retries})...")
                time.sleep(wait)
            elif "500" in msg or "503" in msg:
                wait = _BACKOFF_BASE ** attempt
                print(f"  Server error. Waiting {wait}s...")
                time.sleep(wait)
            else:
                raise
    raise RuntimeError(f"Failed after {max_retries} retries")


def _extract_body(payload: dict) -> str:
    """Recursively extract plain-text body from a Gmail message payload."""
    mime_type = payload.get("mimeType", "")
    body_data = payload.get("body", {}).get("data", "")

    if mime_type == "text/plain" and body_data:
        raw = base64.urlsafe_b64decode(body_data + "==").decode("utf-8", errors="replace")
        return raw[:3000]  # cap at 3k chars

    if "parts" in payload:
        # Try text/plain first
        for part in payload["parts"]:
            if part.get("mimeType") == "text/plain":
                result = _extract_body(part)
                if result:
                    return result
        # Fallback to any part
        for part in payload["parts"]:
            result = _extract_body(part)
            if result:
                return result

    # Last resort: strip HTML tags
    if mime_type == "text/html" and body_data:
        raw = base64.urlsafe_b64decode(body_data + "==").decode("utf-8", errors="replace")
        text = re.sub(r"<[^>]+>", " ", raw)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:3000]

    return ""


def _parse_message(msg: dict) -> dict:
    """Parse a raw Gmail API message into a clean dict."""
    payload = msg.get("payload", {})
    headers = {h["name"].lower(): h["value"] for h in payload.get("headers", [])}

    # Parse date
    date_str = headers.get("date", "")
    date_ts = 0
    try:
        from email.utils import parsedate_to_datetime
        dt = parsedate_to_datetime(date_str)
        date_ts = int(dt.timestamp())
    except Exception:
        try:
            date_ts = int(msg.get("internalDate", 0)) // 1000
            date_str = datetime.fromtimestamp(date_ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        except Exception:
            pass

    # Recipients
    to_raw = headers.get("to", "")
    cc_raw = headers.get("cc", "")
    recipients = [r.strip() for r in re.split(r"[,;]", to_raw + "," + cc_raw) if r.strip()]

    return {
        "gmail_id":   msg["id"],
        "thread_id":  msg.get("threadId", ""),
        "sender":     headers.get("from", ""),
        "recipients": recipients[:10],  # cap
        "subject":    headers.get("subject", "(no subject)"),
        "date_ts":    date_ts,
        "date_str":   date_str,
        "body_text":  _extract_body(payload),
        "labels":     msg.get("labelIds", []),
        "snippet":    msg.get("snippet", ""),
    }


def fetch_emails(
    max_emails: int = 0,
    lookback_days: int = None,
    verbose: bool = True,
) -> dict:
    """
    Fetch emails from Gmail and store in cache.
    Skips emails already in cache (incremental).

    Returns: {"fetched": N, "skipped": N, "total_cached": N}
    """
    if lookback_days is None:
        lookback_days = config.LOOKBACK_DAYS

    cache.init()
    service = _build_service()

    since_date = (datetime.now(timezone.utc) - timedelta(days=lookback_days)).strftime("%Y/%m/%d")
    query = f"after:{since_date}"

    if verbose:
        print(f"Fetching emails since {since_date} (last {lookback_days} days)...")

    fetched = 0
    skipped = 0
    page_token = None
    page = 0

    while True:
        page += 1
        if verbose:
            print(f"  Page {page} — fetched {fetched}, skipped {skipped}", end="\r")

        # List message IDs
        def _list():
            kwargs = {"userId": "me", "q": query, "maxResults": 500}
            if page_token:
                kwargs["pageToken"] = page_token
            return service.users().messages().list(**kwargs).execute()

        result = _with_backoff(_list)
        messages = result.get("messages", [])

        if not messages:
            break

        # Filter to only IDs we haven't cached yet
        new_ids = [m["id"] for m in messages if not cache.email_exists(m["id"])]
        skipped += len(messages) - len(new_ids)

        # Batch-fetch full message details (100 at a time)
        for i in range(0, len(new_ids), 100):
            batch_ids = new_ids[i : i + 100]

            def _batch_get(ids):
                items = []
                for msg_id in ids:
                    def _get(mid=msg_id):
                        return service.users().messages().get(
                            userId="me", id=mid, format="full"
                        ).execute()
                    try:
                        items.append(_with_backoff(_get))
                        time.sleep(_RATE_SLEEP)
                    except Exception as e:
                        print(f"\n  Warning: failed to fetch {mid}: {e}")
                return items

            raw_msgs = _batch_get(batch_ids)
            for raw in raw_msgs:
                parsed = _parse_message(raw)
                cache.save_email(parsed)
                fetched += 1

            if max_emails and fetched >= max_emails:
                break

        if max_emails and fetched >= max_emails:
            if verbose:
                print(f"\n  Reached max_emails={max_emails} limit.")
            break

        page_token = result.get("nextPageToken")
        if not page_token:
            break

        time.sleep(_RATE_SLEEP)

    st = cache.stats()
    if verbose:
        print(f"\nDone. Fetched {fetched} new, skipped {skipped} already cached.")
        print(f"Cache totals: {st['total']} emails ({st['oldest']} → {st['newest']})")

    return {"fetched": fetched, "skipped": skipped, "total_cached": st["total"]}
