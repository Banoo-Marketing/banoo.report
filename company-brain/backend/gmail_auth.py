"""
Gmail OAuth 2.0 – Authorization + Token Management
────────────────────────────────────────────────────
Flow:
  1. GET  /auth/google           → redirect user to Google consent screen
  2. GET  /auth/google/callback  → exchange code for tokens, store in DB
  3. All subsequent Gmail calls  → load token from DB, auto-refresh if needed

Scopes:
  - gmail.readonly  → read emails
  - gmail.send      → send approved emails only (after human approval)

Setup (Google Cloud Console):
  1. Create OAuth 2.0 credentials (Web Application)
  2. Add redirect URI: http://localhost:8000/auth/google/callback
  3. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env
"""
import json
from pathlib import Path
import database as db
from config import settings

# Lazy imports – only load google libs when a Gmail route is actually called
# (avoids cryptography version conflicts at startup)
def _import_google():
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import Flow
    return Credentials, Request, Flow

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
]

REDIRECT_URI = "http://localhost:8000/auth/google/callback"

# Token file fallback (for single-user dev mode)
_TOKEN_FILE = Path(__file__).parent.parent / ".gmail_token.json"


def get_oauth_flow():
    """Build the Google OAuth flow from env vars."""
    _, _, Flow = _import_google()
    if not settings.google_client_id or not settings.google_client_secret:
        raise RuntimeError(
            "GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET must be set in .env. "
            "Get them from console.cloud.google.com → APIs & Services → Credentials"
        )
    client_config = {
        "web": {
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [REDIRECT_URI],
        }
    }
    flow = Flow.from_client_config(client_config, scopes=SCOPES)
    flow.redirect_uri = REDIRECT_URI
    return flow


def get_auth_url() -> str:
    """Return the Google consent screen URL to redirect the user to."""
    flow = get_oauth_flow()
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    return auth_url


def exchange_code(code: str) -> dict:
    """Exchange auth code for access + refresh tokens. Returns token dict."""
    flow = get_oauth_flow()
    flow.fetch_token(code=code)
    creds = flow.credentials
    token_data = {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": list(creds.scopes) if creds.scopes else SCOPES,
    }
    _TOKEN_FILE.write_text(json.dumps(token_data))
    print(f"✅ Gmail token stored → {_TOKEN_FILE}")
    return token_data


def load_credentials():
    """Load + auto-refresh credentials. Returns None if not connected."""
    Credentials, Request, _ = _import_google()
    if not _TOKEN_FILE.exists():
        return None
    token_data = json.loads(_TOKEN_FILE.read_text())
    creds = Credentials(
        token=token_data.get("token"),
        refresh_token=token_data.get("refresh_token"),
        token_uri=token_data.get("token_uri", "https://oauth2.googleapis.com/token"),
        client_id=token_data.get("client_id", settings.google_client_id),
        client_secret=token_data.get("client_secret", settings.google_client_secret),
        scopes=token_data.get("scopes", SCOPES),
    )
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        token_data["token"] = creds.token
        _TOKEN_FILE.write_text(json.dumps(token_data))
    return creds


def is_connected() -> bool:
    """Return True if valid Gmail credentials exist."""
    try:
        creds = load_credentials()
        return creds is not None and (not creds.expired or creds.refresh_token)
    except Exception:
        return False
