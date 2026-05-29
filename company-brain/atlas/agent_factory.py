"""
agent_factory.py — Atlas Agent Factory.

Scans for repetitive patterns in email/actions/calendar data.
Generates agent specs for automation candidates.
Registers approved agents in the workforce registry.

Usage:
  python agent_factory.py scan         # Scan for automation candidates
  python agent_factory.py register     # Register all native sub-agents
  python agent_factory.py list         # List registered agents
  python agent_factory.py kill <name>  # Kill a registered agent
"""
import json
import sqlite3
import sys
from datetime import date, timedelta
from pathlib import Path

_HERE = Path(__file__).parent
_CHIEF = _HERE.parent / "chief"
_EMAIL_DB = _HERE.parent / "email-analyzer" / "email_cache.db"

sys.path.insert(0, str(_CHIEF))
sys.path.insert(0, str(_HERE))

try:
    from dotenv import load_dotenv
    load_dotenv(_HERE.parent.parent / "company-brain" / ".env")
    load_dotenv(_HERE / ".env")
except ImportError:
    pass

import anthropic
import db

FACTORY_SYSTEM = """You are Atlas Agent Factory — the automation detection engine.

Your job: analyze patterns in email, actions, and calendar data, then generate agent specs for recurring tasks.

AGENT CREATION CRITERIA (all 3 must be true):
- REPETITION: same task occurs 2+ times/week OR predictable monthly cycle
- LOW VARIANCE: clear rules, minimal judgment, predictable inputs/outputs
- ROI > 2h/week saved OR reduces decision fatigue OR improves revenue flow

DO NOT create agents for:
- Strategic decisions (require human judgment)
- Relationship management (require Emod's personal touch)
- Creative work (require context + judgment)
- One-off tasks

OUTPUT: Return JSON only. No explanation. No markdown fences.

Agent spec schema:
{
  "name": "agent_name_snake_case",
  "purpose": "One sentence — what problem this solves",
  "scope": "Narrow: what this agent ONLY does",
  "inputs": ["email_cache", "chief.db.actions", "calendar_events"],
  "outputs": {
    "type": "report | alert | update | draft",
    "format": "what the output looks like",
    "frequency": "daily | weekly | monthly | triggered"
  },
  "frequency": "daily | weekly | monthly | triggered",
  "rules": {
    "trigger_conditions": ["..."],
    "decision_rules": ["..."],
    "hard_constraints": ["..."]
  },
  "escalation_rules": {
    "escalate_if": ["..."],
    "suppress_if": ["..."],
    "escalation_threshold": "description"
  },
  "success_metric": "How to know this agent is working",
  "hours_saved_weekly": 0,
  "system_prompt": "You are [agent name]..."
}"""


SCAN_SYSTEM = """You are Atlas pattern detection scanner.

Analyze email/action/calendar data and identify tasks that are:
1. Repetitive (same pattern 2+ times/week or monthly)
2. Low strategic variance (clear rules, predictable)
3. Worth automating (>2h/week saved, or reduces decision fatigue)

OUTPUT: Return JSON array of candidates. No explanation.

[
  {
    "pattern": "What the repetitive task is",
    "evidence": "How many times seen, from what sources",
    "frequency": "How often it repeats",
    "suggested_agent": "What kind of agent would handle this",
    "hours_saved_weekly": 0,
    "roi_justification": "Why this is worth automating"
  }
]"""


