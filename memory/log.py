#!/usr/bin/env python3
"""
memory/log.py — Append a memory entry. Append-only. No deletes.

Schema: { timestamp, type, entity, content, source }

Usage:
  python memory/log.py <folder> <entity> <type> "<content>" [--source manual]

  folder: interactions | clients | tasks | revenue | communications

Examples:
  python memory/log.py clients "Acme Corp" "status_update" "Signed 3-month renewal"
  python memory/log.py revenue "Banoo Inc" "payment" "Received $3000 from client X"
  python memory/log.py tasks "RBC" "reminder" "Confirm mortgage funds before June 1"
"""
import json
import sys
import argparse
from datetime import datetime, timezone
from pathlib import Path

_MEMORY = Path(__file__).parent
_VALID = {"interactions", "clients", "tasks", "revenue", "communications"}


def log_entry(folder: str, entity: str, entry_type: str, content: str,
              source: str = "manual") -> Path:
    if folder not in _VALID:
        raise ValueError(f"Invalid folder '{folder}'. Valid: {', '.join(sorted(_VALID))}")

    now = datetime.now(timezone.utc)
    slug = entity.lower().replace(" ", "_").replace("/", "_")[:30]
    filename = f"{now.strftime('%Y%m%d_%H%M%S')}_{slug}.json"

    entry = {
        "timestamp": now.isoformat(),
        "source":    source,
        "entity":    entity,
        "type":      entry_type,
        "content":   content,
    }

    path = _MEMORY / folder / filename
    path.write_text(json.dumps(entry, indent=2))
    return path


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("folder", choices=list(_VALID))
    parser.add_argument("entity")
    parser.add_argument("type")
    parser.add_argument("content")
    parser.add_argument("--source", default="manual")
    args = parser.parse_args()

    path = log_entry(args.folder, args.entity, args.type, args.content, source=args.source)
    print(f"Logged: {path.relative_to(_MEMORY.parent)}")
