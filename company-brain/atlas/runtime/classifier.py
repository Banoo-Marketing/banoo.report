"""
Atlas event classifier — Claude determines what an event means and who handles it.
"""
import json
import re
import anthropic
from .event_model import AtlasEvent

CLASSIFIER_SYSTEM = """You are Atlas Event Classifier — the triage layer of an executive AI operating system.

Classify every incoming event to determine urgency, category, and routing.

Agent mapping (use exact names):
  relay   — email/communication requiring a human response
  ledger  — financial: invoice, payment, commission, domain renewal, bank
  broker  — real estate: property, tenant, OREA/TRREB compliance
  pulse   — client relationship: satisfaction, churn signal, deliverable
  scout   — hiring: candidates, job applications, pipeline
  atlas   — strategic judgment required — escalate directly to Emod

Do NOT escalate to Emod for:
  - Routine status updates
  - Informational emails with no action required
  - Automated notifications

DO escalate to Emod for:
  - Revenue risk or opportunity (>$500, time-sensitive)
  - Legal issue or compliance deadline
  - Client churn signal (active paying client)
  - Decision with <48h window
  - Anything classified CRITICAL

Return JSON only:
{
  "category": "finance | sales | client | calendar | admin | personal | risk | system",
  "urgency": 1-10,
  "requires_agent": true/false,
  "suggested_agent": "relay | ledger | broker | pulse | scout | atlas | null",
  "summary": "One sentence: what is this event about",
  "escalate_to_emod": true/false,
  "escalation_reason": "Why Emod needs to see this, or null"
}"""


def classify_event(event: AtlasEvent) -> dict:
    """Classify a single event. Returns classification dict."""
    client = anthropic.Anthropic()
    try:
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=350,
            system=CLASSIFIER_SYSTEM,
            messages=[{
                "role": "user",
                "content": f"Classify this event:\n{event.to_json()}"
            }]
        )
        text = resp.content[0].text.strip()
        if text.startswith("{"):
            return json.loads(text)
        m = re.search(r'\{.*\}', text, re.DOTALL)
        if m:
            return json.loads(m.group(0))
    except json.JSONDecodeError:
        pass
    except Exception as e:
        print(f"  [classifier] error: {e}")

    return {
        "category": "admin",
        "urgency": 3,
        "requires_agent": False,
        "suggested_agent": None,
        "summary": f"[classify failed] {event.type} from {event.source}",
        "escalate_to_emod": False,
        "escalation_reason": None,
    }