def _get_pattern_data() -> dict:
    """Gather raw data for pattern detection."""
    data = {"email_patterns": [], "action_patterns": [], "calendar_patterns": []}

    # Email patterns: frequent senders + subject themes
    if _EMAIL_DB.exists():
        with sqlite3.connect(_EMAIL_DB) as c:
            # Top recurring senders
            rows = c.execute("""
                SELECT sender, COUNT(*) as cnt,
                       GROUP_CONCAT(DISTINCT substr(subject,1,40)) as subjects
                FROM emails
                WHERE date_ts > strftime('%s','now','-30 days')
                GROUP BY lower(sender)
                ORDER BY cnt DESC
                LIMIT 30
            """).fetchall()
            data["email_patterns"] = [
                {"sender": r[0], "count_30d": r[1], "sample_subjects": r[2]}
                for r in rows
            ]

            # Recurring subject patterns
            subject_rows = c.execute("""
                SELECT substr(subject,1,50) as subj_prefix, COUNT(*) as cnt
                FROM emails
                WHERE date_ts > strftime('%s','now','-60 days')
                GROUP BY lower(substr(subject,1,30))
                HAVING cnt >= 3
                ORDER BY cnt DESC
                LIMIT 20
            """).fetchall()
            data["recurring_subjects"] = [
                {"prefix": r[0], "count": r[1]} for r in subject_rows
            ]

    # Action patterns: recurring action types
    db.init()
    all_actions = db.get_actions(status="OPEN", limit=100)
    action_type_counts = {}
    for a in all_actions:
        t = a.get("action_type", "task")
        action_type_counts[t] = action_type_counts.get(t, 0) + 1
    data["action_patterns"] = [
        {"type": k, "count": v} for k, v in sorted(action_type_counts.items(), key=lambda x: -x[1])
    ]

    # What agents are already registered
    existing = db.get_agents("active")
    data["existing_agents"] = [a["name"] for a in existing]

    return data


def scan_for_candidates() -> list[dict]:
    """Scan data sources for automation candidates. Returns list of patterns."""
    data = _get_pattern_data()
    client = anthropic.Anthropic()
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        system=SCAN_SYSTEM,
        messages=[{
            "role": "user",
            "content": f"""Analyze this data for automation candidates.
Do not suggest agents that already exist: {data['existing_agents']}

Email patterns (last 30 days):
{json.dumps(data['email_patterns'][:15], indent=2)}

Recurring subjects:
{json.dumps(data['recurring_subjects'][:10], indent=2)}

Action type distribution:
{json.dumps(data['action_patterns'], indent=2)}

Return JSON array of candidates only."""
        }],
    )
    try:
        text = resp.content[0].text.strip()
        if text.startswith("["):
            return json.loads(text)
        import re
        match = re.search(r'\[.*\]', text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
    except Exception:
        pass
    return []


def generate_agent_spec(candidate: dict) -> dict:
    """Generate a full agent spec for a candidate pattern."""
    client = anthropic.Anthropic()
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1500,
        system=FACTORY_SYSTEM,
        messages=[{
            "role": "user",
            "content": f"""Generate a complete agent spec for this automation candidate:

{json.dumps(candidate, indent=2)}

Context: This agent serves Emod Vafa's AI Chief of Staff system (Atlas).
Available data sources: email_cache (SQLite), chief.db (contacts/actions/calendar), memory JSON files.

Return the agent spec JSON only."""
        }],
    )
    import re
    text = resp.content[0].text.strip()
    try:
        if text.startswith("{"):
            return json.loads(text)
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
    except Exception:
        pass
    return {"error": "spec generation failed", "raw": text[:300]}


