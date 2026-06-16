"""
context_engine/engine.py — Convert company profile + memory into current state.

ONLY classification. No forecasting. No scoring. No AI.

Output:
{
  "company": "",
  "focus": "",
  "clients": [],
  "risks": [],
  "state": {
    "revenue": "strong | stable | weak",
    "operations": "stable | overloaded | underutilized",
    "relationships": "healthy | at_risk | fragile"
  },
  "tone": "",
  "top_priorities": []
}

Usage:
  python context_engine/engine.py          # Print snapshot
  python context_engine/engine.py --json   # Raw JSON
"""
import json
import sys
from pathlib import Path

_HERE    = Path(__file__).parent
_ROOT    = _HERE.parent
_PROFILE = _ROOT / "company_profile"
_ENTRIES = _ROOT / "memory" / "entries"
_SNAPSHOT = _HERE / "snapshot.json"


# ── Load ───────────────────────────────────────────────────────────────────────

def load_profile() -> dict:
    profile = {}
    for f in sorted(_PROFILE.glob("*.json")):
        try:
            profile[f.stem] = json.loads(f.read_text())
        except Exception:
            pass
    return profile


def get_recent_memory(limit: int = 20) -> list[dict]:
    entries = []
    if _ENTRIES.exists():
        for f in _ENTRIES.glob("*.json"):
            try:
                entries.append(json.loads(f.read_text()))
            except Exception:
                pass
    entries.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return entries[:limit]


# ── Classification ─────────────────────────────────────────────────────────────

_WEAK_REVENUE   = {"gap", "low", "weak", "lost", "cancel", "overdue", "no payment", "behind", "declined"}
_STRONG_REVENUE = {"signed", "renewal", "paid", "new client", "upsell", "contract", "strong", "closed"}
_OVERLOAD       = {"legal", "blocked", "urgent", "crisis", "failed", "dispute", "overload", "escalated"}
_AT_RISK        = {"silent", "no response", "cancelled", "at risk", "churn", "ghosted", "unresponsive"}


def _classify_revenue(profile: dict, memory: list) -> str:
    identity = profile.get("identity", {})
    current  = identity.get("current_revenue_monthly", 0)
    target   = identity.get("revenue_target_monthly", 1)
    ratio    = current / max(target, 1)

    weak   = sum(1 for e in memory if any(w in e.get("content", "").lower() for w in _WEAK_REVENUE))
    strong = sum(1 for e in memory if any(w in e.get("content", "").lower() for w in _STRONG_REVENUE))

    if ratio < 0.30 or weak > strong:
        return "weak"
    if ratio >= 0.75 or strong > weak:
        return "strong"
    return "stable"


def _classify_operations(memory: list) -> str:
    overload = sum(1 for e in memory[:10] if any(w in e.get("content", "").lower() for w in _OVERLOAD))
    if overload >= 2:
        return "overloaded"
    return "stable"


def _classify_relationships(profile: dict, memory: list) -> str:
    active      = profile.get("clients", {}).get("active", [])
    at_risk_clients = [c for c in active if c.get("health") == "at_risk"]
    at_risk_signals = sum(1 for e in memory if any(w in e.get("content", "").lower() for w in _AT_RISK))

    if at_risk_clients or at_risk_signals >= 2:
        return "at_risk"
    if at_risk_signals == 1:
        return "fragile"
    return "healthy"


# ── Snapshot ───────────────────────────────────────────────────────────────────

def generate_snapshot() -> dict:
    profile = load_profile()
    memory  = get_recent_memory(limit=50)

    identity = profile.get("identity", {})
    tone     = profile.get("tone", {})

    clients = [
        {"name": c["name"], "health": c.get("health", "ok")}
        for c in profile.get("clients", {}).get("active", [])
    ]

    snapshot = {
        "company":        identity.get("company_name", ""),
        "focus":          identity.get("current_focus", ""),
        "clients":        clients,
        "risks":          identity.get("active_risks", []),
        "state": {
            "revenue":       _classify_revenue(profile, memory),
            "operations":    _classify_operations(memory),
            "relationships": _classify_relationships(profile, memory),
        },
        "tone":           tone.get("style", "direct, simple"),
        "top_priorities": identity.get("top_priorities", [])[:3],
    }

    _SNAPSHOT.write_text(json.dumps(snapshot, indent=2))
    return snapshot


def get_snapshot() -> dict:
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
        print(f"\n  Context Snapshot — {snapshot['company'] or '(company not set)'}")
        print(f"  {'─' * 50}")
        print(f"  Focus         : {snapshot['focus'] or '(not set)'}")
        print(f"  Revenue       : {s['revenue'].upper()}")
        print(f"  Operations    : {s['operations'].upper()}")
        print(f"  Relationships : {s['relationships'].upper()}")
        print(f"  Clients       : {len(snapshot['clients'])} active")
        print(f"  Tone          : {snapshot['tone']}")
        if snapshot["top_priorities"]:
            print(f"\n  Priorities:")
            for i, p in enumerate(snapshot["top_priorities"], 1):
                print(f"    {i}. {p}")
        if snapshot["risks"]:
            print(f"\n  Risks:")
            for r in snapshot["risks"]:
                print(f"    - {r}")
