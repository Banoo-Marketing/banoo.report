"""
Scout — Talent & hiring pipeline sub-agent for Atlas.
Drafts JDs, screens candidates, tracks pipeline, manages outreach for Banoo Marketing roles.
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

SCOUT_SYSTEM = """You are Scout, the talent and hiring sub-agent for Atlas (Chief of Staff to Emod Vafa).

COMPANY: Banoo Inc. / Banoo Marketing
FOUNDER: Emod Vafa — digital marketing operator, 15+ years experience
TEAM: Small, offshore-heavy (Philippines team). Remote-first.
CULTURE: Output-driven, low-overhead, AI-augmented. No bureaucracy.

WHAT BANOO ACTUALLY DOES:
- Google Ads, SEO, lead generation, DSP campaigns
- Marketing automation & AI systems for SMBs
- Referral partnerships (lending, financing)
- Client base: real estate, e-commerce, service businesses

WHAT EMOD NEEDS IN EVERY HIRE:
- Self-directed, async-capable — minimal hand-holding
- Results-oriented — owns outcomes, not just tasks
- Can think AND execute — not just one
- Resourceful with AI tools — Emod's operation is AI-first
- Comfortable with fast pivots and changing priorities

WHAT EMOD DOES NOT WANT:
- Clock-watchers who need structure to function
- People who can't communicate in writing
- Generalists with no depth
- Candidates who optimize for job security over impact

COMPENSATION PHILOSOPHY:
- Base + performance (growth/results bonus structure preferred)
- Philippines team: competitive local rates (~$800-1,500 USD/month range)
- Toronto/North America: project-based or fractional before full-time
- Equity only for C-level trust situations (not early)

HIRING PIPELINE STAGES:
1. IDENTIFIED — potential candidate spotted (email, LinkedIn, referral)
2. OUTREACH — first message sent
3. SCREENING — initial conversation or questionnaire
4. INTERVIEW — structured conversation with Emod
5. OFFER — terms being discussed
6. HIRED — onboarded
7. PASSED — not a fit

Your output rules:
- Always flag what requires Emod's approval before executing
- Draft all outreach as PENDING APPROVAL — never say "sent" or "scheduled" without confirmation
- Score candidates 1-10 with clear reasoning
- Be direct — tell Emod if a role description is vague or a candidate is weak
- Track time-sensitive pipeline items (candidates going cold)"""


def _get_hiring_emails(limit: int = 60) -> list[dict]:
    if not _EMAIL_DB.exists():
        return []
    with sqlite3.connect(_EMAIL_DB) as c:
        c.row_factory = sqlite3.Row
        rows = c.execute("""
            SELECT sender, subject, date_str, date_ts, body_text, recipients
            FROM emails
            WHERE (
                sender LIKE '%linkedin%' OR sender LIKE '%indeed%'
                OR sender LIKE '%workopolis%' OR sender LIKE '%glassdoor%'
                OR sender LIKE '%recruit%' OR sender LIKE '%talent%'
                OR subject LIKE '%application%' OR subject LIKE '%job%'
                OR subject LIKE '%resume%' OR subject LIKE '%cv%'
                OR subject LIKE '%hire%' OR subject LIKE '%hiring%'
                OR subject LIKE '%position%' OR subject LIKE '%role%'
                OR subject LIKE '%candidate%' OR subject LIKE '%opportunity%'
                OR subject LIKE '%freelance%' OR subject LIKE '%contractor%'
                OR subject LIKE '%virtual assistant%' OR subject LIKE '%VA%'
            )
            ORDER BY date_ts DESC
            LIMIT ?
        """, (limit,)).fetchall()
    return [dict(r) for r in rows]


def _get_hiring_actions() -> list[dict]:
    import sys
    sys.path.insert(0, str(_CHIEF))
    import db
    all_actions = db.get_actions(status="OPEN", limit=100)
    hire_keywords = [
        "hire", "hiring", "recruit", "candidate", "job", "role", "position",
        "va", "assistant", "freelance", "contractor", "onboard", "talent"
    ]
    return [a for a in all_actions if any(
        kw in (a.get("title") or "").lower() for kw in hire_keywords
    )]


def run_pipeline_scan() -> str:
    """Full hiring pipeline scan — open roles, active candidates, stale threads."""
    emails = _get_hiring_emails(50)
    actions = _get_hiring_actions()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    actions_json = json.dumps([{
        'title': a['title'],
        'priority': a['priority'],
        'deadline': a.get('deadline'),
        'next_step': a.get('suggested_next')
    } for a in actions], indent=2)

    emails_json = json.dumps([{
        'sender': e['sender'],
        'subject': e['subject'],
        'date': e['date_str'],
        'preview': (e.get('body_text') or '')[:300]
    } for e in emails[:40]], indent=2)

    client = anthropic.Anthropic()
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2500,
        system=[{"type": "text", "text": SCOUT_SYSTEM, "cache_control": {"type": "ephemeral"}}],
        messages=[{
            "role": "user",
            "content": f"""Today is {today}. Run a full hiring pipeline scan for Banoo Marketing.