def register_native_agents():
    """Register all existing Python sub-agents in the agent registry."""
    db.init()
    native_agents = [
        {
            "name": "pulse",
            "purpose": "Monitor client health, flag churn risk, draft check-ins",
            "agent_type": "native",
            "native_module": "pulse",
            "native_fn": "run_client_health_scan",
            "scope": "Banoo Marketing clients only (AngeLink, 416 Flowers, Pro Insulation, Azira, Lodestar)",
            "inputs": ["email_cache", "chief.db.actions"],
            "outputs": {"type": "report", "format": "health scores + actions", "frequency": "weekly"},
            "frequency": "weekly",
            "rules": {"escalate_if": ["client 🔴 AT RISK", "no contact >30 days", "payment overdue"]},
            "escalation_rules": {
                "escalate_if": ["client at risk of churn", "payment issue", "relationship breakdown"],
                "suppress_if": ["routine status update", "all clients GREEN"]
            },
            "success_metric": "Zero churn events per quarter",
        },
        {
            "name": "broker",
            "purpose": "Monitor real estate portfolio, tenant issues, and licensing deadlines",
            "agent_type": "native",
            "native_module": "broker",
            "native_fn": "run_property_scan",
            "scope": "218 Wilfred Ave, 8888 Yonge #0627, Markham property + TRREB/OREA compliance",
            "inputs": ["email_cache", "chief.db.actions"],
            "outputs": {"type": "report", "format": "property status + urgent actions", "frequency": "weekly"},
            "frequency": "weekly",
            "rules": {"escalate_if": ["tenant legal issue", "payment overdue", "OREA deadline"]},
            "escalation_rules": {
                "escalate_if": ["legal matter", "financial deadline", "tenant dispute", "urgent maintenance"],
                "suppress_if": ["routine status", "no new activity"]
            },
            "success_metric": "No missed legal/financial deadlines",
        },
        {
            "name": "ledger",
            "purpose": "Track invoices, commissions, domain renewals, mortgage, and banking",
            "agent_type": "native",
            "native_module": "ledger",
            "native_fn": "run_financial_scan",
            "scope": "Banoo Inc finances: RBC, TD, Questrade, domains, mortgage, commissions",
            "inputs": ["email_cache", "chief.db.actions"],
            "outputs": {"type": "report", "format": "financial snapshot + overdue items", "frequency": "weekly"},
            "frequency": "weekly",
            "rules": {"escalate_if": ["payment overdue", "low balance", "domain expiring", "commission pending"]},
            "escalation_rules": {
                "escalate_if": ["overdue payment", "low RBC balance", "domain expiry <30 days", "commission >$500 pending"],
                "suppress_if": ["all payments current", "no anomalies"]
            },
            "success_metric": "Zero missed payments, all commissions tracked",
        },
        {
            "name": "relay",
            "purpose": "Scan inbox for emails needing replies, draft responses for approval",
            "agent_type": "native",
            "native_module": "relay",
            "native_fn": "run_inbox_scan",
            "scope": "Incoming email requiring human response (not automated notifications)",
            "inputs": ["email_cache"],
            "outputs": {"type": "draft", "format": "reply drafts flagged SEND/REVIEW/PERSONALISE", "frequency": "daily"},
            "frequency": "daily",
            "rules": {"escalate_if": ["urgent reply needed", "client complaint", "legal/financial email"]},
            "escalation_rules": {
                "escalate_if": ["client urgent", "payment request", "legal notice", "opportunity with 48h window"],
                "suppress_if": ["routine inquiry", "newsletter", "automated notification"]
            },
            "success_metric": "No email left unanswered >48 hours",
        },
        {
            "name": "scout",
            "purpose": "Manage hiring pipeline, screen candidates, draft outreach for Banoo roles",
            "agent_type": "native",
            "native_module": "scout",
            "native_fn": "run_pipeline_scan",
            "scope": "Banoo Marketing talent acquisition pipeline",
            "inputs": ["email_cache", "chief.db.actions"],
            "outputs": {"type": "report", "format": "pipeline status + candidate recommendations", "frequency": "weekly"},
            "frequency": "weekly",
            "rules": {"escalate_if": ["strong candidate identified", "candidate going cold", "role urgent"]},
            "escalation_rules": {
                "escalate_if": ["high-fit candidate available", "candidate response needed within 48h"],
                "suppress_if": ["no active pipeline", "routine status"]
            },
            "success_metric": "No candidates go cold without outreach",
        },
        {
            "name": "relationship",
            "purpose": "Detect relationship decay, generate personalized outreach drafts",
            "agent_type": "native",
            "native_module": "relationships.relationship_agent",
            "native_fn": "run_pipeline",
            "scope": "relationship_memory table",
            "inputs": ["relationship_memory"],
            "outputs": {"outreach_drafts": "list", "decay_alerts": "list"},
            "frequency": "daily",
            "rules": {"max_outreach_per_run": 3},
            "escalation_rules": {"decay_threshold": 0.85, "priority_types": ["client", "family"]},
            "success_metric": "relationship decay rate < 20% of contacts",
        },
        {
            "name": "parenting",
            "purpose": "Track Diyar + Dario developmental milestones, recommend weekly activities",
            "agent_type": "native",
            "native_module": "personal.parenting_agent",
            "native_fn": "run_pipeline",
            "scope": "child_profiles table",
            "inputs": ["child_profiles"],
            "outputs": {"developmental_summaries": "list", "activity_recommendations": "list"},
            "frequency": "weekly",
            "rules": {},
            "escalation_rules": {},
            "success_metric": "weekly activity recommendations current",
        },
        {
            "name": "relationship_steward",
            "purpose": "Protect Emod-Sahar relationship, monitor workload vs family balance",
            "agent_type": "native",
            "native_module": "personal.relationship_steward_agent",
            "native_fn": "run_pipeline",
            "scope": "attention_log + strategic_context",
            "inputs": ["attention_log", "strategic_context"],
            "outputs": {"marriage_health": "dict", "suggestion": "str"},
            "frequency": "weekly",
            "rules": {"never_creates_email": True},
            "escalation_rules": {"risk_level": "high"},
            "success_metric": "risk_level stays low or medium",
        },
        {
            "name": "revenue_continuity",
            "purpose": "Prevent silent client churn via contextual lightweight touchpoints",
            "agent_type": "native",
            "native_module": "revenue_continuity_agent",
            "native_fn": "run_pipeline",
            "scope": "relationship_memory (clients)",
            "inputs": ["relationship_memory", "contacts"],
            "outputs": {"touchpoints": "list", "quiet_clients": "list"},
            "frequency": "weekly",
            "rules": {"max_touchpoints_per_run": 3},
            "escalation_rules": {"high_value_silent_days": 60},
            "success_metric": "no high-value client silent > 45 days",
        },
    ]

    for spec in native_agents:
        agent_id = db.register_agent(spec)
        print(f"  Registered: {spec['name']} (id={agent_id})")

    return len(native_agents)


