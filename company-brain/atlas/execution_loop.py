"""
Execution Loop — Weekly & daily operating rhythm for Atlas.
Implements: DAILY START, EXECUTE MODE, REALIGN, PIPELINE CHECK, KILL REVIEW,
            WEEK START, WEEK REVIEW, REALITY CHECK
"""
import json
import sqlite3
from datetime import datetime, timezone, date, timedelta
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
import sys
sys.path.insert(0, str(_CHIEF))
import db

INCOME_TARGET = 15000.0

LOOP_SYSTEM = """You are Atlas, Chief of Staff to Emod Vafa. You are running the Weekly Execution Loop.

YOUR ROLE IN THIS LOOP:
- Execution governor, not motivational speaker
- Force prioritization, not options
- Identify constraints, not opportunities
- Kill weak work, protect strong work
- Output: decisions, tasks, numbers — not advice

HARD RULES:
- Max 3 active initiatives at any time
- Max 3 daily tasks
- At least 1 thing killed every week
- Revenue > pipeline > system building > everything else
- No passive planning — planning only if execution starts within 7 days

OUTPUT FORMAT (always):
Diagnosis → Constraint → Decision → Next steps (max 5) → Risk

Be short. Be direct. No fluff. No motivation. No praise.
If something is failing, say it clearly."""


def _week_start() -> str:
    today = date.today()
    return (today - timedelta(days=today.weekday())).isoformat()


def _get_context() -> dict:
    db.init()
    streams = db.get_revenue_streams("active")
    initiatives = db.get_initiatives("active")
    killed = db.get_initiatives("killed")
    queue = db.get_daily_queue()
    weekly = db.get_weekly_metrics(4)
    pipeline = db.get_pipeline_metrics(4)
    actions_open = db.get_actions(status="OPEN", priority="HIGH", limit=10)
    today = date.today().isoformat()
    mrr = sum(s.get("monthly_revenue", 0) for s in streams)
    gap = INCOME_TARGET - mrr
    return {
        "today": today,
        "week_start": _week_start(),
        "mrr": mrr,
        "income_target": INCOME_TARGET,
        "gap": gap,
        "revenue_streams": streams,
        "active_initiatives": initiatives,
        "killed_initiatives_count": len(killed),
        "daily_queue": queue,
        "weekly_metrics": weekly[:2] if weekly else [],
        "pipeline_metrics": pipeline[:2] if pipeline else [],
        "high_priority_actions": [{"title": a["title"], "from": a.get("from_name")} for a in actions_open],
    }


def _call_atlas(prompt: str, max_tokens: int = 1500) -> str:
    ctx = _get_context()
    client = anthropic.Anthropic()
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=max_tokens,
        system=[{"type": "text", "text": LOOP_SYSTEM, "cache_control": {"type": "ephemeral"}}],
        messages=[{
            "role": "user",
            "content": f"Live system data:\n{json.dumps(ctx, indent=2, default=str)}\n\n---\n{prompt}"
        }],
    )
    return resp.content[0].text


def run_daily_start() -> str:
    """DAILY START — Context reset, today's 3 tasks, active bottleneck."""
    return _call_atlas("""DAILY START command triggered.

Produce the morning context reset for Emod:

1. REVENUE OBJECTIVE TODAY
   Single number. What revenue-generating action matters most today?

2. TODAY'S 3 PRIORITY TASKS (maximum 3)
   Each must pass: generates revenue / moves pipeline / builds system / completable today.
   Format: Task | Expected outcome | Revenue impact (direct/indirect/none)

3. ACTIVE BOTTLENECK
   What single constraint is most limiting growth right now?

4. FOCUS LOAD CHECK
   Are there more than 3 active initiatives? If yes: name which one to kill or pause.

5. ONE NUMBER TO HIT TODAY
   Specific, measurable, achievable today.

No options. No suggestions. Directives only.""")


