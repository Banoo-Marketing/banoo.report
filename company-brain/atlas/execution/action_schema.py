"""
Atlas Action Schema — typed representation of every executable action.

Every agent output that should cause a real-world effect must be
converted to an AtlasAction before entering the execution layer.
"""
import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone


class ActionType:
    EMAIL_DRAFT    = "email_draft"    # Create a Gmail draft (no send)
    EMAIL_SEND     = "email_send"     # Send email — always APPROVE minimum
    CALENDAR_CREATE = "calendar_create"  # Create a calendar event
    TASK_CREATE    = "task_create"    # Create an action in chief.db
    TASK_UPDATE    = "task_update"    # Update an existing action
    CRM_UPDATE     = "crm_update"     # Update a contact record
    NOTIFY         = "notify"         # Internal notification only (no external effect)


class PermissionLevel:
    AUTO    = 0   # Execute immediately, no approval needed
    LOG     = 1   # Execute immediately, log prominently for review
    APPROVE = 2   # Queue for Emod's explicit approval before execution
    MANUAL  = 3   # Never auto-execute — human must act directly


# Human-readable labels
LEVEL_LABELS = {
    PermissionLevel.AUTO:    "AUTO",
    PermissionLevel.LOG:     "LOG",
    PermissionLevel.APPROVE: "APPROVE",
    PermissionLevel.MANUAL:  "MANUAL",
}

LEVEL_ICONS = {
    PermissionLevel.AUTO:    "🟢",
    PermissionLevel.LOG:     "🔵",
    PermissionLevel.APPROVE: "🟡",
    PermissionLevel.MANUAL:  "🔴",
}


@dataclass
class AtlasAction:
    action_type: str
    payload: dict
    source_agent: str = ""
    rationale: str = ""
    permission_level: int = PermissionLevel.APPROVE
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    status: str = "pending"          # pending|approved|executed|rejected|failed
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    approved_at: str = None
    executed_at: str = None
    result: str = None
    rejected_reason: str = None

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), default=str)

    @classmethod
    def from_dict(cls, d: dict) -> "AtlasAction":
        return cls(
            action_type=d["action_type"],
            payload=d.get("payload", {}),
            source_agent=d.get("source_agent", ""),
            rationale=d.get("rationale", ""),
            permission_level=d.get("permission_level", PermissionLevel.APPROVE),
            id=d.get("id", str(uuid.uuid4())[:8]),
            status=d.get("status", "pending"),
            created_at=d.get("created_at", datetime.now(timezone.utc).isoformat()),
            approved_at=d.get("approved_at"),
            executed_at=d.get("executed_at"),
            result=d.get("result"),
            rejected_reason=d.get("rejected_reason"),
        )

    def level_label(self) -> str:
        return LEVEL_LABELS.get(self.permission_level, str(self.permission_level))

    def level_icon(self) -> str:
        return LEVEL_ICONS.get(self.permission_level, "?")

    def describe(self) -> str:
        """One-line human description for CLI display."""
        p = self.payload
        if self.action_type == ActionType.EMAIL_DRAFT:
            return f"Draft email to {p.get('to','?')} — {p.get('subject','?')[:50]}"
        if self.action_type == ActionType.EMAIL_SEND:
            return f"Send email to {p.get('to','?')} — {p.get('subject','?')[:50]}"
        if self.action_type == ActionType.CALENDAR_CREATE:
            return f"Create calendar event: {p.get('title','?')} on {p.get('start','?')}"
        if self.action_type == ActionType.TASK_CREATE:
            return f"Create task: {p.get('title','?')}"
        if self.action_type == ActionType.TASK_UPDATE:
            return f"Update task #{p.get('id','?')}: {p.get('field','?')} → {p.get('value','?')}"
        if self.action_type == ActionType.CRM_UPDATE:
            return f"Update contact {p.get('email','?')}: {p.get('field','?')}"
        if self.action_type == ActionType.NOTIFY:
            return f"Notify: {p.get('message','?')[:60]}"
        return f"{self.action_type}: {str(p)[:60]}"
