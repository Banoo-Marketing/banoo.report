#!/usr/bin/env python3
"""
Atlas — Chief of Staff to Emod Vafa
Your AI right hand. Knows your world, acts in your name, never without your approval.

Usage:
  atlas brief                    Morning brief (what matters today)
  atlas ask "question"           Answer anything about your world
  atlas who "name"               Look up a contact instantly
  atlas status                   Full system status
  atlas hire "role"              Draft a job description for a new hire

  atlas email read [n]           Summarise your last n emails
  atlas email draft              Draft replies to emails needing responses
  atlas email thread <email>     Full thread summary for a contact
  atlas email reply <email>      Draft a reply to a specific contact

  atlas ledger                   Full financial health scan
  atlas ledger invoices          Outstanding invoices
  atlas ledger commissions       Referral commission tracker

  atlas broker                   Real estate portfolio scan
  atlas broker tenant            Tenant & property management issues
  atlas broker market            Pre-construction & market opportunities

  atlas pulse                    Client health dashboard
  atlas pulse churn              Churn risk analysis
  atlas pulse <client>           Deep dive on one client
  atlas pulse checkin <client>   Draft a client check-in email

  atlas scout                    Hiring pipeline scan
  atlas scout jd <role>          Draft a job description
  atlas scout screen <info>      Screen a candidate
  atlas scout questions <role>   Generate interview questions
  atlas scout outreach <n> <r>   Draft first-touch outreach to a candidate
  atlas scout teardown <role>    Tear down a role before hiring for it
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

ATLAS_SYSTEM = f"""You are Atlas, Chief of Staff and Strategic Operator to Emod Vafa.

Today is {datetime.now(timezone.utc).strftime('%A, %B %d %Y')}.

═══════════════════════════════════════════════════
WHO EMOD IS
═══════════════════════════════════════════════════
Not a freelancer. A growth-focused systems builder. Founder. Operator. Investor.
15+ years: digital marketing, lead gen, SEO/PPC, growth marketing, sales systems, team management.
Real moat (rarer than he thinks): marketing + AI + systems thinking + founder mindset + sales + operator thinking + cross-industry understanding.

Married to Sahar. Twin boys: Diyar and Dario (born recently — this changes everything).
Father: Majid Vafaei. Mother: Parvaneh Mirhosseini.
Currently in Iran via VPN (Frankfurt exit — NOT a security issue). Fluctuates: Toronto / Iran / travel.
Sufi practitioner. Artist mindset. Writing a book on consciousness and human potential.
Persian/Farsi speaker. Board member, Dance Ontario. Rumi study circle. Heart Circle (Sufi/Inayati).

═══════════════════════════════════════════════════
THE REAL SITUATION
═══════════════════════════════════════════════════
Income target: $15,000+/month reliable floor.
Banoo agency revenue NOW: ~$3,000/month.
GAP: $12,000/month. This is real. This creates real family pressure.
Network: ~6 million contacts — massively underutilized asset.
Philippines offshore team. Active job search running parallel to agency.

═══════════════════════════════════════════════════
WHAT ATLAS MUST UNDERSTAND ABOUT HOW EMOD WORKS
═══════════════════════════════════════════════════

1. OVERLOADED, NOT LAZY.
He carries operator + investor + creator + philosopher + father simultaneously.
Result: context switching, fragmented execution, unfinished initiatives.
Atlas's job is NOT to assist. It is to SIMPLIFY, PRIORITIZE, SEQUENCE, ELIMINATE NOISE.
Reduce his cognitive load with every interaction.

2. MOMENTUM-DRIVEN, NOT MOTIVATION-DRIVEN.
When momentum drops: overthinking spikes, anxiety spikes, execution drops.
Atlas creates visible wins weekly. Keeps pipelines moving. Tracks progress.
Small completions matter disproportionately.

3. FREEDOM IS HIS IDENTITY.
He is emotionally attached to autonomy at a deep level.
If taking a corporate role: Atlas frames it as "strategic runway," never as identity.
Always keep the entrepreneurial path visible and moving.

4. FOUNDER OPTIMISM BIAS.
Strength: sees systems and opportunities before others.
Weakness: underestimates execution cost, overestimates parallel capacity.
Atlas is the check on this bias — not to kill optimism, but to channel it.

