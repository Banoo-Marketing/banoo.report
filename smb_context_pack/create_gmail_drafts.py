#!/usr/bin/env python3
"""
create_gmail_drafts.py — Push reactivation emails directly into Gmail Drafts.

SETUP (one time, ~5 minutes):
  1. Go to: console.cloud.google.com
  2. Create a new project (name it anything, e.g. "Banoo Drafts")
  3. Search "Gmail API" → Enable it
  4. Go to: APIs & Services → Credentials → Create Credentials → OAuth Client ID
  5. Application type: Desktop app → Name it anything → Create
  6. Click "Download JSON" → save as credentials.json in THIS folder
  7. Run: python create_gmail_drafts.py
  8. Visit the URL it shows → sign in as emadvafa@gmail.com → click Allow
  9. Paste the code back → drafts appear in Gmail immediately

Usage:
  python create_gmail_drafts.py
"""

import base64
import json
import os
import sys
from email.mime.text import MIMEText
from pathlib import Path

_HERE = Path(__file__).parent
CREDENTIALS_FILE = _HERE / "credentials.json"
TOKEN_FILE       = _HERE / "gmail_token.json"
SENDER           = "emadvafa@gmail.com"

SCOPES = ["https://www.googleapis.com/auth/gmail.compose"]

# ── Emails to draft ────────────────────────────────────────────────────────────

DRAFTS = [
    {
        "to":      "SKhanam@cclgroup.com",
        "subject": "CCL — your conversion domain is invisible to Google",
        "body": """Hi Sana,

Hope you're doing well.

Last time we connected I put together an SEO audit for CCL. One number has been sitting with me since:

cclprivatecapital.com — your primary conversion domain — is getting 19 visitors a month. Your awareness domain is getting 11,200.

All your SEO authority is in the wrong place. Prospects who should be finding Private Capital can't.

This isn't a 6-month fix. It's a 30-day redirect and content bridge strategy.

Worth 20 minutes this week to walk through it?

— Emod Vafa
(416) 400-4699 | cal.com/emodvafa""",
    },
    {
        "to":      "IPreda@cclgroup.com",
        "subject": "Isabella — cclprivatecapital.com has a visibility problem",
        "body": """Hi Isabella,

Hope you're well.

I did an SEO audit for CCL a while back and I wanted to reach out to you directly because this one touches your domain specifically.

cclprivatecapital.com is getting 19 organic visitors a month. Zero branded search traffic. The authority and backlinks that should be supporting Private Capital are sitting on a subdomain instead.

As the Communications lead, you're probably feeling this — content goes out, but discovery isn't happening.

I have a clear fix mapped out. Would love 20 minutes to show you what's possible.

— Emod Vafa
(416) 400-4699 | cal.com/emodvafa""",
    },
    {
        "to":      "ATate@cclgroup.com",
        "subject": "Adrian — quick follow-up on the CCL audit",
        "body": """Hi Adrian,

Hope you're doing well.

Circling back on the SEO audit I put together for CCL. The core issue — cclprivatecapital.com sitting at 19 visitors/month while your main domain pulls 11,200 — is still an open opportunity.

Have you had a chance to discuss internally? Happy to jump on a quick call if now's a better time.

— Emod Vafa
(416) 400-4699 | cal.com/emodvafa""",
    },
]


# ── Auth ───────────────────────────────────────────────────────────────────────

def get_service():
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    creds = None

    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CREDENTIALS_FILE.exists():
                print("\n  ERROR: credentials.json not found.")
                print(f"  Expected location: {CREDENTIALS_FILE}")
                print("\n  Setup steps:")
                print("  1. Go to console.cloud.google.com")
                print("  2. Create project → Enable Gmail API")
                print("  3. Credentials → OAuth Client ID → Desktop app → Download JSON")
                print(f"  4. Save as: {CREDENTIALS_FILE}")
                sys.exit(1)

            flow = InstalledAppFlow.from_client_secrets_file(
                str(CREDENTIALS_FILE), SCOPES
            )
            print("\n  Opening browser for Gmail authorization...")
            print("  Sign in as: emadvafa@gmail.com\n")
            creds = flow.run_local_server(port=0)

        TOKEN_FILE.write_text(creds.to_json())

    return build("gmail", "v1", credentials=creds)


# ── Draft creator ──────────────────────────────────────────────────────────────

def make_draft(service, to: str, subject: str, body: str) -> str:
    msg = MIMEText(body, "plain")
    msg["to"]      = to
    msg["from"]    = SENDER
    msg["subject"] = subject

    raw     = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    draft   = service.users().drafts().create(
        userId="me",
        body={"message": {"raw": raw}}
    ).execute()

    return draft["id"]


# ── Main ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n  Banoo — Gmail Draft Creator")
    print("  ─────────────────────────────")

    service = get_service()

    print(f"\n  Connected as: {SENDER}")
    print(f"  Creating {len(DRAFTS)} draft(s)...\n")

    for d in DRAFTS:
        draft_id = make_draft(service, d["to"], d["subject"], d["body"])
        print(f"  ✓ Draft created → To: {d['to']}")
        print(f"    Subject: {d['subject']}")
        print(f"    Draft ID: {draft_id}\n")

    print(f"  Done. {len(DRAFTS)} drafts are in your Gmail Drafts folder.")
    print("  Go to Gmail → Drafts → review and send.\n")