Open hiring-related action items:
{actions_json}

Hiring-related emails:
{emails_json}

Produce a structured report:
1. 🎯 OPEN ROLES — positions actively being filled
2. 👤 ACTIVE CANDIDATES — who's in pipeline and at what stage
3. ⚠️ STALE THREADS — candidates going cold (need follow-up)
4. 📋 HIRING PRIORITIES — what Banoo needs most right now
5. 🎯 RECOMMENDED NEXT ACTION — one clear step for Emod today
"""
        }],
    )
    return resp.content[0].text


def run_draft_jd(role: str, context: str = "") -> str:
    """Write a full job description for a role at Banoo Marketing."""
    client = anthropic.Anthropic()
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        system=SCOUT_SYSTEM,
        messages=[{
            "role": "user",
            "content": f"""Write a complete job description for: {role}

Additional context from Emod: {context if context else "None provided."}

Include:
1. Job title (precise, market-accurate)
2. One-sentence company description (Banoo Marketing, Emod's vision)
3. The mission of this role in 2 sentences — what success looks like
4. What you'll own (5 bullet points — outcomes, not tasks)
5. Must-have qualifications (be specific — years, tools, proof required)
6. Nice-to-haves (3 max — don't pad this)
7. Red flags / what will disqualify a candidate immediately
8. Compensation range (Toronto or Philippines as appropriate)
9. Where to post (ranked by quality for this role type)
10. First screening question (the one question that separates real candidates)

Write in Emod's voice: direct, no corporate fluff, honest about what the role is."""
        }],
    )
    return resp.content[0].text


def run_screen_candidate(candidate_info: str, role: str = "") -> str:
    """Score and assess a candidate for a role at Banoo Marketing."""
    client = anthropic.Anthropic()
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1500,
        system=SCOUT_SYSTEM,
        messages=[{
            "role": "user",
            "content": f"""Screen this candidate for Banoo Marketing.
{f'Role being filled: {role}' if role else 'Role: General assessment.'}

Candidate information:
{candidate_info}

Provide:
1. OVERALL SCORE: X/10 with one sentence rationale
2. STRENGTHS: What makes them worth interviewing (max 3)
3. GAPS: Critical missing elements (be direct)
4. GREEN FLAGS: Signals this person is high-output and self-directed
5. RED FLAGS: Signals they'll underperform or be a management burden
6. RECOMMENDATION: ADVANCE / PASS / HOLD WITH NOTE
7. If ADVANCE: draft a 3-sentence outreach message from Emod
8. If PASS: one polite rejection line Emod can send
"""
        }],
    )
    return resp.content[0].text


def run_interview_questions(role: str, candidate_context: str = "") -> str:
    """Generate a focused interview question set for a specific role and candidate."""
    client = anthropic.Anthropic()
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1500,
        system=SCOUT_SYSTEM,
        messages=[{
            "role": "user",
            "content": f"""Generate interview questions for Emod to use.

Role: {role}
{f'Candidate context: {candidate_context}' if candidate_context else ''}

Structure:
1. OPENING (2 questions) — get them talking, understand their story
2. SKILLS VALIDATION (3 questions) — proof of specific capabilities, no fluff
3. SELF-DIRECTION TEST (2 questions) — can they operate without hand-holding?
4. AI & TOOLS (1 question) — how they use AI in their workflow
5. CULTURE FIT (2 questions) — pace, pressure, async, ownership
6. DEAL-BREAKER CHECK (1 question) — the uncomfortable question that reveals truth

For each question, add: what a STRONG answer sounds like vs a WEAK answer.
Emod runs lean, direct interviews — no filler, no soft HR questions."""
        }],
    )
    return resp.content[0].text


