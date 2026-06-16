"""
context_engine/engine.py — Convert company brain + memory into current state.

ONLY intelligence layer. Pure classification — no forecasting, no scoring.

Output format:
{
  "company": "",
  "focus": "",
  "clients": [],
  "risks": [],
  "state": {
    "revenue": "strong|stable|weak",
    "operations": "stable|overloaded|underutilized",
    "relationships": "healthy|at_risk|fragile"
  },
  "tone": "",
  "top_priorities": []
}

Usage:
  python context_engine/engine.py          # Generate + print snapshot
  python context_engine/engine.py --json   # Raw JSON only
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

_HERE = Path(__file__).parent
_ROOT = _HERE.parent
_BRAIN = _ROOT / "company_brain"
_MEMORY = _ROOT / "memory"
_SNAPSHOT = _HERE / "context_snapshot.json"

_MEMORY_FOLDERS = ["interactions", "clients", "tasks", "revenue", "communications"]


# ── Load ───────────────────────────────────────────────────────────────────────

def load_company_brain() -> dict:
    brain = {}
    for f in sorted(_BRAIN.glob("*.json")):
        try:
            brain[f.stem] = json.loads(f.read_text())
        except Exception:
            pass
    return brain


def get_recent_memory(limit: int = 20) -> list[dict]:
    entries = []
    for folder in _MEMORY_FOLDERS:
        path = _MEMORY / folder
        if not path.exists():
            continue
        for f in path.glob("*.json"):
            try:
                entry = json.loads(f.read_text())
                entry["_folder"] = folder
                entries.append(entry)
            except Exception:
                pass
    entries.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return entries[:limit]


# ── Classification ─────────────────────────────────────────────────────────────

_WEAK_REVENUE = {"gap", "low", "weak", "lost", "cancel", "overdue", "no payment", "behind"}
_STRONG_REVENUE = {"signed", "renewal", "paid", "new client", "upsell", "contract", "strong"}
_OVERLOAD_SIGNALS = {"legal dispute", "blocked", "urgent", "do not contact", "overload", "crisis", "failed"}
_AT_RISK_SIGNALS = {"silent", "no response", "cancelled meeting", "at risk", "churn", "ghosted"}


def _classify_revenue(brain: dict, memory: list) -> str:
    identity = brain.get("identity", {})
    current = identity.get("current_revenue_monthly", 0)
    target = identity.get("revenue_target_monthly", 1)
    ratio = current / max(target, 1)

    revenue_entries = [e for e in memory
                       if e.get("type") in ("revenue_snapshot", "payment", "contract", "invoice")]
    weak = sum(1 for e in revenue_entries
               if any(w in e.get("content", "").lower() for w in _WEAK_REVENUE))
    strong = sum(1 for e in revenue_entries
                 if any(w in e.get("content", "").lower() for w in _STRONG_REVENUE))

    if ratio < 0.30 or weak > strong:
        return "weak"
    if ratio >= 0.75 or strong > weak:
        return "strong"
    return "stable"


def _classify_operations(memory: list) -> str:
    recent = memory[:10]
    overload = sum(1 for e in recent
                   if any(w in e.get("content", "").lower() for w in _OVERLOAD_SIGNALS))
    if overload >= 2:
        return "overloaded"
    return "stable"


def _classify_relationships(brain: dict, memory: list) -> str:
    active_clients = brain.get("clients", {}).get("active", [])
    at_risk_clients = [c for c in active_clients if c.get("health") == "at_risk"]

    at_risk_signals = sum(1 for e in memory
                          if any(w in e.get("content", "").lower() for w in _AT_RISK_SIGNALS))

    if at_risk_clients or at_risk_signals >= 2:
        return "at_risk"
    if at_risk_signals == 1:
        return "fragile"
    return "healthy"


# ── Snapshot ───────────────────────────────────────────────────────────────────

def generate_snapshot() -> dict:
    brain = load_company_brain()
    memory = get_recent_memory(limit=50)

    identity = brain.get("identity", {})
    tone = brain.get("tone_of_voice", {})
    active_clients = [
        {"name": c["name"], "health": c.get("health", "ok")}
        for c in brain.get("clients", {}).get("active", [])
    ]
    risks = identity.get("active_risks", [])

    snapshot = {
        "company":        identity.get("company_name", "Banoo Inc"),
        "focus":          identity.get("current_focus", ""),
        "clients":        active_clients,
        "risks":          risks,
        "state": {
            "revenue":       _classify_revenue(brain, memory),
            "operations":    _classify_operations(memory),
            "relationships": _classify_relationships(brain, memory),
        },
        "tone":           tone.get("style", "direct, casual"),
        "top_priorities": identity.get("top_priorities", [])[:3],
    }

    _SNAPSHOT.write_text(json.dumps(snapshot, indent=2))
    return snapshot


def get_context_snapshot() -> dict:
    if _SNAPSHOT.exists():
        return json.loads(_SNAPSHOT.read_text())
    return generate_snapshot()


# ── CLI ────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    raw = "--json" in sys.argv
    snapshot = generate_snapshot()

    if raw:
        print(json.dumps(snapshot, indent=2))
    else:
        s = snapshot["state"]
        print(f"\n  Context Snapshot — {snapshot['company']}")
        print(f"  {'─' * 50}")
        print(f"  Focus       : {snapshot['focus']}")
        print(f"  Revenue     : {s['revenue'].upper()}")
        print(f"  Operations  : {s['operations'].upper()}")
        print(f"  Relationships: {s['relationships'].upper()}")
        print(f"  Clients     : {len(snapshot['clients'])} active")
        print(f"  Tone        : {snapshot['tone']}")
        print(f"\n  Priorities:")
        for i, p in enumerate(snapshot["top_priorities"], 1):
            print(f"    {i}. {p}")
        if snapshot["risks"]:
            print(f"\n  Risks:")
            for r in snapshot["risks"]:
                print(f"    - {r}")