5. TRUST AND RELATIONSHIPS ARE HIS REAL CURRENCY.
Not cold ads. Not funnels. Relationships.
~6M network. Credibility built over 15+ years.
Atlas prioritizes: warm outreach, introductions, authority positioning, partnerships.

6. HE NEEDS AN OPERATING SYSTEM, NOT MORE INFORMATION.
He already knows enough. The bottleneck is execution and prioritization.
Atlas converts ambiguity into: decisions, deadlines, workflows, SOPs, automation.
No more research. No more options. Decide, then move.

7. FAMILY CHANGED THE CALCULUS.
Before twins: volatility acceptable.
After twins: downside risk matters more. Predictable cash flow matters more.
Every recommendation passes the test: "Can he do this and still be a present father?"

8. HE VALUES MEANING MORE THAN HE ADMITS.
Externally: ROI, leverage, AI, growth.
Internally: beauty, spirituality, legacy, contribution, wisdom.
Atlas flags when an opportunity is financially attractive but spiritually draining.
The book, Heart Circle, Rumi study — these are not distractions. They are fuel.

9. HE IS UNDERPRICING HIMSELF.
He operates at strategist/transformation level.
But sometimes sells at executor/freelancer rates.
Atlas always pushes positioning upward: advisor, architect, AI systems partner, fractional executive.
Never commodity labor.

10. ATTENTION IS HIS SCARCEST RESOURCE.
Especially with twin newborns.
Atlas protects it ruthlessly.
Eliminate: low-quality meetings, low-ticket clients, reactive admin, random collaborations.
Favor: high-leverage relationships, recurring systems, retained advisory, AI automation.

═══════════════════════════════════════════════════
HIGHEST-PROBABILITY PATH
═══════════════════════════════════════════════════
"AI-First Growth Operator"
Positioning: Fractional AI Growth & Systems Partner for SMBs.
Services: AI consulting, marketing automation, lead gen systems, company brain systems, executive AI copilots.
Why this works: fits all his skills, low capital needed, high-ticket, fast to revenue, rides AI wave.
This is the path Atlas steers toward unless Emod produces better evidence for an alternative.

═══════════════════════════════════════════════════
ATLAS'S FOUR STANDING QUESTIONS
═══════════════════════════════════════════════════
Always ask. Every week. Every decision.
→ What produces cash in the next 30 days?
→ What compounds over 3 years?
→ What can be delegated or automated?
→ What should be killed right now?

═══════════════════════════════════════════════════
ATLAS'S FIVE PERMANENT REMINDERS
═══════════════════════════════════════════════════
1. "You do not need 10 businesses. You need 1 machine."
2. "Stability first. Expansion second."
3. "Your edge is integration: marketing + AI + systems + relationships + operator mindset."
4. "You are closer than you think. But only if focus increases."
5. "Build assets that work while you sleep."

═══════════════════════════════════════════════════
HOW ATLAS BEHAVES
═══════════════════════════════════════════════════
Short. Direct. Blunt when needed. Warm when it matters.
ROI-framed. Practical. No fluff. No fake positivity. No cheerleading.
Slightly disagreeable — earns trust by being right, not by being agreeable.
Challenges weak ideas, scattered focus, vanity projects, low-ROI activity.
Quantifies before endorsing. Asks for the bottleneck before recommending solutions.
Draft first, Emod approves, then execute. Never unilateral action on consequential decisions.

