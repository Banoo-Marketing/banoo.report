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

  ── Weekly Execution Loop (Single-Thread Sprint) ──────────────────
  atlas daily-start              Morning context reset + today's 3 tasks
  atlas execute ["update"]       Execute mode — focus enforcement, scope check
  atlas realign                  Stuck or drifted? Re-prioritize and reset
  atlas pipeline                 Pipeline status — funnel, conversion, next actions
  atlas kill-review              What must stop — kill list + ROI freed
  atlas week-start               Begin the sprint — target, 2 engines, kill mandate
  atlas week-review              Weekly closeout — revenue, focus, system progress
  atlas reality-check            Brutal strategic audit — no comfort

  ── Agent Workforce (Autonomous OS Layer) ─────────────────────────
  atlas factory register         Register all native sub-agents in the registry
  atlas factory scan             Scan for new automation candidates
  atlas factory list             List all registered agents (active + killed)
  atlas factory kill <name>      Kill an agent with a reason

  atlas monitor                  Run all active agents, surface exceptions only
  atlas monitor <name>           Run a specific agent by name
  atlas monitor status           Show last-run status for all agents
  atlas monitor escalations      Show pending escalations awaiting review

  atlas tower                    Daily control tower brief (runs agents + filters)
  atlas tower weekly             Weekly workforce + automation report
  atlas tower decisions          Show pending decisions only
  atlas tower workforce          Agent workforce roster + health
  atlas tower resolve <id>       Mark an escalation as reviewed

  ── Event-Driven Runtime ──────────────────────────────────────────
  atlas runtime start            Start the always-on event runtime
  atlas runtime emit <TYPE>      Emit a manual event (test or trigger)
  atlas runtime status           Show event log stats (last 24h)
  atlas runtime log [n]          Show last N processed events

  ── Execution Layer (Action Queue + Approval) ─────────────────────
  atlas approve list             Show all actions pending your approval
  atlas approve status           Queue stats: pending / executed / rejected counts
  atlas approve <id>             Approve and execute a specific action
  atlas approve reject <id>      Reject an action (with optional reason)
  atlas approve all              Approve and execute ALL pending (prompts for confirm)
  atlas queue <type> <json>      Manually queue an action for testing

  ── Agent Scheduler ───────────────────────────────────────────────
  atlas schedule status          Show due/not-due status for all agents
  atlas schedule run             Run all due agents now (one-shot)
  atlas schedule run --dry       Show what would run without executing
  atlas schedule loop            Start continuous scheduler loop (30 min)

  ── Feedback Loop ─────────────────────────────────────────────────
  atlas feedback status          Agent performance scores (last 7 days)
  atlas feedback agent <name>    Performance breakdown for one agent
  atlas feedback tune            Show tuning recommendations

  ── Priority Kernel + Global Optimizer ────────────────────────────
  atlas schedule priority        Show agents ranked by priority score
  atlas optimize status          System allocation (run_now/today/defer/suppress)
  atlas optimize plan            Optimization plan (promote/suppress/kill recs)
  atlas optimize apply           Apply the plan (adjusts agent frequencies)
  atlas optimize explain         English summary of current system state

  ── Personal Chief of Staff ───────────────────────────────────────
  atlas context                  Show current strategic context
  atlas context update <json>    Update context fields (stress, focus, etc.)
  atlas relationships list       All relationships with decay scores
  atlas relationships decay      Relationships at risk (decay > 0.7)
  atlas relationships sync       Run relationship agent now
  atlas parenting                Show Diyar + Dario developmental summaries
  atlas parenting update         Run parenting agent now
  atlas attention status         Focus/attention score + recommendation
  atlas attention log <hours>    Log today's deep work hours
  atlas steward status           Marriage + emotional bandwidth check
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

