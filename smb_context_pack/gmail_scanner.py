#!/usr/bin/env python3
"""
gmail_scanner.py — Find missed opportunities in your Gmail inbox.

Scans for:
  - Prospects waiting for a response
  - Old clients you haven't replied to
  - Opportunity signals (interested, proposal, quote, budget, etc.)

Outputs:
  - Prioritized list of missed opportunities
  - Draft reply message for each one

Setup (one time — 5 minutes):
  1. Go to myaccount.google.com/security
  2. Enable 2-Step Verification (if not already on)
  3. Search "App passwords" in your Google account settings
  4. Create a new app password → select "Mail"
  5. Copy the 16-character password

Usage:
  python gmail_scanner.py                    # prompts for credentials
  python gmail_scanner.py --days 60          # look back 60 days (default: 90)
  python gmail_scanner.py --save             # also log findings to memory entries

  Or set env vars to skip the prompt:
    GMAIL_ADDRESS=emadvafa@gmail.com
    GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
"""
import imaplib
import email
import email.header
import email.utils
import datetime
import getpass
import json
import os
import re
import sys
import textwrap
from pathlib import Path

# ── Config ─────────────────────────────────────────────────────────────────────

IMAP_HOST      = "imap.gmail.com"
IMAP_PORT      = 993
DEFAULT_DAYS   = 90
OWNER_EMAIL    = os.environ.get("GMAIL_ADDRESS", "emadvafa@gmail.com")

_HERE          = Path(__file__).parent
_PROFILE       = _HERE / "company_profile" / "clients.json"
_MEMORY        = _HERE / "memory" / "entries"

# ── Known entities — loaded from context pack ──────────────────────────────────

def _load_known_entities() -> dict:
    """Returns {keyword: (display_name, entity_type)} from clients.json."""
    known = {}
    if not _PROFILE.exists():
        return known
    try:
        data = json.loads(_PROFILE.read_text())
        for c in data.get("active", []):
            name = c.get("name", "")
            for word in name.lower().split():
                if len(word) > 3:
                    known[word] = (name, "client")
        for l in data.get("warm_leads", []):
            name = l.get("name", "")
            for word in name.lower().split():
                if len(word) > 3:
                    known[word] = (name, "lead")
    except Exception:
        pass
    return known


OPPORTUNITY_KEYWORDS = [
    "interested", "proposal", "quote", "follow up", "followup",
    "let's talk", "let me know", "available", "schedule a call",
    "next steps", "moving forward", "retainer", "budget", "pricing",
    "how much", "can you help", "when can we", "ready to", "sign",
    "contract", "seo", "google ads", "meta ads", "website", "marketing",
    "campaign", "leads", "paid ads",
]

# ── IMAP helpers ───────────────────────────────────────────────────────────────

def _connect(address: str, app_password: str) -> imaplib.IMAP4_SSL:
    conn = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
    conn.login(address, app_password)
    return conn


def _decode_header(raw) -> str:
    parts = email.header.decode_header(raw or "")
    result = []
    for part, enc in parts:
        if isinstance(part, bytes):
            result.append(part.decode(enc or "utf-8", errors="replace"))
        else:
            result.append(str(part))
    return " ".join(result).strip()


def _parse_date(msg) -> datetime.datetime:
    date_str = msg.get("Date", "")
    try:
        return email.utils.parsedate_to_datetime(date_str)
    except Exception:
        return datetime.datetime.now(datetime.timezone.utc)


def _sender_email(msg) -> str:
    raw = msg.get("From", "")
    _, addr = email.utils.parseaddr(raw)
    return addr.lower().strip()


def _sender_name(msg) -> str:
    raw = msg.get("From", "")
    name, addr = email.utils.parseaddr(raw)
    return (name or addr).strip()


def _get_body(msg) -> str:
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            cd = str(part.get("Content-Disposition", ""))
            if ct == "text/plain" and "attachment" not in cd:
                try:
                    body = part.get_payload(decode=True).decode(
                        part.get_content_charset() or "utf-8", errors="replace"
                    )
                    break
                except Exception:
                    pass
    else:
        try:
            body = msg.get_payload(decode=True).decode(
                msg.get_content_charset() or "utf-8", errors="replace"
            )
        except Exception:
            pass
    return body[:2000]


# ── Opportunity classifier ─────────────────────────────────────────────────────

