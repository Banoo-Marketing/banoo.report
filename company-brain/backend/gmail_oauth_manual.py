"""
Manual Gmail OAuth helper for cloud/remote environments.
Run this to generate an auth URL, then paste the redirected URL back.
"""
import json
import sys
import urllib.parse
import httpx
from pathlib import Path

# Load settings
sys.path.insert(0, str(Path(__file__).parent))
from config import settings

CLIENT_ID = settings.google_client_id
CLIENT_SECRET = settings.google_client_secret
REDIRECT_URI = "http://localhost:8000/auth/google/callback"
SCOPES = "https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/gmail.send"
TOKEN_FILE = Path(__file__).parent.parent / ".gmail_token.json"


def get_auth_url():
    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": SCOPES,
        "access_type": "offline",
        "prompt": "consent",
    }
    return "https://accounts.google.com/o/oauth2/auth?" + urllib.parse.urlencode(params)


def exchange_code(code: str):
    resp = httpx.post(
        "https://oauth2.googleapis.com/token",
        data={
            "code": code,
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "redirect_uri": REDIRECT_URI,
            "grant_type": "authorization_code",
        },
    )
    resp.raise_for_status()
    data = resp.json()
    token_data = {
        "token": data["access_token"],
        "refresh_token": data.get("refresh_token"),
        "token_uri": "https://oauth2.googleapis.com/token",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "scopes": SCOPES.split(),
    }
    TOKEN_FILE.write_text(json.dumps(token_data))
    print(f"Token saved to {TOKEN_FILE}")
    return token_data


if __name__ == "__main__":
    if len(sys.argv) == 1:
        print("\n=== STEP 1: Open this URL in your browser ===\n")
        print(get_auth_url())
        print("\n=== STEP 2: After clicking Allow, copy the full URL from the browser address bar ===")
        print("=== It will start with: http://localhost:8000/auth/google/callback?code= ===")
        print("\nRun again with the code:")
        print("  python3 gmail_oauth_manual.py <CODE>")
    else:
        code = sys.argv[1]
        # Strip if they pasted full URL
        if "code=" in code:
            code = urllib.parse.parse_qs(urllib.parse.urlparse(code).query)["code"][0]
        result = exchange_code(code)
        print("Gmail connected!")
        print(f"Scopes: {result['scopes']}")
