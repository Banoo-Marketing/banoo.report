#!/usr/bin/env python3
"""
create_gmail_drafts.py — Push outreach emails directly into Gmail Drafts.

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

    # ── CCL Financial Group (reactivation) ────────────────────────────────────
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

    # ── Toronto Law Firms — Cold Outreach (PPC) ───────────────────────────────
    {
        "to":      "alex@karapancevlaw.ca",
        "subject": "Alex — congrats on Best Criminal Lawyer. One question.",
        "body": """Hi Alex,

Congratulations on the 2025 Toronto Star Readers' Choice win — Diamond Winner for Best Criminal Lawyer is a big deal.

Here's the question: when someone searches "DUI lawyer Toronto" at midnight, are you the first result they see?

Your reputation is earned. But urgent criminal searches happen 24/7, and the top of Google is decided by paid search — not reputation alone.

I managed Google Ads for Diamond & Diamond — one of Toronto's highest-volume legal advertisers. I know what it takes to convert those late-night searches into booked consultations.

Worth 15 minutes to show you what's possible?

— Emod Vafa
(416) 400-4699 | cal.com/emodvafa""",
    },
    {
        "to":      "info@grillo.ca",
        "subject": "Sal — Diamond & Diamond outspends you. You outperform them.",
        "body": """Hi Sal,

35 years. 15,000+ claims. $300M+ recovered.

Diamond & Diamond spends $50,000+ a month on Google Ads. You don't need their budget — you need smarter targeting that puts Grillo Law in front of the right people at the right time.

I personally managed PPC for Diamond & Diamond and Preszler Law — two of Toronto's largest legal advertisers. I know exactly how they dominate search, and I know the gaps they leave open for a firm like yours.

Happy to put together a quick competitive audit — no cost, no obligation.

20 minutes this week?

— Emod Vafa
(416) 400-4699 | cal.com/emodvafa""",
    },
    {
        "to":      "info@schiffmannlaw.ca",
        "subject": "Chris — personal injury CPCs in Toronto are $50–$100. Are you winning?",
        "body": """Hi Chris,

"Personal injury lawyer Toronto" costs $50–$100 per click on Google Ads.

Most boutique firms either overpay without a strategy, or sit it out entirely — and lose page-one visibility to the firms spending six figures a month.

There's a third option: targeted campaigns built around the cases you actually want, at a budget that makes sense for a boutique practice.

I ran legal PPC for Diamond & Diamond and Preszler Law. I know how to make this work without the big-firm budget.

Would you be open to a quick call this week?

— Emod Vafa
(416) 400-4699 | cal.com/emodvafa""",
    },
    {
        "to":      "info@sokoloff.ca",
        "subject": "Wendy — you added a partner in January. Let's fill that pipeline.",
        "body": """Hi Wendy,

Congratulations on the partnership expansion — Stanley joining officially in January is a growth signal worth acting on.

More partners means more capacity. The question is whether your lead flow keeps pace.

Personal injury is one of the highest-intent practice areas on Google. When someone searches at 11pm after an accident, paid search is what puts you in front of them — not word of mouth.

I managed PPC for Diamond & Diamond and Preszler Law. Happy to put together a quick view of what a targeted campaign would look like for Sokoloff specifically.

Worth 20 minutes?

— Emod Vafa
(416) 400-4699 | cal.com/emodvafa""",
    },
    {
        "to":      "info@longolawyers.ca",
        "subject": "Fabio — Lexpert named you a Leading Firm. Does Google know that?",
        "body": """Hi Fabio,

Lexpert recognizing Longo Lawyers as a Leading Firm in 2026 is well-deserved.

Here's the gap: Lexpert recognition builds credibility with peers. Google Ads builds visibility with clients — the people searching "car accident lawyer Toronto" right now.

Those two need to work together.

I ran paid search for Diamond & Diamond and Preszler Law — two of the most searched personal injury brands in Ontario. Happy to show you what a Longo campaign would look like.

15 minutes?

— Emod Vafa
(416) 400-4699 | cal.com/emodvafa""",
    },
    {
        "to":      "info@kainfamilylaw.com",
        "subject": "Your free 30-minute consultation is a perfect Google Ads offer",
        "body": """Hi,

I came across Kain & Ball while researching Toronto family law firms — Bay Street address, strong positioning, free 30-minute consultation offer.

That consultation offer is exactly what converts in a Google Ads campaign. Most family law firms bury it. You lead with it.

The problem is: divorce lawyers are paying $30–$70 per click in Toronto, and without a well-managed campaign, most of that spend goes to waste.

I managed paid search for some of Toronto's highest-volume legal advertisers, including Diamond & Diamond and Preszler Law.

Would someone on your team be open to a quick conversation about what a targeted campaign could look like for Kain & Ball?

— Emod Vafa
(416) 400-4699 | cal.com/emodvafa""",
    },
    {
        "to":      "info@omulique.ca",
        "subject": "Quick question about your Google Ads",
        "body": """Hi,

I was looking at Toronto immigration law search terms and noticed that "immigration lawyer Toronto free consultation" gets searched over 1,000 times a month.

Omulique's positioning — affordable, accessible immigration law — is exactly what converts on Google Ads. The question is whether you're capturing those searches right now.

I've run paid search for legal clients in Toronto and know how to target immigration keywords efficiently without a large budget.

Would you be open to a 15-minute call to see what's possible?

— Emod Vafa
(416) 400-4699 | cal.com/emodvafa""",
    },
    {
        "to":      "toronto@dekrupelaw.ca",
        "subject": "De Krupe — your weekend availability is a closing argument in an ad",
        "body": """Hi,

I noticed De Krupe Law offers after-hours and weekend appointments — something almost no other Toronto real estate firm advertises.

That's a genuinely strong differentiator, especially when buyers are closing on tight timelines and searching at 9pm on a Saturday.

The problem is: most people searching "real estate lawyer Toronto" never see that offer because it's buried on your website rather than leading your Google Ads.

I run paid search campaigns for professional services firms in Toronto. Happy to show you what a campaign built around that hook would look like — no commitment, just a quick look.

— Emod Vafa
(416) 400-4699 | cal.com/emodvafa""",
    },
    {
        "to":      "info@alexhulaw.ca",
        "subject": "Alex — one Google Ads client covers your entire monthly campaign",
        "body": """Hi Alex,

A real estate closing in Toronto pays $1,500–$2,500 in legal fees.

A well-run Google Ads campaign for a solo real estate lawyer in Toronto typically costs $800–$1,500/month. Two extra closings a month — which is realistic with targeted paid search — and the campaign pays for itself four times over.

I run PPC for professional services firms in Toronto and I've seen this math work for boutique law practices specifically.

Would you be open to a quick call to see if it makes sense for your practice?

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
