#!/usr/bin/env python3
"""
Atlas — Chief of Staff to Emod Vafa
Your AI right hand. Knows your world, acts in your name, never without your approval.

Usage:
  atlas brief              Morning brief (what matters today)
  atlas email draft        Draft replies to emails awaiting response
  atlas email read [n]     Summarise your last n unread emails
  atlas ask "question"     Answer anything about your world
  atlas hire "role"        Draft a job description for a new hire
  atlas status             Full system status
  atlas who "name"         Look up a contact instantly
"""
import sys
import json
import yaml
from pathlib import Path
from datetime import datetime, timezone

_HERE = Path(__file__).parent
_CHIEF = _HERE.parent / "chief"
sys.path.insert(0, str(_CHIEF))
sys.path.insert(0, str(_HERE))

try:
    from dotenv import load_dotenv
    load_dotenv(_HERE.parent.parent / "company-brain" / ".env")
    load_dotenv(_HERE.parent / ".env")
except ImportError:
    pass

import anthropic

# Load Atlas identity
with open(_HERE / "identity.yaml") as f:
    IDENTITY = yaml.safe_load(f)

ATLAS_SYSTEM = f"""You are Atlas, Chief of Staff to Emod Vafa.

{yaml.dump(IDENTITY['persona'], default_flow_style=False)}

You know everything about Emod's world:
- Runs Banoo Marketing (digital marketing agency in Toronto)
- Licensed REALTOR® with Forest Hill Real Estate
- Board member at Dance Ontario
- Married to Sahar Ansari, son Dario
- Persian/Iranian heritage, currently in Iran using VPN (Frankfurt exit node — not a security issue)
- Active in Sufi Heart Circle, Rumi study group, Vipassana community
- Investors in VEGAIN Nutrition, manages multiple referral partnerships
- Actively job hunting while running Banoo

Your rules:
- NEVER act without Emod's approval on consequential matters
- Always draft first, present for approval, then execute
- Be direct, warm when appropriate, never verbose
- Sign off as Atlas when acting as CoS, as Emod when drafting in his voice
- Prioritise: Family → Active clients → Financial deadlines → Job pipeline → Real estate → Partners → Community

Today is {datetime.now(timezone.utc).strftime('%A, %B %d %Y')}.
"""


def _client():
    return anthropic.Anthropic()


def _chief_context() -> dict:
    """Pull live context from chief.db."""
    import db
    db.init()
    contacts = db.get_top_contacts(n=30)
    actions = db.get_actions(status="OPEN", priority="HIGH", limit=10)
    events = db.get_upcoming_events(days=7)
    st = db.stats()
    return {
        "stats": st,
        "top_contacts": contacts,
        "urgent_actions": actions,
        "upcoming_events": events,
    }


def cmd_brief():
    """Morning brief — what Atlas thinks matters most today."""
    import daily_brief
    print(f"\n  ┌{'─'*61}┐")
    print(f"  │  ATLAS — CHIEF OF STAFF                                   │")
    print(f"  │  Briefing for Emod Vafa · {datetime.now().strftime('%a %b %d %Y'):33s}│")
    print(f"  └{'─'*61}┘\n")
    brief = daily_brief.generate_brief(verbose=False)
    daily_brief.print_brief(brief)


def cmd_ask(question: str):
    """Answer any question about Emod's world using live data."""
    ctx = _chief_context()
    client = _client()
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=ATLAS_SYSTEM,
        messages=[{
            "role": "user",
            "content": f"Live data from Emod's systems:\n{json.dumps(ctx, indent=2, default=str)}\n\nQuestion: {question}"
        }],
    )
    print(f"\n  Atlas: {resp.content[0].text}\n")


def cmd_who(name_or_email: str):
    """Instant contact lookup."""
    import db, sqlite3
    with sqlite3.connect(db.DB_PATH) as c:
        c.row_factory = sqlite3.Row
        rows = c.execute("""
            SELECT * FROM contacts
            WHERE lower(email) LIKE ? OR lower(name) LIKE ?
            ORDER BY strength DESC LIMIT 3
        """, (f"%{name_or_email.lower()}%", f"%{name_or_email.lower()}%")).fetchall()

    if not rows:
        print(f"\n  Atlas: No contact found matching '{name_or_email}'.\n")
        return

    for r in rows:
        d = dict(r)
        print(f"\n  ┌── {d.get('name') or d['email']} ──")
        print(f"  │  Email      : {d['email']}")
        if d.get('company'):   print(f"  │  Company    : {d['company']}")
        if d.get('role'):      print(f"  │  Role       : {d['role']}")
        print(f"  │  Rel        : {d.get('relationship','?')} | Strength {d.get('strength',0):.1f}/10")
        if d.get('how_we_met'): print(f"  │  Context    : {d['how_we_met'][:90]}")
        if d.get('suggested_action'): print(f"  │  Next step  : {d['suggested_action'][:90]}")
        print(f"  └──")


