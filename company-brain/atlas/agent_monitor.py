"""
agent_monitor.py — Atlas Control Tower: Agent Monitor.

Runs all registered agents, aggregates outputs, applies escalation rules,
and surfaces only exceptions to the CEO interface.

Usage:
  python agent_monitor.py run          # Run all active agents
  python agent_monitor.py run <name>   # Run a specific agent
  python agent_monitor.py status       # Show last-run summary
  python agent_monitor.py escalations  # Show pending escalations
"""
import importlib
import json
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

_HERE = Path(__file__).parent
_CHIEF = _HERE.parent / "chief"

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

TRIAGE_SYSTEM = """You are Atlas Control Tower triage engine.

Given an agent's raw output, determine:
1. Does this require Emod's attention? (YES / NO)
2. What is the escalation reason? (one sentence, or null)
3. What is the urgency level? (CRITICAL / HIGH / NORMAL)
4. What single action, if any, should Emod take?

Escalate only if:
- Revenue risk (payment overdue, client at risk, commission pending >$500)
- Legal/compliance deadline within 7 days
- Opportunity requiring decision within 48h
- Relationship breakdown or urgent client issue
- Critical system failure or anomaly

Suppress if:
- All systems normal
- Routine status update with no action needed
- Metrics within expected range

Return JSON only. No explanation.

{
  "needs_attention": true,
  "urgency": "CRITICAL | HIGH | NORMAL",
  "escalation_reason": "One sentence or null",
  "recommended_action": "What Emod should do, or null",
  "summary": "2-3 sentence summary of what the agent found"
}"""


def _run_native_agent(agent: dict) -> dict:
    """Run a native Python module agent and return its output."""
    module_name = agent.get("native_module")
    fn_name = agent.get("native_fn")

    if not module_name or not fn_name:
        return {"error": "Missing native_module or native_fn", "raw": ""}

    try:
        module = importlib.import_module(module_name)
        fn = getattr(module, fn_name)
        result = fn()
        return {"raw": result if isinstance(result, str) else json.dumps(result, default=str)}
    except Exception as e:
        return {"error": str(e), "traceback": traceback.format_exc(), "raw": ""}


def _triage_output(agent_name: str, raw_output: str) -> dict:
    """Ask Claude to triage the agent output — escalate or suppress."""
    if not raw_output or raw_output.strip() == "":
        return {
            "needs_attention": False,
            "urgency": "NORMAL",
            "escalation_reason": None,
            "recommended_action": None,
            "summary": f"{agent_name} ran but produced no output."
        }

    client = anthropic.Anthropic()
    try:
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=500,
            system=TRIAGE_SYSTEM,
            messages=[{
                "role": "user",
                "content": f"Agent: {agent_name}\n\nOutput:\n{raw_output[:3000]}"
            }]
        )
        text = resp.content[0].text.strip()
        if text.startswith("{"):
            return json.loads(text)
        import re
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
    except Exception:
        pass

    return {
        "needs_attention": True,
        "urgency": "NORMAL",
        "escalation_reason": "Triage failed — manual review needed",
        "recommended_action": None,
        "summary": raw_output[:200]
    }


def run_agent(agent: dict) -> dict:
    """Run a single agent and log its output. Returns triage result."""
    name = agent["name"]
    agent_type = agent.get("agent_type", "generated")

    print(f"  Running {name}...", end=" ", flush=True)

    # Run the agent
    if agent_type == "native":
        result = _run_native_agent(agent)
    else:
        # Generated agents: run via stored system_prompt + data context
        result = _run_generated_agent(agent)

    raw = result.get("raw", "")
    error = result.get("error")

    if error:
        print(f"ERROR: {error[:60]}")
        triage = {
            "needs_attention": True,
            "urgency": "HIGH",
            "escalation_reason": f"Agent error: {error[:100]}",
            "recommended_action": "Investigate agent failure",
            "summary": f"{name} failed with error: {error}"
        }
        db.log_agent_output(
            agent_name=name,
            output=f"ERROR: {error}",
            exceptions=result.get("traceback", error),
            has_escalation=True,
            escalation_reason=triage["escalation_reason"]
        )
        db.update_agent_last_run(name, output=f"ERROR: {error}", exception=True)
        return triage

    # Triage the output
    triage = _triage_output(name, raw)
    needs_attention = triage.get("needs_attention", False)

    status_icon = "🔴" if triage.get("urgency") == "CRITICAL" else "🟡" if needs_attention else "🟢"
    print(f"{status_icon} {'ESCALATED' if needs_attention else 'OK'}")

    db.log_agent_output(
        agent_name=name,
        output=raw,
        exceptions=None,
        has_escalation=needs_attention,
        escalation_reason=triage.get("escalation_reason")
    )
    db.update_agent_last_run(name, output=raw, exception=False)

    triage["agent_name"] = name
    triage["raw_output"] = raw
    return triage


