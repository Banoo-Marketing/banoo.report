"""
Broker — Real estate monitoring sub-agent for Atlas.
Tracks Emod's properties, tenant issues, transactions, and market activity.
"""
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

_HERE = Path(__file__).parent
_CHIEF = _HERE.parent / "chief"
_EMAIL_DB = _HERE.parent / "email-analyzer" / "email_cache.db"

try:
    from dotenv import load_dotenv
    load_dotenv(_HERE.parent.parent / "company-brain" / ".env")
    load_dotenv(_HERE.parent / ".env")
except ImportError:
    pass

import anthropic

BROKER_SYSTEM = """You are Broker, the real estate sub-agent for Atlas (Chief of Staff to Emod Vafa).

Emod's real estate profile:
- Licensed REALTOR® with Forest Hill Real Estate Inc., Yorkville office
- Member of TRREB (Toronto Regional Real Estate Board) and OREA
- Uses CREA WEBForms / TransactionDesk for deals

Known properties:
1. 218 Wilfred Ave — rental property (tenant issue active, lawyer Mr. Yousefian involved)
2. 8888 Yonge St, Unit 0627 — personal residence (managed by FirstService Residential, YRSCC 1576)
3. Markham property — property tax outstanding

Active real estate contacts:
- Debbie Bould (debbie@timesproperty.ca) — property manager
- Catherine Himelfarb (catherine@foresthill.com) — Forest Hill broker/team leader
- Ken Yeung (ken.yeung@century21.ca) — Century 21, pre-construction
- Serge Younan (serge@condopromo.com) — CondoPromo, pre-construction deals
- CondoAssignment.ca — assignment deal alerts

Your job:
- Flag tenant issues, legal matters, maintenance requests
- Track mortgage payments and property tax deadlines
- Monitor pre-construction opportunities Emod is watching
- Track TRREB/OREA licensing obligations and deadlines
- Note any listings, showings, or deal activity
- Flag anything from real estate contacts needing a response

Output format:
🏠 PROPERTY: which property
⚠️ ISSUE TYPE: Tenant | Legal | Financial | Maintenance | Opportunity | Admin
📋 STATUS: what's happening
🎯 ACTION: what Emod needs to do (with approval gate if needed)
📅 DEADLINE: if applicable"""


def _get_real_estate_emails(limit: int = 80) -> list[dict]:
    if not _EMAIL_DB.exists():
        return []
    with sqlite3.connect(_EMAIL_DB) as c:
        c.row_factory = sqlite3.Row
        rows = c.execute("""
            SELECT sender, subject, date_str, date_ts, body_text
            FROM emails
            WHERE (
                sender LIKE '%trreb%' OR sender LIKE '%orea%'
                OR sender LIKE '%foresthill%' OR sender LIKE '%transactiondesk%'
                OR sender LIKE '%condoassignment%' OR sender LIKE '%condopromo%'
                OR sender LIKE '%century21%' OR sender LIKE '%timesproperty%'
                OR sender LIKE '%fsresidential%' OR sender LIKE '%immobaker%'
                OR sender LIKE '%markham%' OR sender LIKE '%yousefian%'
                OR subject LIKE '%wilfred%' OR subject LIKE '%8888 yonge%'
                OR subject LIKE '%real estate%' OR subject LIKE '%listing%'
                OR subject LIKE '%mortgage%' OR subject LIKE '%property tax%'
                OR subject LIKE '%tenant%' OR subject LIKE '%landlord%'
                OR subject LIKE '%condo%' OR subject LIKE '%assignment%'
                OR subject LIKE '%showing%' OR subject LIKE '%offer%'
                OR subject LIKE '%REALTOR%' OR subject LIKE '%WEBForms%'
                OR sender LIKE '%debbie%' OR sender LIKE '%catherine%'
            )
            ORDER BY date_ts DESC
            LIMIT ?
        """, (limit,)).fetchall()
    return [dict(r) for r in rows]


def _get_real_estate_actions() -> list[dict]:
    import sys
    sys.path.insert(0, str(_CHIEF))
    import db
    all_actions = db.get_actions(status="OPEN", limit=100)
    re_keywords = [
        "wilfred", "property", "tenant", "mortgage", "listing", "condo",
        "realtor", "broker", "trreb", "orea", "assignment", "markham",
        "yonge", "debbie", "tax", "landlord"
    ]
    return [a for a in all_actions if any(
        kw in (a.get("title") or "").lower() for kw in re_keywords
    )]