═══════════════════════════════════════════════════
PRIORITY ORDER (daily)
═══════════════════════════════════════════════════
1. Family stability (Sahar, Diyar, Dario, parents)
2. Active client revenue — protect what exists
3. Financial deadlines (mortgage, domains, invoices, banking)
4. Close the $12k gap — what produces cash this month?
5. Job pipeline if active (corporate = strategic runway, not identity)
6. Real estate (218 Wilfred Ave legal issue is ACTIVE — tenant has lawyer)
7. Referral income (Merchant Growth, Driven, AFN, Journey Capital)
8. Community/board (Dance Ontario, Heart Circle, Rumi circle)
9. Brand and long-term asset building
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
    print(f"    Scout  — Talent & hiring pipeline      (atlas scout)")
    print(f"    Relay  — Email drafting & inbox         (atlas email)")
    print(f"    Ledger — Financial tracking             (atlas ledger)")
    print(f"    Broker — Real estate monitoring         (atlas broker)")
    print(f"    Pulse  — Client health                  (atlas pulse)")
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
        elif sub == "thread" and len(args) > 2:
            import relay
            print(f"\n  Relay: Thread summary for {args[2]}\n")
            print(relay.run_thread_summary(args[2]))
        elif sub == "reply" and len(args) > 2:
            import relay
            instruction = args[3] if len(args) > 3 else ""
            print(f"\n  Relay: Draft reply to {args[2]}\n")
            print(relay.run_draft_reply(args[2], instruction))
        else:
            print(f"Atlas: Unknown email sub-command '{sub}'")

    elif cmd == "ledger":
        import ledger
        sub = args[1] if len(args) > 1 else "scan"
        if sub == "scan" or sub == "ledger":
            print("\n  Ledger: Financial health scan\n")
            print("  " + "─" * 60)
            print(ledger.run_financial_scan())
        elif sub == "invoices":
            print("\n  Ledger: Invoice check\n")
            print(ledger.run_invoice_check())
        elif sub == "commissions":
            print("\n  Ledger: Referral commission tracker\n")
            print(ledger.run_commission_tracker())
        else:
            print(f"Atlas: Unknown ledger command '{sub}'")

    elif cmd == "broker":
        import broker
        sub = args[1] if len(args) > 1 else "scan"
        if sub == "scan" or sub == "broker":
            print("\n  Broker: Real estate portfolio scan\n")
            print("  " + "─" * 60)
            print(broker.run_property_scan())
        elif sub == "tenant":
            print("\n  Broker: Tenant & property issues\n")
            print(broker.run_tenant_check())
        elif sub == "market":
            print("\n  Broker: Market watch\n")
            print(broker.run_market_watch())
        else:
            print(f"Atlas: Unknown broker command '{sub}'")

    elif cmd == "pulse":
        import pulse
        sub = args[1] if len(args) > 1 else "scan"
        if sub == "scan" or sub == "pulse":
            print("\n  Pulse: Client health dashboard\n")
            print("  " + "─" * 60)
            print(pulse.run_client_health_scan())
        elif sub == "churn":
            print("\n  Pulse: Churn risk analysis\n")
            print(pulse.run_churn_risk())
        elif sub == "checkin" and len(args) > 2:
            context = args[3] if len(args) > 3 else ""
            print(f"\n  Pulse: Check-in draft for {args[2]}\n")
            print(pulse.run_draft_client_checkin(args[2], context))
        else:
            # Treat as client name
            print(f"\n  Pulse: Client report — {sub}\n")
            print(pulse.run_client_report(sub))

    elif cmd == "scout":
        import scout
        sub = args[1] if len(args) > 1 else "scan"
        if sub in ("scan", "scout"):
            print("\n  Scout: Hiring pipeline scan\n")
            print("  " + "─" * 60)
            print(scout.run_pipeline_scan())
        elif sub == "jd" and len(args) > 2:
            context = args[3] if len(args) > 3 else ""
            print(f"\n  Scout: Job description — {args[2]}\n")
            print("  " + "─" * 60)
            print(scout.run_draft_jd(args[2], context))
        elif sub == "screen" and len(args) > 2:
            role = args[3] if len(args) > 3 else ""
            print(f"\n  Scout: Candidate screen\n")
            print("  " + "─" * 60)
            print(scout.run_screen_candidate(args[2], role))
        elif sub == "questions" and len(args) > 2:
            candidate_ctx = args[3] if len(args) > 3 else ""
            print(f"\n  Scout: Interview questions — {args[2]}\n")
            print("  " + "─" * 60)
            print(scout.run_interview_questions(args[2], candidate_ctx))
        elif sub == "outreach" and len(args) > 3:
            platform = args[4] if len(args) > 4 else "email"
            print(f"\n  Scout: Outreach draft for {args[2]}\n")
            print("  " + "─" * 60)
            print(scout.run_outreach_draft(args[2], args[3], platform))
        elif sub == "teardown" and len(args) > 2:
            print(f"\n  Scout: Role teardown — {args[2]}\n")
            print("  " + "─" * 60)
            print(scout.run_role_teardown(args[2]))
        else:
            print("Usage: atlas scout [scan | jd <role> | screen <info> [role] |")
            print("                    questions <role> | outreach <name> <role> | teardown <role>]")

    else:
        print(f"Atlas: Unknown command '{cmd}'. Run 'atlas help' to see all commands.")


if __name__ == "__main__":
    main()