def run_realign() -> str:
    """REALIGN — Re-prioritize, identify bottleneck, reduce scope, reset plan."""
    return _call_atlas("""REALIGN command triggered. Emod is stuck or has drifted.

Immediate diagnosis:
1. WHAT ACTUALLY HAPPENED — based on pipeline and weekly data, what stalled?
2. CONSTRAINT — single most blocking issue right now
3. SCOPE REDUCTION — what to remove/pause immediately
4. RESET PLAN — new top 3 tasks, with rationale
5. ONE FORCING QUESTION — the question Emod must answer before proceeding

Intervene directly. Do not soften the diagnosis.""", max_tokens=1000)


def run_pipeline_check() -> str:
    """PIPELINE CHECK — Leads, deals, conversion stages, next actions."""
    return _call_atlas("""PIPELINE CHECK command triggered.

Output pipeline status report:

1. FUNNEL SNAPSHOT (use actual numbers from system data)
   Leads → Calls → Proposals → Closed
   Identify where the drop-off is heaviest.

2. CONVERSION RATE HEALTH
   GREEN / YELLOW / RED with specific numbers.

3. REVENUE VELOCITY
   At current rate, what MRR will be 30 days from now?

4. PIPELINE GAPS
   What is missing from the pipeline right now?

5. NEXT 3 PIPELINE ACTIONS
   Specific. Timed. Named if possible.

If pipeline data is empty: output exactly that as a RED flag and recommend immediate action.""", max_tokens=1000)


def run_kill_review() -> str:
    """KILL REVIEW — What must stop immediately, why, ROI loss avoided."""
    return _call_atlas("""KILL REVIEW command triggered.

Produce the kill list:

1. WHAT MUST STOP IMMEDIATELY
   Based on active initiatives, revenue streams, and open actions.
   Rank by: lowest ROI + highest time cost + least aligned with main machine.

2. KILL RATIONALE FOR EACH
   Specific: why this particular thing, what the cost of NOT killing it is.

3. ROI FREED BY KILLING
   Time hours recovered per week if each is killed.

4. WHAT TO DO INSTEAD
   Redirect that freed capacity to: [specific higher-ROI action].

Atlas rule: if nothing is being killed, scope has already crept. Force at least 1 kill.
Be direct. Name names. Kill what isn't working.""", max_tokens=1000)


def run_week_start() -> str:
    """WEEK START — Weekly target, 2 growth engines, 1 system build, focus constraints."""
    return _call_atlas("""WEEK START command triggered. Beginning Single-Thread Sprint.

Produce the weekly operating plan:

1. REVENUE TARGET (hard number)
   What specific amount should be closed or confirmed this week?

2. PRIMARY GROWTH ENGINE
   One initiative. All energy goes here first.
   Name it. Define the weekly output expected from it.

3. SECONDARY SUPPORT ENGINE
   One supporting activity (pipeline, nurture, system).
   Maximum 5 hours/week. Define the specific task.

4. SYSTEM BUILD TARGET
   One specific system improvement this week.
   What gets more automated or delegated?

5. FOCUS CONSTRAINTS
   What is explicitly NOT allowed this week?
   Name the distractions Emod is most likely to drift toward.

6. WEEK KILL REQUIREMENT
   What must be killed or paused before this week ends? (Non-optional.)

7. SUCCESS DEFINITION
   How do we know this week was a win? (3 metrics max)

Output a tight execution brief, not a plan document.""", max_tokens=1500)


