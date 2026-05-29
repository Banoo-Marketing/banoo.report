#!/usr/bin/env python3
"""
memory/log.py — Append a new memory entry.

Usage:
  python memory/log.py <folder> <entity> <type> "<content>" [--tags tag1 tag2]

  folder: interactions | clients | tasks | revenue | communications

Examples:
  python memory/log.py clients "Acme Corp" "status_update" "Signed 3-month renewal" --tags renewal signed
  python memory/log.py revenue "Banoo Inc" "payment" "Received $3000 from client X" --tags payment received
"""
import json
import sys
import argparse
from datetime import datetime, timezone
from pathlib import Path

_MEMORY = Path(__file__).parent
_VALID_FOLDERS = {"interactions", "clients", "tasks", "revenue", "communications"}


def log_entry(folder: str, entity: str, entry_type: str, content: str,
              source: str = "manual", tags: list[str] = None) -> Path:
    if folder not in _VALID_FOLDERS:
        raise ValueError(f"Invalid folder '{folder}'. Valid: {', '.join(sorted(_VALID_FOLDERS))}")

    now = datetime.now(timezone.utc)
    timestamp = now.isoformat()
    slug = entity.lower().replace(" ", "_").replace("/", "_")[:30]
    filename = f"{now.strftime('%Y%m%d_%H%M%S')}_{slug}.json"

    entry = {
        "timestamp": timestamp,
        "source": source,
        "entity": entity,
        "type": entry_type,
        "content": content,
        "tags": tags or [],
    }

    path = _MEMORY / folder / filename
    path.write_text(json.dumps(entry, indent=2))
    return path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Log a memory entry")
    parser.add_argument("folder", choices=list(_VALID_FOLDERS))
    parser.add_argument("entity")
    parser.add_argument("type")
    parser.add_argument("content")
    parser.add_argument("--source", default="manual")
    parser.add_argument("--tags", nargs="*", default=[])
    args = parser.parse_args()

    path = log_entry(args.folder, args.entity, args.type, args.content,
                     source=args.source, tags=args.tags)
    print(f"Logged: {path.relative_to(_MEMORY.parent)}")