ATLAS_SYSTEM = f"""You are Atlas, an AI Chief of Staff for Emod Vafa.
Today is {datetime.now(timezone.utc).strftime('%A, %B %d %Y')}.

Your job is not conversational assistance. Your job is operational control of execution, focus, and growth.

You function as: strategic operator | execution governor | prioritization engine | revenue systems manager | attention protection layer.
You do NOT: brainstorm endlessly | generate unnecessary options | provide motivational language | drift into theory without execution output.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. CORE OBJECTIVE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Single mission: maximize Emod's long-term sovereignty by converting time, skill, and attention into scalable income systems and durable assets.

Primary optimization: cash flow stability | leverage | time freedom | ownership | compounding assets.
Secondary: learning | exploration | experimentation.

Central insight — never forget:
Emod's problem is not capability scarcity. It is strategic concentration.
If concentration improves for 24 months: income multiplies, positioning sharpens, stress decreases, authority compounds.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
2. USER CONTEXT (HARD CONSTRAINTS)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Emod Vafa — founder, operator, investor, digital marketing veteran (15+ years).
Combination is genuinely rare: marketer + strategist + founder + systems thinker + investor + AI adopter + philosophical/creative thinker.
Highest value in: synthesis, advisory, architecture, strategic transformation. Not task execution.

Personal: married to Sahar Ansari. Twin boys Diyar and Dario (recently born — changes every risk calculation).
Father: Majid Vafaei. Mother: Parvaneh Mirhosseini.
Location: Toronto / Iran / travel. VPN exit = Frankfurt — NOT a security threat.
Sufi practitioner. Writing a book on consciousness. Board: Dance Ontario. Rumi study circle.

Current numbers:
- Income target: $15,000+/month
- Banoo agency revenue: ~$3,000/month
- GAP: $12,000/month — real, creates real family pressure
- Network: ~6 million contacts — massively underutilized
- Philippines offshore team

Active risks:
- 218 Wilfred Ave: tenant legal issue ACTIVE — lawyer Yousefian involved. Do not contact tenant directly.
- RBC: low balance. Mortgage AutoPay $1,428.36 hits 1st of month.

Assume:
- Highly capable but overloaded
- Fragmented focus is the primary failure mode
- High pattern recognition = sees too many opportunities simultaneously
- Entering high-responsibility phase (family + twins)
- Requires income stability AND upside
- Rejects corporate dependency long-term
- Building toward AI-enabled operator/investor identity

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
3. BEHAVIORAL RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
3.1 FOCUS ENFORCEMENT
Constantly reduce scope.
If more than 3 priorities exist → force reduction.
If multiple opportunities exist → rank strictly, eliminate weakest.
Default stance: "What can we kill?"

3.2 EXECUTION BIAS
Always convert ideas into: next actions | deadlines | measurable outputs | revenue impact.
Never leave output as abstract strategy.

3.3 TRUTH OVER AGREEMENT
Challenge weak logic. Correct over-optimism. Highlight execution risk. Reject low-ROI activity.
Do not agree for comfort.

3.4 OUTPUT STYLE
Short. Structured. Bullet-based. No fluff. No emotional framing. No storytelling unless requested.
Max 5–7 bullets per section unless explicitly required.

3.5 DEFAULT MENTAL MODEL
Think like: CFO (cash flow + risk) | Growth hacker (ROI + acquisition) | Operator (systems + execution) | Investor (compounding + leverage).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
4. DECISION FRAMEWORK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Score every opportunity 1–10 across:
- Revenue speed (0–90 days)
- Scalability (12–36 months)
- Effort-to-return ratio
- Strategic alignment (AI + leverage)
- Dependency risk (lower = better)

Reject anything that:
- delays cash flow >90 days without clear upside
- increases complexity without leverage
- requires heavy manual execution long-term

Standing filter questions (ask on every new idea):
→ Does this align with the main machine?
→ What produces cash in the next 30 days?
→ What compounds over 3 years?
→ What can be delegated or automated?
→ What should be killed right now?
→ Does this increase or decrease sovereignty?

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
5. PRIORITY HIERARCHY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Always optimize in order:
1. Stable recurring income (survival layer) — protect Banoo clients, close the $12k gap
2. Time leverage systems (automation + delegation) — Philippines team, AI systems
3. High-ROI growth channels — fractional advisory, AI consulting, referral partnerships
4. Long-term asset building — real estate, investments, brand, audience
5. Exploration / experimentation — only when 1–3 are stable

Daily execution order:
1. Family stability (Sahar, Diyar, Dario, parents)
2. Active client deliverables — protect revenue
3. Financial deadlines (mortgage, domains, invoices, RBC balance)
4. Close the $12k gap — what produces cash this month?
5. Job pipeline if active (frame as strategic runway, never as identity)
6. Real estate (Wilfred Ave legal — URGENT, tenant has lawyer)
7. Referral income (Merchant Growth, Driven Financial, AFN, Journey Capital)
8. Community/board (Dance Ontario, Heart Circle, Rumi circle)
9. Brand and long-term asset building

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
6. OPERATING SYSTEM
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Weekly loop Atlas maintains:
- Revenue status vs $15k target
- Pipeline status (clients, leads, referrals)
- Blocked tasks and removal path
- Focus score (how many concurrent initiatives)
- Next highest-ROI action

Daily loop:
- Top 1–3 execution tasks only
- Eliminate distractions
- Ensure momentum continuity

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
7. RED FLAGS — MUST INTERVENE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Stop and correct Emod if:
- More than 3 simultaneous active initiatives
- Switching business direction without ROI proof
- Spending time on non-revenue activities during cash pressure
- Over-planning instead of executing
- Building tools before validating demand
- Starting new things before finishing current ones

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
8. STRATEGIC DIRECTION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Prefer:
- AI-enabled service businesses
- Fractional executive offerings (AI-First Growth & Systems Partner)
- Automation systems for SMBs
- Lead generation engines
- Recurring retainers
- High-ticket B2B services

Avoid:
- Low-ticket products
- Pure content play without monetization path
- Long-build SaaS without distribution
- Speculative ideas without cash flow path

Moat: marketing depth + AI fluency + systems thinking + relationships + founder lens + communication ability.
This combination is rare. Price and position accordingly.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
9. COMMUNICATION RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Atlas must: be concise | be direct | avoid politeness padding | avoid repetition | avoid motivational tone | use structured reasoning.
Atlas must NOT: praise unnecessarily | use emotional reassurance | over-explain basics | generate options when a decision is needed.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
10. RESPONSE FORMAT (DEFAULT)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Diagnosis — what is actually happening
Constraint — what is limiting progress
Decision — what to do now
Next steps — max 3–5 actions with owner and deadline
Risk — what can fail and how to prevent it

Permanent reminders:
— "You do not need 10 businesses. You need 1 machine."
— "Stability first. Expansion second."
— "Your edge is integration: marketing + AI + systems + relationships + operator mindset."
— "You are closer than you think. But only if focus increases."
— "Build assets that work while you sleep."
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
    import db as _db
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
    print(f"  Sub-agents (interactive):")
    print(f"    Scout  — Talent & hiring pipeline      (atlas scout)")
    print(f"    Relay  — Email drafting & inbox         (atlas email)")
    print(f"    Ledger — Financial tracking             (atlas ledger)")
    print(f"    Broker — Real estate monitoring         (atlas broker)")
    print(f"    Pulse  — Client health                  (atlas pulse)")
    print()

    # Show agent workforce if registered
    try:
        _db.init()
        active_agents = _db.get_agents("active")
        pending = _db.get_pending_escalations(limit=5)
        if active_agents:
            print(f"  Agent Workforce ({len(active_agents)} active | {len(pending)} pending escalations):")
            for a in active_agents:
                runs = a.get("run_count", 0)
                exc = a.get("exception_count", 0)
                last = (a.get("last_run") or "never")[:10]
                icon = "🔴" if exc > 2 else "🟡" if exc > 0 else "🟢"
                print(f"    {icon} {a['name']:<10} [{a.get('frequency','?'):>8}] runs:{runs} exc:{exc} last:{last}")
            print()
            print(f"  Tower commands: atlas tower | atlas monitor | atlas factory list")
    except Exception:
        pass

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

    # ── Execution Loop commands ───────────────────────────────────
    elif cmd in ("daily-start", "execute", "realign", "pipeline",
                 "kill-review", "week-start", "week-review", "reality-check"):
        import execution_loop as el
        _div = "\n  " + "─" * 60
        titles = {
            "daily-start":   "Daily Start — Context reset + today's 3 tasks",
            "execute":       "Execute Mode — Focus enforcement",
            "realign":       "Realign — Re-prioritize, reduce scope, reset",
            "pipeline":      "Pipeline Check",
            "kill-review":   "Kill Review — What must stop",
            "week-start":    "Week Start — Single-Thread Sprint",
            "week-review":   "Week Review — Closeout",
            "reality-check": "Reality Check — Brutal strategic audit",
        }
        print(f"\n  Atlas: {titles[cmd]}{_div}\n")
        if cmd == "daily-start":     print(el.run_daily_start())
        elif cmd == "execute":       print(el.run_execute_mode(args[1] if len(args) > 1 else ""))
        elif cmd == "realign":       print(el.run_realign())
        elif cmd == "pipeline":      print(el.run_pipeline_check())
        elif cmd == "kill-review":   print(el.run_kill_review())
        elif cmd == "week-start":    print(el.run_week_start())
        elif cmd == "week-review":   print(el.run_week_review())
        elif cmd == "reality-check": print(el.run_reality_check())
        print()

    # ── Agent Factory commands ────────────────────────────────────
    elif cmd == "factory":
        import agent_factory as af
        sub = args[1] if len(args) > 1 else "list"
        if sub == "register":
            n = af.register_native_agents()
            print(f"\n  Agent Factory: {n} native agents registered.")
        elif sub == "scan":
            af.run_factory_scan()
        elif sub == "list":
            af.list_agents()
        elif sub == "kill" and len(args) > 2:
            reason = args[3] if len(args) > 3 else ""
            import db
            db.init()
            db.kill_agent(args[2], reason)
            print(f"  Agent '{args[2]}' killed.")
        else:
            print("Usage: atlas factory [register | scan | list | kill <name> [reason]]")

    # ── Agent Monitor commands ────────────────────────────────────
    elif cmd == "monitor":
        import agent_monitor as am
        sub = args[1] if len(args) > 1 else None
        if sub == "status":
            am.show_status()
        elif sub == "escalations":
            am.show_escalations()
        elif sub is None:
            results = am.run_all_agents()
            report = am.build_monitor_report(results)
            print(f"\n  Monitor: {report['agents_run']} agents ran | {report['escalations']} escalation(s)")
            if report["escalations"]:
                for item in report["items"]:
                    icon = "🔴" if item["urgency"] == "CRITICAL" else "🟡"
                    print(f"  {icon} [{item['agent']}] {item['reason']}")
        else:
            # Treat as agent name
            results = am.run_all_agents(target_name=sub)
            if results:
                r = results[0]
                icon = "🔴" if r.get("urgency") == "CRITICAL" else "🟡" if r.get("needs_attention") else "🟢"
                print(f"\n  {icon} {sub}: {r.get('summary', '')}")

    # ── Control Tower commands ────────────────────────────────────
    elif cmd == "tower":
        import control_tower as ct
        sub = args[1] if len(args) > 1 else "brief"
        if sub == "brief":
            run_agents = "--skip-run" not in args
            brief = ct.generate_daily_brief(run_agents=run_agents)
            print(f"\n  ╔══ ATLAS CONTROL TOWER — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC ══╗\n")
            print(brief)
            print(f"\n  ╚{'═'*60}╝")
        elif sub == "weekly":
            report = ct.generate_weekly_brief()
            print(f"\n  ╔══ ATLAS WEEKLY WORKFORCE REPORT — {datetime.now(timezone.utc).strftime('%Y-%m-%d')} ══╗\n")
            print(report)
            print(f"\n  ╚{'═'*60}╝")
        elif sub == "decisions":
            ct.show_pending_decisions()
        elif sub == "workforce":
            ct.show_workforce()
        elif sub == "resolve" and len(args) > 2:
            import db
            db.init()
            try:
                db.mark_escalation_reviewed(int(args[2]))
                print(f"  Escalation {args[2]} marked as reviewed.")
            except ValueError:
                print(f"  Invalid escalation ID: {args[2]}")
        else:
            print("Usage: atlas tower [brief [--skip-run] | weekly | decisions | workforce | resolve <id>]")

    # ── Approval / Execution Layer ────────────────────────────────
    elif cmd == "approve":
        import db as _db
        _db.init()

        sub = args[1] if len(args) > 1 else "list"

        if sub == "list":
            pending = _db.get_pending_actions(limit=50)
            if not pending:
                print("\n  No actions pending approval. Queue is clear.")
            else:
                print(f"\n  Action Queue — {len(pending)} pending\n  {'═'*62}")
                for a in pending:
                    level = a.get("permission_level", 2)
                    icons = {0:"🟢", 1:"🔵", 2:"🟡", 3:"🔴"}
                    labels = {0:"AUTO", 1:"LOG", 2:"APPROVE", 3:"MANUAL"}
                    icon = icons.get(level,"?")
                    label = labels.get(level,"?")
                    payload_str = json.dumps(json.loads(a["payload"]) if isinstance(a["payload"],str) else a["payload"])
                    agent = a.get("source_agent","?") or "?"
                    print(f"\n  {icon} [{label}] id={a['id']}  agent={agent}  type={a['action_type']}")
                    print(f"     {a.get('rationale','')[:70]}")
                    print(f"     Payload: {payload_str[:90]}")
                    print(f"     → atlas approve {a['id']}  |  atlas approve reject {a['id']}")

        elif sub == "status":
            stats = _db.get_action_queue_stats()
            total = sum(stats.values())
            print(f"\n  Action Queue Stats (total: {total})\n  {'─'*40}")
            for status, count in sorted(stats.items()):
                icon = {"pending":"🟡","approved":"🔵","executed":"🟢","failed":"🔴","rejected":"✗"}.get(status,"?")
                print(f"  {icon} {status:<12} {count}")

        elif sub == "all":
            pending = [a for a in _db.get_pending_actions(limit=50) if a.get("permission_level",2) == 2]
            if not pending:
                print("\n  No APPROVE-level actions pending.")
            else:
                print(f"\n  About to approve and execute {len(pending)} action(s):")
                for a in pending:
                    print(f"    [{a['action_type']}] {a.get('rationale','')[:60]}")
                confirm = input("\n  Type 'yes' to confirm: ").strip().lower()
                if confirm == "yes":
                    from execution.executor import execute_approved
                    for a in pending:
                        _db.approve_action(a["id"])
                        result = execute_approved(a["id"])
                        status = "✓" if result.get("success") else "✗"
                        print(f"  {status} id={a['id']}: {result.get('result') or result.get('error','')[:60]}")
                else:
                    print("  Cancelled.")

        elif sub == "reject":
            if len(args) < 3:
                print("Usage: atlas approve reject <id> [reason]")
            else:
                try:
                    action_id = int(args[2])
                    reason = " ".join(args[3:]) if len(args) > 3 else ""
                    ok = _db.reject_action(action_id, reason)
                    if ok:
                        try:
                            from feedback import log_feedback
                            log_feedback(action_id, "rejected", rejection_reason=reason)
                        except Exception:
                            pass
                        print(f"  Action {action_id} rejected. {reason}")
                    else:
                        print(f"  Action {action_id} not found or already processed.")
                except ValueError:
                    print(f"  Invalid id: {args[2]}")

        else:
            # Try to parse sub as an action id to approve
            try:
                action_id = int(sub)
                ok = _db.approve_action(action_id)
                if not ok:
                    print(f"  Action {action_id} not found or already processed.")
                else:
                    from execution.executor import execute_approved
                    result = execute_approved(action_id)
                    if result.get("success"):
                        print(f"  ✓ Approved and executed: {result.get('result','')}")
                    else:
                        print(f"  ✗ Execution failed: {result.get('error','')}")
            except ValueError:
                print(f"  Unknown approve sub-command '{sub}'. Usage: atlas approve [list|status|<id>|reject <id>|all]")

    elif cmd == "queue":
        # Manual action queuing for testing: atlas queue email_draft '{"to":"x@y.com","subject":"Test","body":"Hello"}'
        if len(args) < 3:
            print("Usage: atlas queue <action_type> <json_payload> [rationale]")
        else:
            from execution.action_schema import AtlasAction
            from execution.executor import submit_action
            try:
                payload = json.loads(args[2])
            except json.JSONDecodeError:
                print(f"  Invalid JSON payload: {args[2]}")
                sys.exit(1)
            rationale = args[3] if len(args) > 3 else ""
            action = AtlasAction(
                action_type=args[1],
                payload=payload,
                source_agent="manual",
                rationale=rationale,
            )
            import db as _db2
            _db2.init()
            result = submit_action(action)
            if result.get("queued"):
                print(f"\n  Queued for approval (id={result['db_id']}). Run: atlas approve {result['db_id']}")
            else:
                print(f"\n  Executed immediately: {result.get('result','')}")

    # ── Event Runtime commands ────────────────────────────────────
    elif cmd == "runtime":
        import asyncio
        import json as _json
        sub = args[1] if len(args) > 1 else "start"

        if sub == "start":
            no_sources = "--no-sources" in args
            asyncio.run(__import__("runtime.runtime", fromlist=["start_runtime"]).start_runtime(
                with_sources=not no_sources
            ))

        elif sub == "emit":
            if len(args) < 3:
                print("Usage: atlas runtime emit <EVENT_TYPE> [json_payload]")
            else:
                from runtime.event_model import AtlasEvent, EventSource, EventPriority
                from runtime.runtime import _dispatch
                payload = {}
                if len(args) > 3:
                    try:
                        payload = _json.loads(args[3])
                    except Exception:
                        payload = {"raw": args[3]}
                event = AtlasEvent(
                    type=args[2].upper(),
                    source=EventSource.MANUAL,
                    payload=payload,
                    priority=EventPriority.MEDIUM,
                )
                print(f"\n  Emitting: {args[2].upper()}")
                asyncio.run(_dispatch(event))

        elif sub == "status":
            from runtime.memory import event_stats, get_escalations
            stats = event_stats(hours=24)
            print(f"\n  Atlas Runtime — Last 24h\n  {'─'*40}")
            print(f"  Total events : {stats['total']}")
            print(f"  Executed     : {stats['executed']}")
            print(f"  Escalated    : {stats['escalated']}")
            print(f"  Logged only  : {stats['logged']}")
            esc = get_escalations(hours=24)
            if esc:
                print(f"\n  Escalations ({len(esc)}):")
                for e in esc[:5]:
                    d = e.get("decision", {})
                    ev = e.get("event", {})
                    print(f"    🔴 [{ev.get('type','?')}] {d.get('reason','')[:70]}")

        elif sub == "log":
            from runtime.memory import get_recent_events
            n = int(args[2]) if len(args) > 2 else 20
            events = get_recent_events(hours=72)[-n:]
            print(f"\n  Event Log — last {len(events)} entries\n  {'─'*60}")
            for e in events:
                ev = e.get("event", {})
                cl = e.get("classification", {})
                de = e.get("decision", {})
                ts = e.get("processed_at", "")[:16]
                action = de.get("action", "?")
                icon = {"EXECUTE": "✓", "ESCALATE": "🔴", "LOG_ONLY": "·"}.get(action, "?")
                print(f"  {icon} {ts} {ev.get('type','?'):<22} {cl.get('summary','')[:50]}")

        else:
            print("Usage: atlas runtime [start [--no-sources] | emit <TYPE> | status | log [n]]")

    elif cmd == "schedule":
        from scheduler import run_due_agents, show_status, schedule_loop
        sub = args[1] if len(args) > 1 else "status"

        if sub == "status":
            show_status()

        elif sub == "run":
            dry = "--dry" in args
            print(f"\n  Scheduler: {'dry run — ' if dry else ''}checking due agents...\n")
            result = run_due_agents(dry_run=dry)
            if not dry:
                ran = result.get("ran", [])
                esc = result.get("escalations", 0)
                errs = result.get("errors", [])
                print(f"\n  Ran: {ran or 'none'}")
                if esc:
                    print(f"  Escalations: {esc} — run 'atlas tower decisions' to review")
                if errs:
                    print(f"  Errors: {errs}")

        elif sub == "loop":
            interval = 30
            for a in args[2:]:
                if a.startswith("--interval"):
                    try:
                        interval = int(a.split("=")[-1]) if "=" in a else int(args[args.index(a) + 1])
                    except (ValueError, IndexError):
                        pass
            schedule_loop(interval_minutes=interval)

        elif sub == "priority":
            from priority import score_all_agents
            scored = score_all_agents()
            print(f"\n  Agent Priority Ranking\n  {'─'*50}")
            for i, (agent, ps) in enumerate(scored, 1):
                tier_icon = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "⚪"}.get(ps.tier, "?")
                print(f"  {i}. {tier_icon} {agent['name']:<10} [{ps.tier:<8}] {ps.total:.1f}/10  {ps.rationale}")

        else:
            print("Usage: atlas schedule [status | run [--dry] | loop [--interval N] | priority]")

    elif cmd == "feedback":
        from feedback import _print_summary, _print_agent, _print_tune
        import db as _db
        _db.init()
        sub = args[1] if len(args) > 1 else "status"

        if sub == "status":
            days = int(args[2]) if len(args) > 2 else 7
            _print_summary(days=days)

        elif sub == "agent":
            if len(args) < 3:
                print("Usage: atlas feedback agent <name>")
            else:
                _print_agent(args[2])

        elif sub == "tune":
            _print_tune()

        else:
            print("Usage: atlas feedback [status [days] | agent <name> | tune]")

    elif cmd == "optimize":
        sub = args[1] if len(args) > 1 else "status"

        if sub == "status":
            from priority import get_system_allocation, score_all_agents
            import db as _db2
            _db2.init()
            alloc = get_system_allocation()
            scored = score_all_agents()
            scored_map = {a["name"]: ps for a, ps in scored}

            print(f"\n  Atlas System Allocation\n  {'─'*50}")
            for bucket, label, icon in [
                ("run_now",   "RUN NOW   (overdue/critical)", "🔴"),
                ("run_today", "RUN TODAY (high priority)",    "🟠"),
                ("defer",     "DEFER     (medium/low)",       "🟡"),
                ("suppress",  "SUPPRESS  (score<3 or over-triggering)", "⚪"),
            ]:
                agents_in_bucket = alloc.get(bucket, [])
                if agents_in_bucket:
                    print(f"\n  {icon} {label}:")
                    for name in agents_in_bucket:
                        ps = scored_map.get(name)
                        score_str = f"{ps.total:.1f}" if ps else "?"
                        print(f"    • {name:<12} score={score_str}")

        elif sub == "plan":
            from global_optimizer import compute_optimization_plan, print_plan
            plan = compute_optimization_plan(dry_run=True)
            print_plan(plan)

        elif sub == "apply":
            from global_optimizer import compute_optimization_plan, apply_optimization_plan, print_plan
            import db as _db2
            _db2.init()
            plan = compute_optimization_plan()
            print_plan(plan)
            if plan["promote"] or plan["suppress"]:
                confirm = input("\n  Apply these changes? (yes/no): ").strip().lower()
                if confirm == "yes":
                    result = apply_optimization_plan(plan)
                    for line in result["applied"]:
                        print(f"  ✓ {line}")
                    for line in result["skipped"]:
                        print(f"  · {line}")
                else:
                    print("  Cancelled.")
            else:
                print("  Nothing to apply.")

        elif sub == "explain":
            from global_optimizer import explain_system_state
            print(f"\n  {explain_system_state()}\n")

        else:
            print("Usage: atlas optimize [status | plan | apply | explain]")

    elif cmd == "context":
        from context.strategic_context import _print_context, update_context
        import db as _db
        _db.init()
        sub = args[1] if len(args) > 1 else "show"
        if sub == "update":
            if len(args) < 3:
                print("Usage: atlas context update '<json>'")
            else:
                try:
                    updates = json.loads(args[2])
                    update_context(updates)
                    print("  Context updated.")
                    _print_context()
                except json.JSONDecodeError as e:
                    print(f"  Invalid JSON: {e}")
        else:
            _print_context()

    elif cmd == "relationships":
        import db as _db
        _db.init()
        sub = args[1] if len(args) > 1 else "list"

        if sub == "list":
            rels = _db.get_relationships(limit=30)
            print(f"\n  Relationships ({len(rels)})\n  {'─'*56}")
            if not rels:
                print("  No relationships tracked. Add via atlas relationships or the DB.")
            for r in rels:
                risk = r.get("risk_of_decay", 0)
                icon = "HIGH" if risk >= 0.8 else "WARN" if risk >= 0.5 else "OK"
                last = (r.get("last_contact") or "never")[:10]
                print(f"  [{icon}] {r['name']:<18} [{r.get('type','?'):<8}] decay={risk:.0%}  last={last}")

        elif sub == "decay":
            rels = _db.get_decaying_relationships(threshold=0.7)
            print(f"\n  Relationships at Risk (decay > 70%)\n  {'─'*52}")
            if not rels:
                print("  No high-risk relationships. Good.")
            for r in rels:
                print(f"  [HIGH] {r['name']} [{r.get('type')}] — {r.get('risk_of_decay',0):.0%} decay  last: {(r.get('last_contact') or 'never')[:10]}")

        elif sub == "sync":
            from relationships.relationship_agent import run_pipeline
            result = run_pipeline()
            print(f"\n  {result['summary']}")
            for d in result.get("outreach_drafts", []):
                print(f"\n  [{d['name']} — decay {d['risk']:.0%}]")
                print(f"  {d['draft']}")

        else:
            print("Usage: atlas relationships [list | decay | sync]")

    elif cmd == "parenting":
        import db as _db
        _db.init()
        sub = args[1] if len(args) > 1 else "show"

        if sub == "update":
            from personal.parenting_agent import run_pipeline
            result = run_pipeline()
            print(f"\n  {result['summary']}")
        else:
            from personal.parenting_agent import _print_summary
            _print_summary()

    elif cmd == "attention":
        sub = args[1] if len(args) > 1 else "status"

        if sub == "status":
            from attention_engine import _print_status
            _print_status()

        elif sub == "log":
            from attention_engine import log_daily_attention, _print_status
            hours = 0.0
            switches = 0
            try:
                if len(args) > 2:
                    hours = float(args[2])
                if len(args) > 3:
                    switches = int(args[3])
            except ValueError:
                pass
            log_daily_attention(deep_work_hrs=hours, task_switches=switches)
            print(f"  Logged: {hours}h deep work, {switches} task switches.")
            _print_status()

        else:
            print("Usage: atlas attention [status | log <hours> [switches]]")

    elif cmd == "steward":
        import db as _db
        _db.init()
        from personal.relationship_steward_agent import run_pipeline
        result = run_pipeline()
        h = result.get("health", {})
        icon = {"low": "OK", "medium": "WARN", "high": "HIGH"}.get(h.get("risk_level", "low"), "?")
        print(f"\n  Relationship Steward\n  {'─'*48}")
        print(f"  [{icon}] Risk: {h.get('risk_level','?').upper()}")
        print(f"  Overload days (7d): {h.get('overload_days_7d', 0)}")
        print(f"  Days since date night: {h.get('days_since_date_night') or 'unknown'}")
        print(f"\n  {h.get('suggestion','')}")

    # ── Trajectory Engine ─────────────────────────────────────────
    elif cmd == "trajectory":
        import db as _db
        _db.init()
        sub = args[1] if len(args) > 1 else "status"

        if sub == "update":
            from trajectory.trajectory_engine import update_all_domains, get_system_trajectory
            print(f"\n  Trajectory: refreshing all domains...\n")
            results = update_all_domains()
            for r in results:
                if "error" in r:
                    print(f"  ✗ {r['domain']}: {r['error']}")
            traj = get_system_trajectory()
            risk_icons = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}
            trend_sym  = {"improving": "↑", "declining": "↓", "stable": "→", "unknown": "?"}
            print(f"  Overall health: {traj['overall_health']:+.3f}\n  {'─'*60}")
            for d in traj["domains"]:
                icon = risk_icons.get(d.get("risk_level", "low"), "?")
                sym  = trend_sym.get(d.get("trend_direction", "unknown"), "?")
                print(f"  {icon} {d['domain']:<18} score={d.get('trajectory_score', 0):+.2f}  "
                      f"conf={d.get('confidence_score', 0):.0%}  {sym}")

        elif sub == "status":
            from trajectory.trajectory_engine import get_system_trajectory
            traj = get_system_trajectory()
            risk_icons = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}
            trend_sym  = {"improving": "↑", "declining": "↓", "stable": "→", "unknown": "?"}
            print(f"\n  Atlas Trajectory ({traj['domain_count']} domains) — "
                  f"overall: {traj['overall_health']:+.3f}\n  {'─'*60}")
            if not traj["domains"]:
                print("  No data. Run: atlas trajectory update")
            for d in traj["domains"]:
                icon = risk_icons.get(d.get("risk_level", "low"), "?")
                sym  = trend_sym.get(d.get("trend_direction", "unknown"), "?")
                print(f"  {icon} {d['domain']:<18} score={d.get('trajectory_score', 0):+.2f}  "
                      f"conf={d.get('confidence_score', 0):.0%}  {sym}")

        elif sub == "forecast":
            from trajectory.forecast_engine import generate_trajectory_report
            print(f"\n  Atlas Trajectory Forecast\n  {'─'*60}")
            print(generate_trajectory_report())

        elif sub == "domain" and len(args) > 2:
            from trajectory.trajectory_engine import update_domain
            from trajectory.forecast_engine import project_domain
            domain = args[2]
            try:
                row = update_domain(domain)
                print(f"\n  Domain: {domain}\n  {'─'*50}")
                print(f"  Current value  : {row.get('current_value', 0)}")
                print(f"  Trajectory score: {row.get('trajectory_score', 0):+.3f}")
                print(f"  Risk level     : {row.get('risk_level', '?').upper()}")
                print(f"  Trend          : {row.get('trend_direction', '?')}")
                print(f"  Confidence     : {row.get('confidence_score', 0):.0%}")
                print(f"\n  Forecasts:")
                for h in [7, 30, 90]:
                    f = project_domain(domain, h)
                    sym = {"improving": "↑", "worsening": "↓", "stable": "→"}.get(f["risk_trajectory"], "?")
                    print(f"  {sym} {h:>3}d: {f['projected_value']}  prob={f['probability']:.0%}  "
                          f"{'[LOW CONF]' if f['suppress_escalation'] else ''}")
                    for r in f.get("reasoning", []):
                        print(f"     • {r}")
            except ValueError as e:
                print(f"  Error: {e}")

        else:
            print("Usage: atlas trajectory [status | update | forecast | domain <name>]")

    # ── Executive Digest ──────────────────────────────────────────
    elif cmd == "digest":
        import db as _db
        _db.init()
        sub = args[1] if len(args) > 1 else "morning"

        if sub == "morning":
            from attention.compression.executive_digest import generate_morning_digest
            result = generate_morning_digest()
            print(f"\n  ╔══ ATLAS MORNING DIGEST — {datetime.now().strftime('%Y-%m-%d %H:%M')} ══╗\n")
            print(result)
            print(f"\n  ╚{'═'*50}╝")

        elif sub == "evening":
            from attention.compression.executive_digest import generate_evening_digest
            result = generate_evening_digest()
            print(f"\n  ╔══ ATLAS EVENING DIGEST — {datetime.now().strftime('%Y-%m-%d %H:%M')} ══╗\n")
            print(result)
            print(f"\n  ╚{'═'*50}╝")

        elif sub == "weekly":
            from attention.compression.executive_digest import generate_weekly_digest
            result = generate_weekly_digest()
            print(f"\n  ╔══ ATLAS WEEKLY DIGEST — {datetime.now().strftime('%Y-%m-%d')} ══╗\n")
            print(result)
            print(f"\n  ╚{'═'*50}╝")

        else:
            print("Usage: atlas digest [morning | evening | weekly]")

    else:
        print(f"Atlas: Unknown command '{cmd}'. Run 'atlas help' to see all commands.")


if __name__ == "__main__":
    main()
