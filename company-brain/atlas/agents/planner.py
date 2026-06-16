"""
Planner Agent — Strategic brain.
Chooses focus, prioritizes initiatives, selects revenue engines, kills weak ideas.
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

PLANNER_SYSTEM = """You are Atlas Planner Agent — the strategic brain of the Atlas system.

ROLE:
- Choose focus for the next 7 days
- Prioritize initiatives by ROI and strategic alignment
- Select the 2 primary revenue engines
- Identify and kill low-ROI work
- Enforce the max-3-initiatives rule without exception

RULES:
- Max 3 active initiatives. Period.
- Revenue-first decision making
- Kill anything with ROI < 6 or no revenue path in 90 days
- No new initiatives without killing an existing one first
- Think like: CFO (cash flow) + Investor (compounding) + Operator (execution)

OUTPUT: Return JSON only. No explanation. No preamble. No markdown fences.

JSON schema:
{
  "top_priorities": [
    {"rank": 1, "name": "...", "rationale": "...", "weekly_target": "..."},
    {"rank": 2, "name": "...", "rationale": "...", "weekly_target": "..."},
    {"rank": 3, "name": "...", "rationale": "...", "weekly_target": "..."}
  ],
  "primary_engine": {"name": "...", "type": "...", "weekly_output": "..."},
  "secondary_engine": {"name": "...", "type": "...", "weekly_output": "..."},
  "kill_list": [
    {"name": "...", "reason": "...", "hours_freed": 0}
  ],
  "focus_decision": "...",
  "revenue_target_week": 0,
  "constraint": "...",
  "sovereignty_check": "INCREASES | DECREASES | NEUTRAL"
}"""


def _extract_json(text: str) -> dict:
    text = text.strip()
    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Extract from markdown fences
    match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except Exception:
            pass
    # Find first {...}
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except Exception:
            pass
    return {"error": "Failed to parse planner output", "raw": text[:500]}


def run_planner(memory: dict) -> dict:
    """Run the Planner agent with current memory state. Returns structured JSON."""
    prompt = f"""CURRENT MEMORY STATE:

Revenue streams: {json.dumps(memory.get('revenue', []), indent=2)}

Active initiatives: {json.dumps(memory.get('initiatives', []), indent=2)}

System state: {json.dumps(memory.get('state', {}), indent=2)}

Pipeline: {json.dumps(memory.get('pipeline', {}), indent=2)}

TASK:
Choose top 3 priorities. Select 2 revenue engines. Kill low-ROI work.
Revenue gap to close: ${memory.get('state', {}).get('gap', 12000):,.0f}/month.

Return JSON only."""

    client = anthropic.Anthropic()
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1500,
        system=PLANNER_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    return _extract_json(resp.content[0].text)