def _classify(subject: str, body: str, sender: str,
               known_entities: dict) -> tuple[str, str, str]:
    """
    Returns (priority, entity_name, reason).
    priority: "HIGH" | "MEDIUM" | "LOW"
    """
    text = (subject + " " + body + " " + sender).lower()

    # Check against known clients and leads
    for keyword, (name, etype) in known_entities.items():
        if keyword in text:
            label = "CLIENT" if etype == "client" else "LEAD"
            return "HIGH", name, f"Known {label.lower()} — {name}"

    # Check for opportunity keywords
    matched = [kw for kw in OPPORTUNITY_KEYWORDS if kw in text]
    if len(matched) >= 2:
        return "MEDIUM", "", f"Opportunity signals: {', '.join(matched[:3])}"
    if matched:
        return "MEDIUM", "", f"Signal: {matched[0]}"

    return "LOW", "", "No clear signal"


# ── Draft reply generator ──────────────────────────────────────────────────────

def _draft_reply(sender_name: str, subject: str, body: str,
                 entity: str, priority: str, days_ago: int) -> str:
    name = (entity or sender_name or "there").split()[0]
    subj_clean = re.sub(r'^(re|fwd?):\s*', '', subject, flags=re.IGNORECASE).strip()

    if "proposal" in subject.lower() or "proposal" in body.lower():
        return (
            f"Hi {name},\n\n"
            f"Just following up on the proposal I sent over. "
            f"Happy to jump on a quick 15-min call to walk you through it and answer any questions.\n\n"
            f"What does your schedule look like this week?\n\n"
            f"— Emod"
        )

    if any(w in body.lower() for w in ["interested", "can you help", "how much", "pricing", "cost"]):
        return (
            f"Hi {name},\n\n"
            f"Thanks for reaching out. Yes, we can help with that.\n\n"
            f"Let me know a good time for a quick 15-min call and I'll walk you through exactly "
            f"what we'd do for your business and what it costs.\n\n"
            f"— Emod, Banoo Marketing"
        )

    if days_ago > 30:
        return (
            f"Hi {name},\n\n"
            f"Checking in — it's been a little while since we last connected. "
            f"Still thinking about {subj_clean or 'what we discussed'}?\n\n"
            f"Happy to reconnect whenever the timing works for you.\n\n"
            f"— Emod"
        )

    return (
        f"Hi {name},\n\n"
        f"Apologies for the slow reply on {subj_clean or 'this'}. "
        f"Still very much interested — can we find 15 minutes this week?\n\n"
        f"— Emod, Banoo Marketing"
    )


# ── Scanner ────────────────────────────────────────────────────────────────────

def scan(conn: imaplib.IMAP4_SSL, days: int = DEFAULT_DAYS) -> list[dict]:
    conn.select("INBOX")

    since = (datetime.datetime.now() - datetime.timedelta(days=days)).strftime("%d-%b-%Y")
    _, data = conn.search(None, f'(SINCE "{since}")')
    ids = data[0].split()

    known_entities = _load_known_entities()
    results = []
    owner = OWNER_EMAIL.lower()

    for uid in ids:
        try:
            _, raw = conn.fetch(uid, "(RFC822)")
            msg = email.message_from_bytes(raw[0][1])
        except Exception:
            continue

        sender = _sender_email(msg)

        # Skip emails I sent
        if owner in sender:
            continue

        # Skip newsletters and no-reply
        if any(x in sender for x in ["noreply", "no-reply", "newsletter",
                                       "unsubscribe", "notifications@", "donotreply",
                                       "mailer-daemon", "postmaster", "support@"]):
            continue

        subject  = _decode_header(msg.get("Subject", "(no subject)"))
        body     = _get_body(msg)
        date     = _parse_date(msg)
        now      = datetime.datetime.now(datetime.timezone.utc)
        days_ago = max(0, (now - date).days)

        priority, entity, reason = _classify(subject, body, sender, known_entities)

        results.append({
            "uid":          uid.decode(),
            "sender_name":  _sender_name(msg),
            "sender_email": sender,
            "subject":      subject,
            "date":         date.strftime("%Y-%m-%d"),
            "days_ago":     days_ago,
            "priority":     priority,
            "entity":       entity,
            "reason":       reason,
            "draft":        _draft_reply(_sender_name(msg), subject, body,
                                         entity, priority, days_ago),
        })

    # Sort: HIGH → MEDIUM → LOW, then oldest first within each group
    order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    results.sort(key=lambda x: (order[x["priority"]], x["days_ago"]), reverse=False)
    results.sort(key=lambda x: order[x["priority"]])

    return results