def _run_generated_agent(agent: dict) -> dict:
    """Run a generated (non-native) agent using its stored system_prompt."""
    system_prompt = agent.get("system_prompt", "")
    if not system_prompt:
        return {"error": "No system_prompt defined for generated agent", "raw": ""}

    # Pull relevant data based on agent inputs
    inputs = agent.get("inputs", [])
    context_parts = []

    if "email_cache" in json.dumps(inputs):
        try:
            import sqlite3
            email_db = _HERE.parent / "email-analyzer" / "email_cache.db"
            if email_db.exists():
                with sqlite3.connect(email_db) as c:
                    rows = c.execute("""
                        SELECT sender, subject, date_ts
                        FROM emails
                        ORDER BY date_ts DESC LIMIT 20
                    """).fetchall()
                    context_parts.append(f"Recent emails:\n" + "\n".join(
                        f"  {r[0]} | {r[1][:50]}" for r in rows
                    ))
        except Exception:
            pass

    if "chief.db" in json.dumps(inputs):
        try:
            actions = db.get_actions(status="OPEN", limit=20)
            context_parts.append(f"Open actions ({len(actions)}):\n" + "\n".join(
                f"  [{a.get('priority','?')}] {a.get('title','?')[:60]}" for a in actions[:10]
            ))
        except Exception:
            pass

    context = "\n\n".join(context_parts) if context_parts else "No context data available."

    client = anthropic.Anthropic()
    try:
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1500,
            system=system_prompt,
            messages=[{
                "role": "user",
                "content": f"Run your scan now.\n\nContext:\n{context}"
            }]
        )
        return {"raw": resp.content[0].text}
    except Exception as e:
        return {"error": str(e), "raw": ""}


def run_all_agents(target_name: str = None) -> list[dict]:
    """Run all active agents (or one by name). Returns list of triage results."""
    db.init()
    agents = db.get_agents("active")

    if target_name:
        agents = [a for a in agents if a["name"] == target_name]
        if not agents:
            print(f"  No active agent named '{target_name}'")
            return []

    if not agents:
        print("  No active agents registered.")
        return []

    print(f"\n  Atlas Monitor: Running {len(agents)} agent(s)...\n")
    results = []
    for agent in agents:
        triage = run_agent(agent)
        results.append(triage)

    return results


def show_status():
    """Print last-run status for all agents."""
    db.init()
    agents = db.get_agents("active")
    print(f"\n  Agent Monitor Status ({len(agents)} active)\n  {'─'*60}")
    for a in agents:
        last = (a.get("last_run") or "never")[:16]
        runs = a.get("run_count", 0)
        exc = a.get("exception_count", 0)
        last_out = (a.get("last_output") or "")[:60]
        icon = "🔴" if exc > 2 else "🟡" if exc > 0 else "🟢"
        print(f"  {icon} {a['name']:<18} last:{last} runs:{runs} exc:{exc}")
        if last_out:
            print(f"     {last_out}...")


def show_escalations():
    """Print all pending escalations."""
    db.init()
    pending = db.get_pending_escalations()
    if not pending:
        print("\n  No pending escalations. All clear.")
        return

    print(f"\n  Pending Escalations ({len(pending)})\n  {'─'*60}")
    for e in pending:
        icon = "🔴" if e.get("urgency") == "CRITICAL" else "🟡"
        print(f"\n  {icon} [{e.get('agent_name','?')}] {e.get('escalation_reason','?')}")
        print(f"     Ran: {(e.get('ran_at') or '')[:16]}")
        print(f"     Output preview: {(e.get('output') or '')[:100]}...")


def build_monitor_report(results: list[dict]) -> dict:
    """Aggregate triage results into a single monitor report."""
    escalations = [r for r in results if r.get("needs_attention")]
    critical = [r for r in escalations if r.get("urgency") == "CRITICAL"]
    high = [r for r in escalations if r.get("urgency") == "HIGH"]
    normal_runs = [r for r in results if not r.get("needs_attention")]

    return {
        "ran_at": datetime.now(timezone.utc).isoformat(),
        "agents_run": len(results),
        "escalations": len(escalations),
        "critical_count": len(critical),
        "high_count": len(high),
        "clean_count": len(normal_runs),
        "items": [
            {
                "agent": r.get("agent_name", "?"),
                "urgency": r.get("urgency", "NORMAL"),
                "reason": r.get("escalation_reason"),
                "action": r.get("recommended_action"),
                "summary": r.get("summary", "")
            }
            for r in escalations
        ],
        "all_summaries": [
            {"agent": r.get("agent_name", "?"), "summary": r.get("summary", "")}
            for r in results
        ]
    }


if __name__ == "__main__":
    db.init()
    args = sys.argv[1:]
    cmd = args[0] if args else "status"

    if cmd == "run":
        target = args[1] if len(args) > 1 else None
        results = run_all_agents(target)
        report = build_monitor_report(results)

        print(f"\n  Monitor complete: {report['agents_run']} agents, {report['escalations']} escalation(s)")
        if report["escalations"]:
            print(f"\n  Escalations requiring attention:")
            for item in report["items"]:
                icon = "🔴" if item["urgency"] == "CRITICAL" else "🟡"
                print(f"  {icon} [{item['agent']}] {item['reason']}")
                if item["action"]:
                    print(f"     → {item['action']}")
        else:
            print("  All agents clean. No escalations.")

    elif cmd == "status":
        show_status()

    elif cmd == "escalations":
        show_escalations()

    else:
        print("Usage: agent_monitor.py [run [name] | status | escalations]")
