"""
memory/log.py — Append a memory entry. Append-only. No edits. No deletes.

Schema: { timestamp, type, entity, content, source }
Types:  email | crm | manual | system

Usage:
  python memory/log.py <entity> <type> "<content>" [--source manual]

Examples:
  python memory/log.py "Acme Corp" manual "Signed 3-month renewal"
  python memory/log.py "Acme Corp" crm "CRM note: payment overdue 30 days"
  python memory/log.py "Team" system "Onboarded new team member"
"""
import json
import argparse
from datetime import datetime, timezone
from pathlib import Path

_ENTRIES = Path(__file__).parent / "entries"
_ENTRIES.mkdir(exist_ok=True)

_VALID_TYPES = {"email", "crm", "manual", "system"}


def log_entry(entity: str, entry_type: str, content: str, source: str = "manual") -> Path:
    now = datetime.now(timezone.utc)
    slug = entity.lower().replace(" ", "_").replace("/", "_")[:30]
    filename = f"{now.strftime('%Y%m%d_%H%M%S_%f')}_{slug}.json"

    entry = {
        "timestamp": now.isoformat(),
        "type":      entry_type,
        "entity":    entity,
        "content":   content,
        "source":    source,
    }

    path = _ENTRIES / filename
    path.write_text(json.dumps(entry, indent=2))
    return path


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("entity")
    parser.add_argument("type")
    parser.add_argument("content")
    parser.add_argument("--source", default="manual")
    args = parser.parse_args()

    path = log_entry(args.entity, args.type, args.content, source=args.source)
    print(f"Logged: {path.relative_to(Path(__file__).parent.parent)}")
