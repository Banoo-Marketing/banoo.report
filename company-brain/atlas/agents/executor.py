"""
Executor Agent — Daily operator.
Generates today's 3 tasks, maps them to revenue/pipeline, identifies bottlenecks.
Returns structured JSON only.
"""
import json
import re
from pathlib import Path

_HERE = Path(__file__).parent.parent

try:
    from dotenv import load_dotenv
    load_dotenv(_HERE.parent.parent / "company-brain" / ".env")
    load_dotenv(_HERE / ".env")
except ImportError:
    pass

import anthropic

EXECUTOR_SYSTEM = """You are Atlas Executor Agent — the daily operator of the Atlas system.

ROLE:
- Generate today's max 3 execution tasks
- Map every task to revenue, pipeline movement, or system building
- Identify the single active bottleneck
- Reject non-revenue tasks unless they build automation
- Enforce the 3-task limit without exception

RULES:
- Max 3 tasks. If there are more than 3 priorities, you must reduce scope.
- Every task must pass: generates revenue OR moves pipeline OR builds a system
- Tasks must be completable today
- Think like: Operator (execution) + Growth hacker (ROI/acquisition)

OUTPUT: Return JSON only. No explanation. No preamble. No markdown fences.

JSON schema:
{
  "date": "YYYY-MM-DD",
  "revenue_objective_today": "...",
  "daily_tasks": [
    {
      "rank": 1,
      "task": "...",
      "impact": "direct | indirect | system",
      "expected_outcome": "...",
      "revenue_link": "..."
    }
  ],
  "bottleneck": "...",
  "focus_check": {
    "initiatives_active": 0,
    "status": "GREEN | YELLOW | RED",
    "action_needed": "..."
  },
  "one_number_today": "..."
}"""


def _extract_json(text: str) -> dict:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except Exception:
            pass
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except Exception:
            pass
    return {"error": "Failed to parse executor output", "raw": text[:500]}


def run_executor(memory: dict) -> dict:
    """Run the Executor agent with current memory state. Returns structured JSON."""
    from datetime import date
    prompt = f"""TODAY IS: {date.today().isoformat()}

SYSTEM STATE:
{json.dumps(memory.get('state', {}), indent=2)}

ACTIVE INITIATIVES:
{json.dumps(memory.get('initiatives', []), indent=2)}

PIPELINE:
{json.dumps(memory.get('pipeline', {}), indent=2)}

CURRENT TASK QUEUE:
{json.dumps(memory.get('tasks_today', {}).get('tasks', []), indent=2)}

OPEN HIGH-PRIORITY ACTIONS:
Revenue gap: ${memory.get('state', {}).get('gap', 12000):,.0f}/month to close.

TASK:
Generate today's max 3 execution tasks. Map each to revenue, pipeline, or system.
Identify the single bottleneck blocking progress.

Return JSON only."""

    client = anthropic.Anthropic()
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1200,
        system=EXECUTOR_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    return _extract_json(resp.content[0].text)
