#!/usr/bin/env python3
"""
chief — Your AI Chief of Staff

Commands:
  chief sync              Sync emails, calendar, build relationship graph
  chief daily-brief       Generate + print your morning brief
  chief show tasks        Show open action items
  chief show tasks --urgent  Only HIGH priority tasks
  chief show contacts     Show your top contacts by relationship strength
  chief contact "Name"    Show full profile + history for a contact
  chief nurture-leads     Show business owners to nurture for Banoo
  chief reconnect         Show dormant valuable contacts to re-engage
  chief status            Show system stats
  chief ask "question"    Natural language query about your contacts/emails
"""
import sys
import json
from pathlib import Path

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))

try:
    from dotenv import load_dotenv
    load_dotenv(_HERE.parent.parent / "company-brain" / ".env")
    load_dotenv(_HERE.parent / ".env")
except ImportError:
    pass


def cmd_sync(quick: bool = False):
    import db
    db.init()

    # 1. Calendar
    print("\n[1/3] Syncing calendar...")
    try:
        import calendar_fetcher
        result = calendar_fetcher.fetch_calendar(days_back=365 if quick else 3650, days_ahead=90)
        print(f"  Calendar: {result.get('fetched', 0)} events")
    except Exception as e:
        print(f"  Calendar sync skipped: {e}")

    # 2. Relationship graph
    print("\n[2/3] Building relationship graph...")
    import relationship_builder
    result = relationship_builder.build_relationship_graph(
        min_email_count=2,
        max_contacts=50 if quick else 200,
    )
    print(f"  Relationships: {result.get('contacts_built', 0)} contacts profiled")

    # 3. Action extraction
    print("\n[3/3] Extracting action items...")
    import action_extractor
    result = action_extractor.extract_actions(max_emails=50 if quick else 200)
    print(f"  Actions: {result.get('actions_found', 0)} new action items found")

    print("\nSync complete.")
    cmd_status()


def cmd_daily_brief():
    import daily_brief
    print("Generating your daily brief...")
    brief = daily_brief.generate_brief()
    daily_brief.print_brief(brief)


def cmd_show_tasks(urgent_only: bool = False):
    import db
    priority = "HIGH" if urgent_only else None
    actions = db.get_actions(status="OPEN", priority=priority, limit=30)

    if not actions:
        print("No open action items. Run: chief sync")
        return

    label = "URGENT TASKS" if urgent_only else "OPEN ACTION ITEMS"
    print(f"\n{'='*60}")
    print(f"  {label} ({len(actions)})")
    print(f"{'='*60}")

    for a in actions:
        pri_icon = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}.get(a["priority"], "⚪")
        type_icon = {"followup": "↩", "promise": "🤝", "decision": "🤔", "task": "✓"}.get(a.get("action_type",""), "•")
        deadline = f" [by {a['deadline']}]" if a.get("deadline") else ""
        print(f"\n  {pri_icon} {type_icon} {a['title']}{deadline}")
        print(f"     From: {a.get('from_name','unknown')}")
        if a.get("suggested_next"):
            print(f"     Next: {a['suggested_next']}")


def cmd_show_contacts(relationship: str = None, limit: int = 20):
    import db
    contacts = db.get_contacts(relationship=relationship, limit=limit)

    if not contacts:
        print("No contacts yet. Run: chief sync")
        return

    title = f"CONTACTS — {relationship.upper()}" if relationship else "TOP CONTACTS BY STRENGTH"
    print(f"\n{'='*65}")
    print(f"  {title} ({len(contacts)})")
    print(f"{'='*65}")

    for c in contacts:
        strength_bar = "█" * int(c.get("strength", 0)) + "░" * (10 - int(c.get("strength", 0)))
        rel_icon = {
            "Family": "👨‍👩‍👧", "Close friend": "🤗", "Key business partner": "🤝",
            "Client (Banoo)": "💼", "Lead (business owner)": "🎯",
            "Vendor": "📦", "Mentor/Advisor": "🎓",
            "Needs rekindling": "🌱", "Acquaintance": "👋",
        }.get(c.get("relationship",""), "•")

        print(f"\n  {rel_icon} {c.get('name','') or c['email']}")
        print(f"     Email     : {c['email']}")
        if c.get("company"):
            print(f"     Company   : {c['company']}")
        print(f"     Rel       : {c.get('relationship','?')} | Strength: [{strength_bar}] {c.get('strength',0):.1f}/10")
        print(f"     Emails    : {c.get('email_count',0)} | Last: {(c.get('last_contact') or '')[:10]}")
        if c.get("suggested_action"):
            print(f"     Action    : {c['suggested_action']}")


