"""
context_engine/engine.py — Convert company brain + memory into current state.

This is the ONLY intelligence layer. Logic is simple state classification.
No forecasting. No scoring. No models.

Usage:
  python context_engine/engine.py          # Generate + print snapshot
  python context_engine/engine.py --json   # Print raw JSON only
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


# ── Load functions ─────────────────────────────────────────────────────────────

def load_company_brain() -> dict:
    """Load all static brain JSON files into a single dict keyed by filename stem."""
    brain = {}
    for f in sorted(_BRAIN.glob("*.json")):
        try:
            brain[f.stem] = json.loads(f.read_text())
        except Exception:
            pass
    return brain


def get_recent_memory(limit: int = 20) -> list[dict]:
    """Return most recent memory entries across all folders, sorted newest-first."""
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


# ── State classification ───────────────────────────────────────────────────────

def _classify_revenue(brain: dict, memory: list) -> str:
    revenue_entries = [e for e in memory if e.get("type") in
                       ("payment", "invoice", "contract", "renewal", "churn",
                        "revenue_snapshot", "financial_obligation")]

    if not revenue_entries:
        identity = brain.get("identity", {})
        current = identity.get("current_revenue_monthly", 0)
        target = identity.get("revenue_target_monthly", 1)
        ratio = current / max(target, 1)
        if ratio >= 0.75:
            return "strong"
        if ratio <= 0.30:
            return "weak"
        return "stable"

    weak_tags = {"at_risk", "overdue", "lost", "cancelled", "weak", "gap", "churn"}
    strong_tags = {"new_client", "upsell", "renewal", "paid", "strong", "signed"}

    weak = sum(1 for e in revenue_entries if weak_tags & set(e.get("tags", [])))
    strong = sum(1 for e in revenue_entries if strong_tags & set(e.get("tags", [])))

    if strong > weak:
        return "strong"
    if weak > 0:
        return "weak"
    return "stable"


def _classify_operations(memory: list) -> str:
    recent = memory[:10]
    overload_tags = {"overload", "blocked", "delayed", "urgent", "legal", "dispute"}
    idle_tags = {"idle", "underutilized", "waiting", "slow"}

    overload = sum(1 for e in recent if overload_tags & set(e.get("tags", [])))
    idle = sum(1 for e in recent if idle_tags & set(e.get("tags", [])))

    if overload >= 3:
        return "overloaded"
    if idle >= 3:
        return "underutilized"
    return "stable"


def _count_at_risk_clients(brain: dict, memory: list) -> int:
    at_risk_from_memory = len(set(
        e["entity"] for e in memory
        if "at_risk" in e.get("tags", []) and e.get("entity")
    ))
    at_risk_from_brain = sum(
        1 for c in brain.get("clients", {}).get("active", [])
        if c.get("health") == "at_risk"
    )
    return max(at_risk_from_memory, at_risk_from_brain)


# ── Snapshot generation ────────────────────────────────────────────────────────

def generate_snapshot() -> dict:
    """Read brain + memory, classify current state, write and return snapshot."""
    brain = load_company_brain()
    memory = get_recent_memory(limit=50)

    identity = brain.get("identity", {})
    tone = brain.get("tone_of_voice", {})
    active_clients = brain.get("clients", {}).get("active", [])

    snapshot = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "company": identity.get("company_name", "Banoo Inc"),
        "focus": identity.get("current_focus", "client retention + cashflow stability"),
        "active_clients": len(active_clients),
        "at_risk_clients": _count_at_risk_clients(brain, memory),
        "revenue_state": _classify_revenue(brain, memory),
        "operational_state": _classify_operations(memory),
        "communication_tone": tone.get("style", "direct, casual"),
        "top_priorities": identity.get("top_priorities", [])[:3],
    }

    _SNAPSHOT.write_text(json.dumps(snapshot, indent=2))
    return snapshot


def get_context_snapshot() -> dict:
    """Return snapshot from disk, or generate fresh if missing."""
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
        print(f"\n  Company Brain — Context Snapshot")
        print(f"  {'─' * 50}")
        print(f"  Company          : {snapshot['company']}")
        print(f"  Focus            : {snapshot['focus']}")
        print(f"  Active clients   : {snapshot['active_clients']}")
        print(f"  At-risk clients  : {snapshot['at_risk_clients']}")
        print(f"  Revenue state    : {snapshot['revenue_state'].upper()}")
        print(f"  Operations       : {snapshot['operational_state'].upper()}")
        print(f"  Tone             : {snapshot['communication_tone']}")
        print(f"\n  Top Priorities:")
        for i, p in enumerate(snapshot["top_priorities"], 1):
            print(f"    {i}. {p}")
        print(f"\n  Generated: {snapshot['generated_at'][:19]} UTC")
