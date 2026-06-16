"""
Agent Decision Loop
────────────────────
Central reasoning engine. Analyses a deal + context and decides
what action (if any) to recommend. ALL actions go through the
action_queue for human approval – nothing executes automatically.
"""
from enum import Enum
from typing import Any
import json
import anthropic
import database as db
from config import settings


class ActionType(str, Enum):
    REMIND = "remind"
    DRAFT_EMAIL = "draft_email"
    ASSIGN_TASK = "assign_task"
    ESCALATE = "escalate"
    NO_ACTION = "no_action"


def build_deal_context(deal_id: str) -> dict[str, Any]:
    """Fetch deal + related contact + recent audit history."""
    deal = db.fetchone(
        """
        SELECT d.*, c.name AS contact_name, c.email AS contact_email,
               c.clv_tier, c.industry
        FROM deals d
        LEFT JOIN contacts c ON c.id = d.contact_id
        WHERE d.id = %s
        """,
        (deal_id,),
    )
    if not deal:
        raise ValueError(f"Deal {deal_id} not found")

    last_action = db.fetchone(
        """
        SELECT action_type, created_at FROM audit_log
        WHERE deal_id = %s
        ORDER BY created_at DESC LIMIT 1
        """,
        (deal_id,),
    )

    deal["last_action"] = last_action["action_type"] if last_action else "None"
    deal["last_action_at"] = str(last_action["created_at"]) if last_action else "Never"
    return deal


def decide_action(deal_id: str) -> dict[str, Any]:
    """
    Core LLM decision: what should happen next for this deal?
    Returns the decision dict AND queues it if not NO_ACTION.
    """
    context = build_deal_context(deal_id)
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    prompt = f"""
You are an AI sales operations assistant. Analyse this CRM situation and decide what action to take.

Deal: {context["name"]}
Stage: {context["stage"]}
Value: ${float(context.get("amount", 0)):,.2f}
Company: {context["company"]}
Industry: {context.get("industry", "Unknown")}
Client tier: {context.get("clv_tier", "Unknown")}
Days since last activity: {context.get("days_since_activity", "?")}
Renewal date: {context.get("renewal_date", "N/A")}
Last action taken: {context["last_action"]} (at {context["last_action_at"]})

Available actions:
- DRAFT_EMAIL  → draft and queue a personalised email for rep approval
- REMIND       → send the rep a reminder to follow up
- ASSIGN_TASK  → create a CRM task for the rep
- ESCALATE     → flag to manager (use for PLATINUM clients stalled >5 days)
- NO_ACTION    → nothing needed right now

Decision rules:
- If renewal is within 30 days and no recent action → DRAFT_EMAIL
- If PLATINUM client with >7 days no activity → ESCALATE
- If deal has been in same stage >14 days → REMIND or ASSIGN_TASK
- If everything looks healthy → NO_ACTION

Respond ONLY with valid JSON (no markdown):
{{
  "action": "DRAFT_EMAIL",
  "reason": "Short explanation of why",
  "urgency": "HIGH | MEDIUM | LOW",
  "suggested_message": "Brief description of what the email/task should say"
}}
""".strip()

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=350,
        messages=[{"role": "user", "content": prompt}],
    )

    decision = json.loads(response.content[0].text)
    decision["deal_id"] = deal_id

    # Queue for human approval (never auto-execute)
    if decision["action"] != ActionType.NO_ACTION:
        _queue_decision(context, decision)

    return decision


def _queue_decision(deal: dict, decision: dict) -> None:
    db.execute(
        """
        INSERT INTO action_queue
            (action_type, deal_id, contact_id, payload, urgency, reason)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (
            decision["action"].lower(),
            deal["id"],
            deal.get("contact_id"),
            json.dumps(decision),
            decision.get("urgency", "MEDIUM"),
            decision.get("reason", ""),
        ),
    )
    db.execute(
        "INSERT INTO audit_log (action_type, deal_id, actor, details) VALUES (%s, %s, 'system', %s)",
        (decision["action"].lower() + "_queued", deal["id"], json.dumps(decision)),
    )


def run_full_scan() -> list[dict]:
    """
    Run decide_action on every active (non-closed) deal.
    Returns list of decisions that produced a non-NO_ACTION result.
    """
    active_deals = db.fetchall(
        "SELECT id FROM deals WHERE stage NOT IN ('closed_won', 'closed_lost')"
    )
    actions = []
    for row in active_deals:
        try:
            decision = decide_action(row["id"])
            if decision["action"] != ActionType.NO_ACTION:
                actions.append(decision)
        except Exception as e:
            print(f"  ⚠️  Error processing deal {row['id']}: {e}")
    return actions