# ── Output formatter ───────────────────────────────────────────────────────────

def _print_results(results: list[dict], days: int):
    high   = [r for r in results if r["priority"] == "HIGH"]
    medium = [r for r in results if r["priority"] == "MEDIUM"]

    total = len(high) + len(medium)
    print(f"\n{'=' * 60}")
    print(f"  GMAIL OPPORTUNITY SCAN — Banoo Inc")
    print(f"  Scanned: last {days} days  |  Actionable: {total} found")
    print(f"{'=' * 60}")

    def _print_block(items: list[dict], label: str):
        if not items:
            return
        print(f"\n── {label} {'─' * (50 - len(label))}")
        for i, r in enumerate(items, 1):
            entity_tag = f" [{r['entity']}]" if r["entity"] else ""
            print(f"\n  {i}. {r['sender_name']}{entity_tag}")
            print(f"     Subject  : {r['subject'][:70]}")
            print(f"     Received : {r['date']} ({r['days_ago']} days ago)")
            print(f"     Reason   : {r['reason']}")
            print(f"\n     DRAFT REPLY:")
            for line in r["draft"].split("\n"):
                print(f"     {line}")
            print(f"     {'─' * 50}")

    _print_block(high,   "HIGH PRIORITY — Known clients & leads")
    _print_block(medium, "MEDIUM PRIORITY — Opportunity signals")

    if not high and not medium:
        print("\n  ✓ No missed opportunities found in the last", days, "days.")
        low = [r for r in results if r["priority"] == "LOW"]
        print(f"  ({len(low)} low-priority emails skipped)")

    print(f"\n{'=' * 60}\n")


# ── Memory logger (optional) ───────────────────────────────────────────────────

def _save_to_memory(results: list[dict]):
    import uuid
    _MEMORY.mkdir(parents=True, exist_ok=True)
    saved = 0
    for r in results:
        if r["priority"] not in ("HIGH", "MEDIUM"):
            continue
        now  = datetime.datetime.utcnow()
        name = (r["entity"] or r["sender_name"]).lower()
        name = re.sub(r'[^a-z0-9]', '_', name)[:20]
        fname = now.strftime(f"%Y%m%d_%H%M%S_") + str(uuid.uuid4()).replace("-","")[:6] + f"_{name}.json"
        entry = {
            "timestamp": now.isoformat() + "+00:00",
            "type":      "gmail_scan",
            "entity":    r["entity"] or r["sender_name"],
            "content":   f"Unanswered email — '{r['subject'][:80]}' ({r['days_ago']} days ago). Priority: {r['priority']}.",
            "source":    "gmail_scanner",
        }
        (_MEMORY / fname).write_text(json.dumps(entry, indent=2))
        saved += 1
    print(f"  → {saved} opportunities saved to memory entries.")


# ── CLI ────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    args = sys.argv[1:]

    days      = DEFAULT_DAYS
    save_mem  = "--save" in args

    for i, a in enumerate(args):
        if a == "--days" and i + 1 < len(args):
            try:
                days = int(args[i + 1])
            except ValueError:
                pass

    # Credentials
    address      = os.environ.get("GMAIL_ADDRESS", OWNER_EMAIL)
    app_password = os.environ.get("GMAIL_APP_PASSWORD", "")

    if not app_password:
        print("\n  Gmail App Password required.")
        print("  (Google Account → Security → App passwords → Mail)")
        print(f"  Account: {address}\n")
        app_password = getpass.getpass("  App password: ")

    print(f"\n  Connecting to Gmail ({address})...")

    try:
        conn = _connect(address, app_password)
        print(f"  Connected. Scanning last {days} days...\n")
    except imaplib.IMAP4.error as e:
        print(f"\n  Connection failed: {e}")
        print("  Check your app password and try again.")
        sys.exit(1)

    try:
        results = scan(conn, days=days)
    finally:
        try:
            conn.logout()
        except Exception:
            pass

    _print_results(results, days)

    if save_mem and results:
        _save_to_memory(results)
