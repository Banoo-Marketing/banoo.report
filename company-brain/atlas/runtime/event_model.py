"""
Atlas event model — every real-world signal is typed as an AtlasEvent.
"""
import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone


class EventType:
    EMAIL_RECEIVED   = "EMAIL_RECEIVED"
    CALENDAR_UPDATE  = "CALENDAR_UPDATE"
    INVOICE_RECEIVED = "INVOICE_RECEIVED"
    LEAD_CREATED     = "LEAD_CREATED"
    DEAL_UPDATED     = "DEAL_UPDATED"
    TASK_OVERDUE     = "TASK_OVERDUE"
    AGENT_EXCEPTION  = "AGENT_EXCEPTION"
    END_OF_DAY       = "END_OF_DAY"
    END_OF_WEEK      = "END_OF_WEEK"
    MANUAL           = "MANUAL"


class EventSource:
    GMAIL    = "gmail"
    CALENDAR = "calendar"
    CRM      = "crm"
    MANUAL   = "manual"
    SYSTEM   = "system"


class EventPriority:
    LOW      = "low"
    MEDIUM   = "medium"
    HIGH     = "high"
    CRITICAL = "critical"


@dataclass
class AtlasEvent:
    type: str
    source: str
    payload: dict
    priority: str = EventPriority.MEDIUM
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), default=str)

    @classmethod
    def from_dict(cls, d: dict) -> "AtlasEvent":
        return cls(
            type=d["type"],
            source=d.get("source", EventSource.MANUAL),
            payload=d.get("payload", {}),
            priority=d.get("priority", EventPriority.MEDIUM),
            id=d.get("id", str(uuid.uuid4())[:8]),
            timestamp=d.get("timestamp", datetime.now(timezone.utc).isoformat()),
        )