def run_week_review() -> str:
    """WEEK REVIEW — Performance report, revenue analysis, kill list, next week plan."""
    return _call_atlas("""WEEK REVIEW command triggered. Weekly closeout.

Produce the weekly review report:

1. REVENUE SUMMARY
   - Revenue produced vs target
   - Conversion rate changes (if pipeline data exists)
   - Pipeline velocity trend

2. FOCUS REPORT
   - Active initiatives count (GREEN if ≤2, YELLOW if 3, RED if >3)
   - Initiatives killed this cycle
   - Focus score trend

3. SYSTEM PROGRESS
   - What improved or automated this week
   - Automation ratio direction (improving / degrading)

4. BOTTLENECK SHIFT
   - Was last week's constraint resolved?
   - New constraint for next week

5. KILL MANDATE
   - What MUST be killed before next week starts (required, not optional)

6. NEXT WEEK'S PRIMARY FOCUS
   One sentence. One initiative. One revenue target.

7. BRUTAL ASSESSMENT
   Rate this week: 1-10 with one sentence of reasoning.
   No softening.

Use actual data from the system. Flag where data is missing.""", max_tokens=1500)


def run_reality_check() -> str:
    """REALITY CHECK — Brutally evaluate if strategy matches execution."""
    return _call_atlas("""REALITY CHECK command triggered.

Brutal strategic audit. No comfort. No softening.

1. STRATEGY vs EXECUTION GAP
   Is what Emod says he's doing matching what the data shows he's doing?
   Be specific. Use numbers.

2. FOCUS FRAGMENTATION SCORE
   How many things are actually running? Is it the right number?

3. REVENUE REALITY
   At current trajectory, when does he hit $15k/month?
   What would need to change to accelerate that?

4. OVEREXTENSION DIAGNOSIS
   What is being attempted that should be stopped?
   What is being avoided that should be started?

5. SOVEREIGNTY CHECK
   Is the current path increasing or decreasing autonomy/sovereignty?

6. HARD QUESTION EMOD MUST ANSWER
   The single most important strategic question he is currently avoiding.

7. ATLAS VERDICT
   In 2 sentences: what is the most honest assessment of where things stand?

This is not a motivational review. It is an operational audit.
Tell the truth.""", max_tokens=1500)


def run_execute_mode(update: str = "") -> str:
    """EXECUTE MODE — Monitor execution, enforce focus, block distractions."""
    context = f"\nEmod's update: {update}" if update else ""
    return _call_atlas(f"""EXECUTE MODE triggered.{context}

Emod is in execution. Monitor and enforce:

1. EXECUTION STATUS
   Based on today's queue: what is done, what is pending, what is blocked?

2. SCOPE CHECK
   Is anything outside the 3 queued tasks happening? Flag it.

3. BOTTLENECK
   What is the single thing blocking forward movement right now?

4. MICRO-DECISION
   If blocked: one specific decision that unblocks progress.

5. MOMENTUM CHECK
   Is momentum increasing or decreasing? What is the signal?

Keep it tight. This is a status check, not a planning session.""", max_tokens=800)


if __name__ == "__main__":
    import sys as _sys
    args = _sys.argv[1:]
    cmd = args[0] if args else "help"

    _divider = "\n  " + "─" * 60 + "\n"

    dispatch = {
        "daily-start": (run_daily_start, "Daily Start — Context reset + today's 3 tasks"),
        "realign":     (run_realign,     "Realign — Re-prioritize, reduce scope, reset"),
        "pipeline":    (run_pipeline_check, "Pipeline Check — Funnel status + next actions"),
        "kill-review": (run_kill_review, "Kill Review — What must stop + ROI freed"),
        "week-start":  (run_week_start,  "Week Start — Single-Thread Sprint plan"),
        "week-review": (run_week_review, "Week Review — Closeout report"),
        "reality-check":(run_reality_check,"Reality Check — Brutal strategic audit"),
        "execute":     (lambda: run_execute_mode(args[1] if len(args)>1 else ""), "Execute Mode — Focus enforcement"),
    }

    if cmd in dispatch:
        fn, title = dispatch[cmd]
        print(f"\n  Atlas Execution Loop: {title}{_divider}")
        print(fn())
        print()
    else:
        print("Atlas Execution Loop commands:")
        for k, (_, title) in dispatch.items():
            print(f"  atlas {k:<18} — {title}")
