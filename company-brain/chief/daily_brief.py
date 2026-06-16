"""
daily_brief.py — Generates your daily morning brief using Claude.

Synthesises: today's calendar, urgent actions, key people to contact,
dormant relationships, and one strategic reminder.
"""
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import anthropic
import db

_HERE = Path(__file__).parent
try:
    from dotenv import load_dotenv
    load_dotenv(_HERE.parent.parent / "company-brain" / ".env")
    load_dotenv(_HERE.parent / ".env")
except ImportError:
    pass


def _format_event(e: dict) -> str:
    import json as _json
    attendees = e.get("attendees", [])
    if isinstance(attendees, str):
        try:
            attendees = _json.loads(attendees)
        except Exception:
            attendees = []
    names = [a.get("name") or a.get("email", "") for a in attendees[:4]]
    names_str = ", ".join(n for n in names if n) or "no attendees"
    return f"  {e['start_time'][11:16] if len(e.get('start_time',''))>10 else e.get('start_time','')} — {e['title']} (with {names_str})"


def generate_brief(verbose: bool = True) -> dict:
    """Generate today's daily brief. Returns structured brief data."""
    db.init()

    # Gather data
    events = db.get_upcoming_events(days=1)
    urgent_actions = db.get_actions(status="OPEN", priority="HIGH", limit=5)
    all_actions = db.get_actions(status="OPEN", limit=10)
    dormant = db.get_dormant_contacts(days=90)[:5]
    top_contacts = db.get_top_contacts(n=5)
    st = db.stats()

    # Build context for Claude
    context = {
        "today": datetime.now(timezone.utc).strftime("%A, %B %d %Y"),
        "calendar_today": [_format_event(e) for e in events],
        "urgent_actions": [
            {"title": a["title"], "from": a.get("from_name",""), "deadline": a.get("deadline","")}
            for a in urgent_actions
        ],
        "pending_actions_count": st["actions_open"],
        "dormant_contacts": [
            {"name": c.get("name",""), "email": c["email"], "last_contact": c.get("last_contact",""),
             "relationship": c.get("relationship",""), "suggested_action": c.get("suggested_action","")}
            for c in dormant
        ],
        "top_contacts": [
            {"name": c.get("name",""), "email": c["email"], "strength": c.get("strength",0)}
            for c in top_contacts
        ],
    }

    prompt = f"""Generate a concise daily brief for my Chief of Staff system.

Context:
{json.dumps(context, indent=2)}

Return JSON:
{{
  "greeting": "Brief personalised good morning (1 sentence)",
  "calendar_summary": "What today looks like in 1-2 sentences",
  "top_3_tasks": [
    {{"title": "...", "why": "why this is urgent today", "action": "specific next step"}}
  ],
  "people_to_contact": [
    {{"name": "...", "email": "...", "reason": "why contact them today", "suggested_message": "2-sentence draft"}}
  ],
  "dormant_alert": "One person you should reconnect with and why (or null)",
  "strategic_reminder": "One bigger-picture strategic nudge relevant to today"
}}"""

    client = anthropic.Anthropic()
    try:
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        text = resp.content[0].text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.rsplit("```", 1)[0]
        brief = json.loads(text.strip())
    except Exception as e:
        brief = {
            "greeting": f"Good morning! Today is {context['today']}.",
            "calendar_summary": f"You have {len(events)} event(s) today.",
            "top_3_tasks": [{"title": a["title"], "why": "Pending", "action": a.get("suggested_next","")} for a in urgent_actions[:3]],
            "people_to_contact": [],
            "dormant_alert": None,
            "strategic_reminder": "Review your pending actions.",
        }

    brief["generated_at"] = datetime.now(timezone.utc).isoformat()
    brief["raw_context"] = context

    # Save to DB
    import sqlite3
    with sqlite3.connect(db.DB_PATH) as c:
        c.execute("INSERT INTO briefs (generated_at, content, delivered) VALUES (?,?,1)",
                  (brief["generated_at"], json.dumps(brief)))

    return brief


def print_brief(brief: dict):
    """Pretty-print the daily brief to console."""
    print()
    print("=" * 65)
    print("  CHIEF OF STAFF — DAILY BRIEF")
    print("=" * 65)
    print(f"\n  {brief.get('greeting','Good morning!')}")
    print(f"\n  📅 {brief.get('calendar_summary','')}")

    tasks = brief.get("top_3_tasks", [])
    if tasks:
        print(f"\n  🎯 TOP {len(tasks)} TASKS TODAY")
        for i, t in enumerate(tasks, 1):
            print(f"    {i}. {t.get('title','')}")
            print(f"       Why: {t.get('why','')}")
            print(f"       Do: {t.get('action','')}")

    people = brief.get("people_to_contact", [])
    if people:
        print(f"\n  🤝 PEOPLE TO CONTACT TODAY")
        for p in people:
            print(f"    • {p.get('name','')} ({p.get('email','')})")
            print(f"      {p.get('reason','')}")
            if p.get("suggested_message"):
                print(f"      Draft: \"{p['suggested_message']}\"")

    if brief.get("dormant_alert"):
        print(f"\n  ⚠️  RECONNECT ALERT")
        print(f"    {brief['dormant_alert']}")

    if brief.get("strategic_reminder"):
        print(f"\n  🔭 STRATEGIC REMINDER")
        print(f"    {brief['strategic_reminder']}")

    print("\n" + "=" * 65)
