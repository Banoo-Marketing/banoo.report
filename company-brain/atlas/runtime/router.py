"""
Atlas event router — maps classified events to the right agent or escalation.
"""

# Maps agent name → (module, function)
AGENT_MAP = {
    "relay":  ("relay",  "run_inbox_scan"),
    "ledger": ("ledger", "run_financial_scan"),
    "broker": ("broker", "run_property_scan"),
    "pulse":  ("pulse",  "run_client_health_scan"),
    "scout":  ("scout",  "run_pipeline_scan"),
}

# Urgency threshold above which we skip agent execution and escalate directly
ESCALATE_URGENCY_THRESHOLD = 8


def route_to_agent(classification: dict) -> dict:
    """
    Decide what to do with a classified event.

    Returns one of:
      {"action": "LOG_ONLY"}
      {"action": "EXECUTE",  "agent": name, "module": mod, "fn": fn}
      {"action": "ESCALATE", "reason": str}
    """
    urgency = classification.get("urgency", 5)
    escalate = classification.get("escalate_to_emod", False)
    requires_agent = classification.get("requires_agent", False)
    suggested = classification.get("suggested_agent")
    reason = classification.get("escalation_reason") or classification.get("summary", "")

    # Hard escalation: Claude said so, or urgency is critical
    if escalate or urgency >= ESCALATE_URGENCY_THRESHOLD:
        return {"action": "ESCALATE", "reason": reason}

    # No agent needed
    if not requires_agent or not suggested or suggested == "null":
        return {"action": "LOG_ONLY"}

    # Atlas = strategic judgment = escalate, don't run an agent
    if suggested == "atlas":
        return {"action": "ESCALATE", "reason": f"Strategic judgment required: {reason}"}

    # Known agent
    if suggested in AGENT_MAP:
        module, fn = AGENT_MAP[suggested]
        return {"action": "EXECUTE", "agent": suggested, "module": module, "fn": fn}

    # Unknown agent name — log and escalate
    return {"action": "ESCALATE", "reason": f"Unknown agent '{suggested}': {reason}"}