def cmd_email_read(n: int = 10):
    """Summarise recent unread emails with Atlas commentary."""
    import db, sqlite3
    email_db = _CHIEF.parent / "email-analyzer" / "email_cache.db"
    if not email_db.exists():
        print("  Atlas: No email cache found. Run chief sync first.")
        return

    with sqlite3.connect(email_db) as c:
        c.row_factory = sqlite3.Row
        rows = c.execute("""
            SELECT sender, subject, date_str, body_text
            FROM emails ORDER BY date_ts DESC LIMIT ?
        """, (n,)).fetchall()

    emails = [dict(r) for r in rows]
    client = _client()
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=ATLAS_SYSTEM,
        messages=[{
            "role": "user",
            "content": f"""Summarise these {n} recent emails for Emod.
For each, note: who it's from, what they want, and whether it needs action.
Flag anything urgent. Be concise — one line per email unless it's important.

Emails:
{json.dumps(emails, indent=2, default=str)}"""
        }],
    )
    print(f"\n  Atlas: Recent email summary\n")
    print(resp.content[0].text)
    print()


def cmd_email_draft():
    """Find emails needing a reply and draft responses for Emod's approval."""
    import db, sqlite3
    email_db = _CHIEF.parent / "email-analyzer" / "email_cache.db"
    if not email_db.exists():
        print("  Atlas: No email cache found.")
        return

    # Get recent emails from real people (not automated senders)
    with sqlite3.connect(email_db) as c:
        c.row_factory = sqlite3.Row
        rows = c.execute("""
            SELECT sender, subject, date_str, body_text
            FROM emails
            WHERE sender NOT LIKE '%noreply%'
              AND sender NOT LIKE '%no-reply%'
              AND sender NOT LIKE '%notification%'
              AND sender NOT LIKE '%calendar-notification%'
              AND sender NOT LIKE '%alerts%'
              AND length(body_text) > 100
            ORDER BY date_ts DESC
            LIMIT 15
        """).fetchall()

    emails = [dict(r) for r in rows]
    client = _client()
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        system=ATLAS_SYSTEM,
        messages=[{
            "role": "user",
            "content": f"""Review these recent emails and identify which ones need a reply from Emod.

For each email that needs a reply:
1. State who it's from and what they're asking
2. Draft a reply in Emod's voice (professional, direct, warm where appropriate)
3. Flag: SEND AS-IS / REVIEW FIRST / EMOD TO PERSONALISE
4. Note the appropriate signature to use

Skip automated emails, newsletters, and notifications. Focus on humans expecting a response.

Emails to review:
{json.dumps(emails, indent=2, default=str)}"""
        }],
    )
    print(f"\n  Atlas: Email drafts for your approval\n")
    print(f"  {'─'*60}")
    print(resp.content[0].text)
    print()


def cmd_hire(role: str):
    """Draft a job description and hiring plan for a new role."""
    ctx = _chief_context()
    client = _client()
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        system=ATLAS_SYSTEM,
        messages=[{
            "role": "user",
            "content": f"""Emod wants to hire for this role: "{role}"

Context about Banoo Marketing:
- Digital marketing agency in Toronto (Google Ads, SEO, DSP, lead gen)
- Small team, high output
- Clients include real estate, e-commerce, and service businesses
- Emod is the founder — this hire will work closely with him

Draft:
1. Job title and one-line pitch
2. What this person will own (3-5 bullet points)
3. Must-have qualifications (be specific, no generic fluff)
4. Nice-to-haves
5. Compensation range suggestion (Toronto market)
6. Where to post (job boards, communities)
7. First screening question to filter serious candidates

Keep it tight. Real candidates should feel excited and clear on expectations."""
        }],
    )
    print(f"\n  Atlas: Job Description — {role}\n")
    print(f"  {'─'*60}")
    print(resp.content[0].text)
    print()


def cmd_status():
    """Full Atlas + system status."""
    ctx = _chief_context()
    st = ctx["stats"]
    print(f"\n  ┌{'─'*61}┐")
    print(f"  │  ATLAS STATUS                                             │")
    print(f"  └{'─'*61}┘")
    print(f"  Serving        : Emod Vafa")
    print(f"  Contacts mapped: {st.get('contacts', 0):,}")
    print(f"  Open actions   : {st.get('actions_open', 0):,}")
    print(f"  Upcoming events: {len(ctx.get('upcoming_events', []))}")
    print(f"  Daily briefs   : {st.get('briefs', 0):,}")
    print()
    print(f"  Sub-agents available:")
    print(f"    Scout  — Talent & hiring pipeline")
    print(f"    Relay  — Email drafting & inbox")
    print(f"    Ledger — Financial tracking")
    print(f"    Broker — Real estate monitoring")
    print(f"    Pulse  — Client health")
    print()
    print(f"  All actions require Emod's approval before execution.")
    print()


def main():
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help", "help"):
        print(__doc__)
        return

    cmd = args[0]

    if cmd == "brief":
        cmd_brief()
    elif cmd == "ask":
        if len(args) < 2:
            print("Usage: atlas ask \"your question\"")
            return
        cmd_ask(args[1])
    elif cmd == "who":
        if len(args) < 2:
            print("Usage: atlas who \"name or email\"")
            return
        cmd_who(args[1])
    elif cmd == "status":
        cmd_status()
    elif cmd == "hire":
        if len(args) < 2:
            print("Usage: atlas hire \"role description\"")
            return
        cmd_hire(args[1])
    elif cmd == "email":
        sub = args[1] if len(args) > 1 else "read"
        if sub == "draft":
            cmd_email_draft()
        elif sub == "read":
            n = int(args[2]) if len(args) > 2 else 10
            cmd_email_read(n)
        else:
            print(f"Unknown email command: {sub}")
    else:
        print(f"Atlas: Unknown command '{cmd}'. Try: atlas brief | ask | who | email | hire | status")


if __name__ == "__main__":
    main()