def run_property_scan() -> str:
    """Full real estate portfolio scan — status of all properties and activity."""
    emails = _get_real_estate_emails(60)
    actions = _get_real_estate_actions()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    client = anthropic.Anthropic()
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2500,
        system=[{"type": "text", "text": BROKER_SYSTEM, "cache_control": {"type": "ephemeral"}}],
        messages=[{
            "role": "user",
            "content": f"""Today is {today}. Run a full real estate portfolio scan for Emod.

Open real estate action items:
{json.dumps([{'title': a['title'], 'priority': a['priority'], 'deadline': a.get('deadline'),
              'next_step': a.get('suggested_next')} for a in actions], indent=2)}

Recent real estate emails:
{json.dumps([{
    'sender': e['sender'],
    'subject': e['subject'],
    'date': e['date_str'],
    'preview': (e.get('body_text') or '')[:350]
} for e in emails[:50]], indent=2)}

Produce a structured report:
1. 🔴 URGENT — needs action today (tenant/legal/financial deadline)
2. 🏠 PROPERTY STATUS — each of the 3 properties
3. 📋 OPEN MATTERS — ongoing issues and their current state
4. 🎯 OPPORTUNITIES — pre-con deals or market activity worth tracking
5. 📅 UPCOMING DEADLINES — licensing, property tax, mortgage, TRREB/OREA
6. 👥 CONTACTS TO FOLLOW UP WITH"""
        }],
    )
    return resp.content[0].text


def run_tenant_check() -> str:
    """Deep dive on tenant and property management issues."""
    emails = _get_real_estate_emails(40)
    tenant_emails = [e for e in emails if any(
        kw in (e.get('subject') or '').lower() or kw in (e.get('body_text') or '').lower()
        for kw in ['tenant', 'wilfred', 'yousefian', 'landlord', 'rent', 'maintenance',
                   'repair', 'notice', 'lease', 'eviction', 'ltb']
    )]

    if not tenant_emails:
        return "Broker: No active tenant/property management issues found in recent emails."

    client = anthropic.Anthropic()
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1500,
        system=BROKER_SYSTEM,
        messages=[{
            "role": "user",
            "content": f"""Summarise all tenant and property management issues from these emails.

Key context: 218 Wilfred Ave has an active tenant issue. Lawyer Yousefian is involved.
Debbie Bould (debbie@timesproperty.ca) is the property manager.

For each issue:
- Property address
- Nature of the problem
- Current status
- What Emod needs to do and by when
- Legal risks if not addressed

Emails:
{json.dumps([{
    'sender': e['sender'],
    'subject': e['subject'],
    'date': e['date_str'],
    'body': (e.get('body_text') or '')[:600]
} for e in tenant_emails], indent=2)}"""
        }],
    )
    return resp.content[0].text


def run_market_watch() -> str:
    """Summarise pre-construction and market opportunities in Emod's inbox."""
    emails = _get_real_estate_emails(60)
    market_emails = [e for e in emails if any(
        kw in (e.get('sender') or '').lower() or kw in (e.get('subject') or '').lower()
        for kw in ['condoassignment', 'condopromo', 'pre-construction', 'preconstruction',
                   'assignment', 'launch', 'vip', 'platinum', 'developer']
    )]

    if not market_emails:
        return "Broker: No pre-construction or market opportunity emails found recently."

    client = anthropic.Anthropic()
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1500,
        system=BROKER_SYSTEM,
        messages=[{
            "role": "user",
            "content": f"""Summarise pre-construction and investment real estate opportunities from these emails.

For each opportunity:
- Project name and location
- Price range / unit types
- Why it might interest Emod (investor lens)
- Urgency (VIP/launch dates)
- Recommended action

Emails:
{json.dumps([{
    'sender': e['sender'],
    'subject': e['subject'],
    'date': e['date_str'],
    'body': (e.get('body_text') or '')[:500]
} for e in market_emails], indent=2)}"""
        }],
    )
    return resp.content[0].text


if __name__ == "__main__":
    import sys
    args = sys.argv[1:]
    cmd = args[0] if args else "scan"

    if cmd == "scan":
        print("\n  Broker: Real estate portfolio scan\n")
        print("  " + "─" * 60)
        print(run_property_scan())
    elif cmd == "tenant":
        print("\n  Broker: Tenant & property management check\n")
        print(run_tenant_check())
    elif cmd == "market":
        print("\n  Broker: Market watch — pre-con & opportunities\n")
        print(run_market_watch())
    else:
        print("Usage: broker.py [scan | tenant | market]")
