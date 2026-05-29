"""
Ledger — Financial tracking & reminders sub-agent for Atlas.
Tracks invoices, referral commissions, domain renewals, mortgage, and overdue payments.
"""
import json
import re
import sqlite3
from datetime import datetime, timezone, timedelta
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

LEDGER_SYSTEM = """You are Ledger, the financial sub-agent for Atlas (Chief of Staff to Emod Vafa).

You track every financial signal in Emod's world:
- Banoo Marketing invoices (receivables and payables)
- Referral commissions: Merchant Growth, Driven Financial (code: BANOO), AFN, Journey Capital
- Domain renewals: banoo.report, roofing.us.com, kerman.marketing, superlink.my, legalshield.my
- Mortgage: $1,428.36/month AutoPay (1st of month)
- RBC business account (Banoo Inc. — account XXXXX-XXX2309)
- TD accounts (Emod + father Majid Vafaei's Direct Investment account)
- Questrade brokerage (YieldMax ETFs, stocks)
- VEGAIN Nutrition investment
- Alibaba Trade Assurance orders

Your output format for each financial item:
- CATEGORY: Invoice | Commission | Renewal | Mortgage | Banking | Investment
- AMOUNT: if known
- DUE / STATUS: date or status
- ACTION: what Emod needs to do (if anything)
- URGENCY: 🔴 Overdue | 🟠 Due within 7 days | 🟡 Due within 30 days | 🟢 Tracked

Be precise. Flag anything that could cost money if missed.
Never recommend financial actions without noting they require Emod's approval."""


def _get_financial_emails(limit: int = 100) -> list[dict]:
    if not _EMAIL_DB.exists():
        return []
    with sqlite3.connect(_EMAIL_DB) as c:
        c.row_factory = sqlite3.Row
        rows = c.execute("""
            SELECT sender, subject, date_str, date_ts, body_text
            FROM emails
            WHERE (
                sender LIKE '%rbc%' OR sender LIKE '%td%'
                OR sender LIKE '%questrade%' OR sender LIKE '%porkbun%'
                OR sender LIKE '%interac%' OR sender LIKE '%mortgage%'
                OR sender LIKE '%afnllc%' OR sender LIKE '%journeycapital%'
                OR sender LIKE '%merchantgrowth%' OR sender LIKE '%driven%'
                OR sender LIKE '%vegain%' OR sender LIKE '%alibaba%'
                OR subject LIKE '%invoice%' OR subject LIKE '%payment%'
                OR subject LIKE '%renewal%' OR subject LIKE '%commission%'
                OR subject LIKE '%statement%' OR subject LIKE '%expires%'
                OR subject LIKE '%domain%' OR subject LIKE '%retainer%'
                OR subject LIKE '%deposit%' OR subject LIKE '%transfer%'
            )
            ORDER BY date_ts DESC
            LIMIT ?
        """, (limit,)).fetchall()
    return [dict(r) for r in rows]


def _get_open_financial_actions() -> list[dict]:
    import sys
    sys.path.insert(0, str(_CHIEF))
    import db
    all_actions = db.get_actions(status="OPEN", limit=100)
    financial_keywords = [
        "invoice", "payment", "mortgage", "domain", "renew", "commission",
        "statement", "transfer", "autopay", "billing", "retainer", "expires",
        "fee", "overdue", "credit", "debit"
    ]
    financial = []
    for a in all_actions:
        title_lower = (a.get("title") or "").lower()
        if any(kw in title_lower for kw in financial_keywords):
            financial.append(a)
    return financial