def cmd_contact(name_or_email: str):
    import db
    import sqlite3

    # Search by email or name
    with sqlite3.connect(db.DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
        SELECT * FROM contacts
        WHERE lower(email) LIKE ? OR lower(name) LIKE ?
        ORDER BY strength DESC LIMIT 5
        """, (f"%{name_or_email.lower()}%", f"%{name_or_email.lower()}%")).fetchall()
        contacts = [dict(r) for r in rows]

    if not contacts:
        print(f"No contact found matching: {name_or_email}")
        return

    c = contacts[0]
    print(f"\n{'='*65}")
    print(f"  CONTACT PROFILE: {c.get('name','') or c['email']}")
    print(f"{'='*65}")
    print(f"  Email      : {c['email']}")
    print(f"  Company    : {c.get('company','unknown')}")
    print(f"  Role       : {c.get('role','unknown')}")
    print(f"  Rel type   : {c.get('relationship','unknown')}")
    print(f"  How we met : {c.get('how_we_met','unknown')}")
    print(f"  Strength   : {c.get('strength',0):.1f}/10 | {c.get('email_count',0)} emails")
    print(f"  First seen : {(c.get('first_contact') or '')[:10]}")
    print(f"  Last seen  : {(c.get('last_contact') or '')[:10]}")

    try:
        obligations = json.loads(c.get("obligations") or "[]")
        if obligations:
            print(f"\n  📋 OBLIGATIONS:")
            for o in obligations:
                print(f"     • {o}")
    except Exception:
        pass

    if c.get("suggested_action"):
        print(f"\n  💡 SUGGESTED ACTION:")
        print(f"     {c['suggested_action']}")

    # Show recent actions
    actions = db.get_actions(status="OPEN", limit=50)
    contact_actions = [a for a in actions if name_or_email.lower() in (a.get("from_email","") or "").lower()
                       or name_or_email.lower() in (a.get("from_name","") or "").lower()]
    if contact_actions:
        print(f"\n  🎯 OPEN ACTIONS ({len(contact_actions)}):")
        for a in contact_actions[:5]:
            print(f"     • [{a['priority']}] {a['title']}")


def cmd_nurture_leads():
    import db
    import sqlite3

    with sqlite3.connect(db.DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        leads = conn.execute("""
        SELECT * FROM contacts
        WHERE (relationship = 'Lead (business owner)' OR is_business_owner = 1)
          AND nurture_score > 0
        ORDER BY nurture_score DESC, strength DESC
        LIMIT 20
        """).fetchall()
        leads = [dict(r) for r in leads]

    if not leads:
        print("No nurture leads found. Run: chief sync")
        return

    print(f"\n{'='*65}")
    print(f"  BANOO NURTURE LEADS ({len(leads)})")
    print(f"  Business owners to target for digital marketing / lead gen")
    print(f"{'='*65}")

    for i, lead in enumerate(leads, 1):
        score_bar = "█" * int(lead.get("nurture_score",0)) + "░" * (10-int(lead.get("nurture_score",0)))
        print(f"\n  {i}. {lead.get('name','') or lead['email']}")
        print(f"     Email   : {lead['email']}")
        if lead.get("company"):
            print(f"     Company : {lead['company']}")
        if lead.get("role"):
            print(f"     Role    : {lead['role']}")
        print(f"     Score   : [{score_bar}] {lead.get('nurture_score',0):.0f}/10")
        print(f"     Last    : {(lead.get('last_contact') or '')[:10]}")
        if lead.get("nurture_notes"):
            print(f"     Why     : {lead['nurture_notes']}")
        if lead.get("suggested_action"):
            print(f"     Action  : {lead['suggested_action']}")


def cmd_reconnect():
    import db
    dormant = db.get_dormant_contacts(days=180)

    if not dormant:
        print("No dormant contacts found.")
        return

    print(f"\n{'='*65}")
    print(f"  RECONNECT LIST — Valuable contacts you've lost touch with")
    print(f"{'='*65}")

    for c in dormant[:15]:
        print(f"\n  • {c.get('name','') or c['email']}")
        print(f"    Email   : {c['email']}")
        print(f"    Rel     : {c.get('relationship','?')} | Strength: {c.get('strength',0):.1f}/10")
        print(f"    Last    : {(c.get('last_contact') or 'unknown')[:10]} ({c.get('email_count',0)} emails total)")
        if c.get("how_we_met"):
            print(f"    Context : {c['how_we_met']}")
        if c.get("suggested_action"):
            print(f"    Action  : {c['suggested_action']}")


def cmd_ask(question: str):
    """Natural language query answered by Claude using your contact + action data."""
    import db
    import anthropic

    contacts = db.get_top_contacts(n=50)
    actions = db.get_actions(status="OPEN", limit=30)

    context = {
        "contacts": [{
            "name": c.get("name",""), "email": c["email"],
            "company": c.get("company",""), "relationship": c.get("relationship",""),
            "strength": c.get("strength",0), "last_contact": c.get("last_contact",""),
            "how_we_met": c.get("how_we_met",""),
        } for c in contacts],
        "open_actions": [{
            "title": a["title"], "from": a.get("from_name",""),
            "priority": a["priority"], "deadline": a.get("deadline",""),
        } for a in actions],
    }

    client = anthropic.Anthropic()
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        system="You are a Chief of Staff AI assistant. Answer questions about the user's contacts, relationships, and pending actions using the provided data. Be concise and actionable.",
        messages=[{"role": "user", "content": f"Data:\n{json.dumps(context)}\n\nQuestion: {question}"}],
    )
    print(f"\n{resp.content[0].text}")


def cmd_status():
    import db
    db.init()
    st = db.stats()

    # Also check email cache
    email_total = 0
    email_processed = 0
    email_db = _HERE.parent / "email-analyzer" / "email_cache.db"
    if email_db.exists():
        import sqlite3
        with sqlite3.connect(email_db) as conn:
            email_total = conn.execute("SELECT COUNT(*) FROM emails").fetchone()[0]
            email_processed = conn.execute("SELECT COUNT(*) FROM processing").fetchone()[0]

    print(f"\n{'='*55}")
    print(f"  CHIEF OF STAFF — STATUS")
    print(f"{'='*55}")
    print(f"  Email cache      : {email_total:,} emails ({email_processed:,} processed)")
    print(f"  Contacts         : {st['contacts']:,}")
    print(f"  Open actions     : {st['actions_open']:,} (of {st['actions_total']:,} total)")
    print(f"  Calendar events  : {st['calendar_events']:,}")
    print(f"  Daily briefs     : {st['briefs']:,}")
    print(f"{'='*55}")


def main():
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help", "help"):
        print(__doc__)
        return

    cmd = args[0]

    if cmd == "sync":
        quick = "--quick" in args
        cmd_sync(quick=quick)
    elif cmd == "daily-brief":
        cmd_daily_brief()
    elif cmd == "show":
        what = args[1] if len(args) > 1 else "tasks"
        if what == "tasks":
            cmd_show_tasks(urgent_only="--urgent" in args)
        elif what == "contacts":
            rel = args[2] if len(args) > 2 else None
            cmd_show_contacts(relationship=rel)
        else:
            print(f"Unknown: show {what}")
    elif cmd == "contact":
        if len(args) < 2:
            print("Usage: chief contact \"Name or email\"")
            return
        cmd_contact(args[1])
    elif cmd == "nurture-leads":
        cmd_nurture_leads()
    elif cmd == "reconnect":
        cmd_reconnect()
    elif cmd == "status":
        cmd_status()
    elif cmd == "ask":
        if len(args) < 2:
            print("Usage: chief ask \"your question\"")
            return
        cmd_ask(args[1])
    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)


if __name__ == "__main__":
    main()