def run_outreach_draft(candidate_name: str, role: str, platform: str = "email") -> str:
    """Draft a first-touch outreach message to a promising candidate."""
    client = anthropic.Anthropic()
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=600,
        system=SCOUT_SYSTEM,
        messages=[{
            "role": "user",
            "content": f"""Draft a first-touch outreach message from Emod to a potential candidate.

Candidate name: {candidate_name}
Role: {role}
Platform: {platform}

Write a message that:
- Is honest about the company and role (small, fast-moving, remote)
- Respects the candidate's time — gets to the point in 3-4 sentences
- Feels like Emod wrote it (direct, no corporate BS, clear about the opportunity)
- Ends with a specific, low-friction call to action
- Is NOT a form letter — sounds like a real person reaching out

Keep it under 100 words. Flag as PENDING EMOD'S APPROVAL before sending."""
        }],
    )
    return resp.content[0].text


def run_role_teardown(role: str) -> str:
    """Break down a role into core outcomes, ideal profile, and sourcing strategy."""
    client = anthropic.Anthropic()
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1200,
        system=SCOUT_SYSTEM,
        messages=[{
            "role": "user",
            "content": f"""Do a full teardown of this role before we start hiring for it.

Role: {role}

Answer these before writing any JD or sourcing:
1. PROBLEM THIS SOLVES: What specific pain goes away when this person is hired?
2. SUCCESS METRICS: How do you know in 90 days it was the right hire?
3. SCOPE CREEP RISK: What are they likely to drift into vs stay focused on?
4. FULL-TIME vs FRACTIONAL vs CONTRACTOR: Which model fits best and why?
5. OFFSHORE vs NORTH AMERICA: Where does this role actually need to sit?
6. COST RANGE: What's the realistic monthly budget?
7. WHERE TO FIND THEM: Top 3 sourcing channels for this specific profile
8. ONE THING MOST JDs GET WRONG for this role type

Be direct. If the role doesn't actually need to be filled yet, say so."""
        }],
    )
    return resp.content[0].text


if __name__ == "__main__":
    import sys
    args = sys.argv[1:]
    cmd = args[0] if args else "scan"

    if cmd == "scan":
        print("\n  Scout: Hiring pipeline scan\n")
        print("  " + "─" * 60)
        print(run_pipeline_scan())
    elif cmd == "jd" and len(args) > 1:
        role = args[1]
        context = args[2] if len(args) > 2 else ""
        print(f"\n  Scout: Job description — {role}\n")
        print("  " + "─" * 60)
        print(run_draft_jd(role, context))
    elif cmd == "screen" and len(args) > 1:
        role = args[2] if len(args) > 2 else ""
        print(f"\n  Scout: Candidate screen\n")
        print("  " + "─" * 60)
        print(run_screen_candidate(args[1], role))
    elif cmd == "questions" and len(args) > 1:
        candidate_ctx = args[2] if len(args) > 2 else ""
        print(f"\n  Scout: Interview questions — {args[1]}\n")
        print("  " + "─" * 60)
        print(run_interview_questions(args[1], candidate_ctx))
    elif cmd == "outreach" and len(args) > 2:
        platform = args[3] if len(args) > 3 else "email"
        print(f"\n  Scout: Outreach draft for {args[1]}\n")
        print("  " + "─" * 60)
        print(run_outreach_draft(args[1], args[2], platform))
    elif cmd == "teardown" and len(args) > 1:
        print(f"\n  Scout: Role teardown — {args[1]}\n")
        print("  " + "─" * 60)
        print(run_role_teardown(args[1]))
    else:
        print("Usage: scout.py [scan | jd <role> [context] | screen <candidate_info> [role] |")
        print("                 questions <role> [candidate_context] | outreach <name> <role> [platform] |")
        print("                 teardown <role>]")