def run_financial_scan() -> str:
    """Full financial health scan — returns structured report."""
    emails = _get_financial_emails(80)
    actions = _get_open_financial_actions()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    client = anthropic.Anthropic()
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2500,
        system=[{"type": "text", "text": LEDGER_SYSTEM, "cache_control": {"type": "ephemeral"}}],
        messages=[{
            "role": "user",
            "content": f"""Today is {today}. Run a full financial health scan for Emod.

Open financial action items from system:
{json.dumps([{'title': a['title'], 'priority': a['priority'], 'deadline': a.get('deadline')}
             for a in actions], indent=2)}

Recent financial emails (newest first):
{json.dumps([{
    'sender': e['sender'],
    'subject': e['subject'],
    'date': e['date_str'],
    'preview': (e.get('body_text') or '')[:300]
} for e in emails[:50]], indent=2)}

Produce a structured financial snapshot:
1. 🔴 OVERDUE or CRITICAL (act today)
2. 🟠 DUE THIS WEEK (act by Friday)
3. 🟡 DUE THIS MONTH (plan ahead)
4. 💰 MONEY OWED TO EMOD (receivables/commissions outstanding)
5. 📊 INVESTMENTS (brief status)
6. 🗂️ DOMAINS PORTFOLIO (renewal calendar)

Be specific with amounts and dates where visible. Flag what's missing."""
        }],
    )
    return resp.content[0].text


def run_invoice_check() -> str:
    """Check for any outstanding invoices to or from Emod."""
    emails = _get_financial_emails(50)
    invoice_emails = [e for e in emails if any(
        kw in (e.get('subject') or '').lower() or kw in (e.get('body_text') or '').lower()
        for kw in ['invoice', 'retainer', 'payment due', 'outstanding', 'overdue']
    )]
    if not invoice_emails:
        return "Ledger: No invoice-related emails found in recent history."

    client = anthropic.Anthropic()
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1500,
        system=LEDGER_SYSTEM,
        messages=[{
            "role": "user",
            "content": f"""Extract all invoice information from these emails.

For each invoice found, list:
- Direction: EMOD OWES or EMOD IS OWED
- Amount
- From/To
- Due date
- Status (paid / outstanding / overdue)
- Action needed

Emails:
{json.dumps([{
    'sender': e['sender'],
    'subject': e['subject'],
    'date': e['date_str'],
    'body': (e.get('body_text') or '')[:500]
} for e in invoice_emails], indent=2)}"""
        }],
    )
    return resp.content[0].text


def run_commission_tracker() -> str:
    """Track referral commissions across all partner programs."""
    client = anthropic.Anthropic()
    emails = _get_financial_emails(60)
    commission_emails = [e for e in emails if any(
        kw in (e.get('sender') or '').lower() or kw in (e.get('subject') or '').lower()
        for kw in ['merchantgrowth', 'driven', 'afnllc', 'journeycapital', 'referral', 'commission', 'partner']
    )]

    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1200,
        system=LEDGER_SYSTEM,
        messages=[{
            "role": "user",
            "content": f"""Track Emod's referral commission pipeline across his 4 partner programs:

1. Merchant Growth (Justin Chen — jchen@merchantgrowth.com) — business loan referrals
2. Driven Financial (Cordia Tsoi — code: BANOO) — financing referrals
3. Advance Funds Network / AFN (Brian Costello) — business funding
4. Journey Capital (Laura Stewart) — lending referrals

From these emails, determine:
- What leads have been submitted
- What commissions are pending
- What commissions have been paid
- What's the estimated pipeline value
- What needs follow-up

Emails:
{json.dumps([{
    'sender': e['sender'],
    'subject': e['subject'],
    'date': e['date_str'],
    'body': (e.get('body_text') or '')[:400]
} for e in commission_emails], indent=2)}

If no data available for a program, flag it as "needs check-in"."""
        }],
    )
    return resp.content[0].text


if __name__ == "__main__":
    import sys
    args = sys.argv[1:]
    cmd = args[0] if args else "scan"

    if cmd == "scan":
        print("\n  Ledger: Full financial scan\n")
        print("  " + "─" * 60)
        print(run_financial_scan())
    elif cmd == "invoices":
        print("\n  Ledger: Invoice check\n")
        print(run_invoice_check())
    elif cmd == "commissions":
        print("\n  Ledger: Referral commission tracker\n")
        print(run_commission_tracker())
    else:
        print("Usage: ledger.py [scan | invoices | commissions]")
