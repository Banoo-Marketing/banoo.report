"""
Evaluator Agent — Weekly CFO layer.
Reviews performance, calculates revenue vs target, issues kill decisions,
resets focus for next week. Returns structured JSON only.
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

EVALUATOR_SYSTEM = """You are Atlas Evaluator Agent — the weekly CFO and performance layer of the Atlas system.

ROLE:
- Brutally honest weekly performance review
- Revenue vs target analysis (no softening)
- Issue kill decisions on underperforming initiatives
- Score the week 1–10 with clear reasoning
- Set the primary focus for next week

RULES:
- No comfort. No softening. If something is failing, say it clearly.
- Kill underperforming initiatives — at least 1 per week required
- Revenue below target = RED flag, must diagnose cause
- Think like: CFO (cash flow + risk) + Investor (compounding + leverage)

OUTPUT: Return JSON only. No explanation. No preamble. No markdown fences.

JSON schema:
{
  "week_start": "YYYY-MM-DD",
  "revenue_summary": {
    "target": 0,
    "produced": 0,
    "gap": 0,
    "trend": "IMPROVING | FLAT | DECLINING",
    "diagnosis": "..."
  },
  "focus_report": {
    "initiatives_active": 0,
    "initiatives_killed_this_cycle": 0,
    "focus_score": 0,
    "assessment": "..."
  },
  "pipeline_performance": {
    "conversion_rate": 0,
    "velocity_trend": "INCREASING | FLAT | DECREASING",
    "primary_drop_off": "...",
    "next_action": "..."
  },
  "system_progress": {
    "systems_improved": 0,
    "automation_gains": "...",
    "leverage_delta": "INCREASING | FLAT | DECREASING"
  },
  "kill_mandate": [
    {"name": "...", "reason": "...", "hours_freed": 0}
  ],
  "next_week_primary_focus": "...",
  "next_week_revenue_target": 0,
  "week_score": 0,
  "week_rating_reason": "...",
  "hard_question": "..."
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
    return {"error": "Failed to parse evaluator output", "raw": text[:500]}


def run_evaluator(memory: dict) -> dict:
    """Run the Evaluator agent with current memory state. Returns structured JSON."""
    prompt = f"""WEEKLY REVIEW DATA:

System state:
{json.dumps(memory.get('state', {}), indent=2)}

Revenue streams:
{json.dumps(memory.get('revenue', []), indent=2)}

Active initiatives:
{json.dumps(memory.get('initiatives', []), indent=2)}

Pipeline (this week + history):
{json.dumps(memory.get('pipeline', {}), indent=2)}

Recent decisions:
{json.dumps(memory.get('decisions', [])[:5], indent=2)}

Kill list (this cycle):
{json.dumps(memory.get('kill_list', [])[:5], indent=2)}

Dashboard snapshot:
{json.dumps(memory.get('snapshot', {}), indent=2)}

TASK:
Produce the weekly closeout report.
Revenue target: ${memory.get('state', {}).get('target_revenue', 15000):,.0f}/month.
Current MRR: ${memory.get('state', {}).get('current_revenue', 0):,.0f}/month.
Score the week honestly. Issue at least 1 kill mandate.
Name next week's primary focus.

Return JSON only."""

    client = anthropic.Anthropic()
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        system=EVALUATOR_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    return _extract_json(resp.content[0].text)