def list_agents():
    db.init()
    active = db.get_agents("active")
    killed = db.get_agents("killed")
    print(f"\n  Agent Workforce ({len(active)} active, {len(killed)} killed)\n")
    print(f"  {'─'*60}")
    for a in active:
        runs = a.get("run_count", 0)
        exc = a.get("exception_count", 0)
        last = (a.get("last_run") or "never")[:16]
        atype = "native" if a.get("agent_type") == "native" else "generated"
        print(f"  {'🔵' if atype=='native' else '🟣'} {a['name']:<20} [{a['frequency']}] runs:{runs} exc:{exc} last:{last}")
        if a.get("purpose"):
            print(f"     {a['purpose'][:70]}")
    if killed:
        print(f"\n  Killed agents ({len(killed)}):")
        for a in killed:
            print(f"    ✕ {a['name']} — {a.get('kill_reason','')[:50]}")


def run_factory_scan() -> list[dict]:
    """Full scan → detect → generate specs → present for approval."""
    print("\n  Agent Factory: Scanning for automation candidates...\n")
    candidates = scan_for_candidates()

    if not candidates:
        print("  No new automation candidates detected.")
        return []

    print(f"  Found {len(candidates)} candidate(s):\n")
    specs = []
    for i, c in enumerate(candidates[:5]):
        print(f"  {i+1}. {c.get('pattern','?')} ({c.get('frequency','?')})")
        print(f"     Evidence: {c.get('evidence','')[:80]}")
        print(f"     Est. savings: {c.get('hours_saved_weekly',0)}h/wk")
        print(f"     → {c.get('suggested_agent','')}")
        print()

        spec = generate_agent_spec(c)
        if "error" not in spec:
            specs.append(spec)

    if specs:
        print(f"  Generated {len(specs)} agent spec(s). Review below:")
        for s in specs:
            print(f"\n  ── {s.get('name','?')} ──")
            print(f"  Purpose: {s.get('purpose','')}")
            print(f"  Scope: {s.get('scope','')}")
            print(f"  Frequency: {s.get('frequency','')}")
            print(f"  Hours saved: {s.get('hours_saved_weekly',0)}/wk")
            print(f"  Success metric: {s.get('success_metric','')}")
        print(f"\n  ⚠️  PENDING EMOD'S APPROVAL — run 'atlas factory approve' to register")
        # Save pending specs to file
        pending_path = _HERE / "dashboard" / "pending_agents.json"
        pending_path.write_text(json.dumps(specs, indent=2, default=str))

    return specs


if __name__ == "__main__":
    db.init()
    args = sys.argv[1:]
    cmd = args[0] if args else "help"

    if cmd == "register":
        n = register_native_agents()
        print(f"\n  Agent Factory: {n} native agents registered.")
    elif cmd == "scan":
        run_factory_scan()
    elif cmd == "list":
        list_agents()
    elif cmd == "kill" and len(args) > 1:
        reason = args[2] if len(args) > 2 else ""
        db.kill_agent(args[1], reason)
        print(f"  Agent '{args[1]}' killed.")
    else:
        print("Usage: agent_factory.py [register | scan | list | kill <name> [reason]]")
