"""
Atlas Permission Engine — computes the correct permission level for every action.

Rules are applied in order, highest-safety-wins. A rule can only RAISE the
permission level, never lower it. Once MANUAL (3) is triggered, it is final.
"""
import json
from .action_schema import ActionType, PermissionLevel, AtlasAction

# ── Hard-blocked content patterns ────────────────────────────────────────────
# Any action whose payload contains these strings → MANUAL (3), no exceptions.

_LEGAL_PATTERNS = [
    "tenant", "yousefian", "lawyer", "legal", "court", "eviction",
    "tribunal", "LTB", "lease termination", "notice to vacate",
    "218 wilfred", "wilfred ave",
]

_FINANCIAL_PATTERNS = [
    "payment", "wire transfer", "etransfer", "e-transfer", "mortgage",
    "deposit", "withdrawal", "bank account", "routing number",
    "credit card", "stripe charge", "invoice payment", "pay now",
]

# ── Type-based default permission levels ─────────────────────────────────────
_TYPE_DEFAULTS: dict[str, int] = {
    ActionType.NOTIFY:          PermissionLevel.AUTO,
    ActionType.TASK_CREATE:     PermissionLevel.AUTO,
    ActionType.TASK_UPDATE:     PermissionLevel.AUTO,
    ActionType.EMAIL_DRAFT:     PermissionLevel.AUTO,     # draft only, no send
    ActionType.CRM_UPDATE:      PermissionLevel.LOG,
    ActionType.CALENDAR_CREATE: PermissionLevel.LOG,
    ActionType.EMAIL_SEND:      PermissionLevel.APPROVE,  # minimum — always
}


def _payload_text(action: AtlasAction) -> str:
    """Flatten the payload + rationale into a single searchable string."""
    parts = [action.rationale or "", action.source_agent or ""]
    try:
        parts.append(json.dumps(action.payload, default=str))
    except Exception:
        parts.append(str(action.payload))
    return " ".join(parts).lower()


def compute_permission_level(action: AtlasAction) -> int:
    """
    Return the correct PermissionLevel for this action.

    Rules applied in ascending order of severity; level can only increase.
    """
    text = _payload_text(action)

    # Start from the type-based default
    level = _TYPE_DEFAULTS.get(action.action_type, PermissionLevel.APPROVE)

    # Rule 1: email_send is always at least APPROVE — hard floor
    if action.action_type == ActionType.EMAIL_SEND:
        level = max(level, PermissionLevel.APPROVE)

    # Rule 2: legal/tenant patterns → MANUAL, full stop
    if any(p in text for p in _LEGAL_PATTERNS):
        return PermissionLevel.MANUAL

    # Rule 3: financial patterns → MANUAL
    if any(p in text for p in _FINANCIAL_PATTERNS):
        return PermissionLevel.MANUAL

    return level


def apply_permission(action: AtlasAction) -> AtlasAction:
    """Compute and set permission_level on an action in place. Returns action."""
    action.permission_level = compute_permission_level(action)
    return action


def explain_permission(action: AtlasAction) -> str:
    """Return a human-readable explanation of why the level was assigned."""
    text = _payload_text(action)
    reasons = []

    if any(p in text for p in _LEGAL_PATTERNS):
        matched = [p for p in _LEGAL_PATTERNS if p in text]
        reasons.append(f"Legal/tenant keyword: {matched[0]!r}")

    if any(p in text for p in _FINANCIAL_PATTERNS):
        matched = [p for p in _FINANCIAL_PATTERNS if p in text]
        reasons.append(f"Financial keyword: {matched[0]!r}")

    if action.action_type == ActionType.EMAIL_SEND:
        reasons.append("email_send always requires approval")

    if not reasons:
        reasons.append(f"type default for {action.action_type!r}")

    return "; ".join(reasons)
