"""
FROZEN — Not required for core product. Do not extend or activate.

notification_compressor.py — Interruption cost model + alert deduplication.

Filters escalation queue before it reaches the CEO.
NEVER suppresses CRITICAL urgency items.

Usage:
  python notification_compressor.py status   # Print fatigue score + queue stats
"""
from __future__ import annotations
import sys
from pathlib import Path

_HERE = Path(__file__).parent         # atlas/attention/compression/
_ATLAS = _HERE.parent.parent          # atlas/
_CHIEF = _ATLAS.parent / "chief"

sys.path.insert(0, str(_CHIEF))
sys.path.insert(0, str(_ATLAS))

try:
    from dotenv import load_dotenv
    load_dotenv(_ATLAS.parent / ".env")
except ImportError:
    pass

import db

_URGENCY_SCORES = {"CRITICAL": 10.0, "HIGH": 7.0, "NORMAL": 4.0}

_DOMAIN_KEYWORDS: dict[str, list[str]] = {
    "revenue":       ["revenue", "payment", "invoice", "retainer", "cash", "money", "billing"],
    "legal":         ["legal", "tenant", "wilfred", "lawyer", "court", "dispute"],
    "relationship":  ["relationship", "contact", "decay", "outreach", "client"],
    "health":        ["overload", "stress", "attention", "focus", "bandwidth"],
    "operations":    ["agent", "error", "exception", "failed", "scheduler", "monitor"],
    "family":        ["family", "diyar", "dario", "sahar", "parenting", "children"],
}

_HIGH_EMOTIONAL_KEYWORDS = {"legal", "wilfred", "lawyer", "court", "dispute", "overload"}


# ── Core functions ─────────────────────────────────────────────────────────────

def score_alert(alert: dict) -> dict:
    """
    Add interruption cost scores to alert dict.
    Returns enriched copy.
    """
    urgency = (alert.get("urgency") or "NORMAL").upper()
    reason  = (alert.get("reason") or alert.get("escalation_reason") or "").lower()
    summary = (alert.get("summary") or "").lower()
    text    = reason + " " + summary

    urgency_score = _URGENCY_SCORES.get(urgency, 4.0)

    leverage_score = min(10.0, urgency_score * 0.8)

    try:
        from attention_engine import is_overloaded
        overloaded = is_overloaded(days=1)
    except Exception:
        overloaded = False
    fragmentation_cost = 7.0 if overloaded else 3.0

    emotional_kw_hits = sum(1 for kw in _HIGH_EMOTIONAL_KEYWORDS if kw in text)
    emotional_load_score = min(5.0, emotional_kw_hits * 1.5)

    executive_relevance = urgency_score * 0.9

    net_score = (
        urgency_score      * 0.30
        + leverage_score   * 0.25
        + executive_relevance * 0.25
        - fragmentation_cost  * 0.15
        - emotional_load_score * 0.10
    )

    result = dict(alert)
    result.update({
        "_urgency_score":       urgency_score,
        "_leverage_score":      leverage_score,
        "_fragmentation_cost":  fragmentation_cost,
        "_emotional_load":      emotional_load_score,
        "_executive_relevance": executive_relevance,
        "_net_score":           round(net_score, 3),
    })
    return result


def filter_alerts(alerts: list[dict], max_alerts: int = 5) -> list[dict]:
    """
    Score, deduplicate, and rank alerts.
    In suppress mode: passes only CRITICAL items (never suppressed).
    """
    if not alerts:
        return []

    scored = [score_alert(a) for a in alerts]

    try:
        from attention_engine import should_suppress_alerts
        suppress_mode = should_suppress_alerts()
    except Exception:
        suppress_mode = False

    if suppress_mode:
        # CRITICAL items always pass through
        return [a for a in scored if (a.get("urgency") or "").upper() == "CRITICAL"]

    # Deduplicate: keep highest net_score per (agent, urgency) pair
    seen: dict[tuple, dict] = {}
    for a in scored:
        agent = a.get("agent_name") or a.get("agent") or ""
        urgency = (a.get("urgency") or "NORMAL").upper()
        key = (agent, urgency)
        if key not in seen or a["_net_score"] > seen[key]["_net_score"]:
            seen[key] = a

    deduped = list(seen.values())
    deduped.sort(key=lambda x: x["_net_score"], reverse=True)
    return deduped[:max_alerts]


def cluster_alerts(alerts: list[dict]) -> list[dict]:
    """
    Group related alerts by domain keyword matching.
    Merged clusters become one alert with the highest urgency.
    """
    if not alerts:
        return []

    def _detect_domain(alert: dict) -> str:
        text = (
            (alert.get("reason") or "") + " " +
            (alert.get("escalation_reason") or "") + " " +
            (alert.get("summary") or "")
        ).lower()
        for domain, keywords in _DOMAIN_KEYWORDS.items():
            if any(kw in text for kw in keywords):
                return domain
        return "other"

    domain_groups: dict[str, list[dict]] = {}
    for a in alerts:
        domain = _detect_domain(a)
        domain_groups.setdefault(domain, []).append(a)

    result = []
    urgency_rank = {"CRITICAL": 3, "HIGH": 2, "NORMAL": 1}

    for domain, group in domain_groups.items():
        if len(group) == 1:
            result.append(group[0])
            continue

        # Merge: pick highest urgency, combine reasons
        group.sort(key=lambda x: urgency_rank.get((x.get("urgency") or "NORMAL").upper(), 1), reverse=True)
        primary = dict(group[0])
        combined_reasons = "; ".join(
            filter(None, [a.get("reason") or a.get("escalation_reason") or "" for a in group])
        )
        primary["reason"] = combined_reasons[:300]
        primary["_cluster_size"] = len(group)
        primary["_cluster_domain"] = domain
        result.append(primary)

    return result


def alert_fatigue_score() -> float:
    """
    0-10 estimate of CEO alert fatigue.
    Formula: (alerts_today/10)*5 + (overload_days_recent/3)*5
    """
    try:
        db.init()
        log_today = db.get_attention_log(days=1)
        alerts_today = sum(e.get("agent_alerts", 0) for e in log_today) if log_today else 0

        log_3d = db.get_attention_log(days=3)
        overload_days = sum(1 for e in log_3d if e.get("overload_flag")) if log_3d else 0

        score = (alerts_today / 10.0) * 5.0 + (overload_days / 3.0) * 5.0
        return round(min(10.0, max(0.0, score)), 2)
    except Exception:
        return 0.0


# ── CLI ────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    db.init()
    fatigue = alert_fatigue_score()
    pending = db.get_pending_escalations(limit=50)
    filtered = filter_alerts([
        {
            "agent_name":  e.get("agent_name", "?"),
            "urgency":     e.get("urgency", "NORMAL"),
            "reason":      e.get("escalation_reason", ""),
            "summary":     (e.get("output") or "")[:200],
        }
        for e in pending
    ])

    print(f"\n  Notification Compressor\n  {'─'*50}")
    print(f"  Alert fatigue score : {fatigue:.1f}/10")
    print(f"  Pending escalations : {len(pending)}")
    print(f"  After compression   : {len(filtered)}")
    if filtered:
        print(f"\n  Filtered alerts:")
        for a in filtered:
            urgency = (a.get("urgency") or "NORMAL").upper()
            icon = "🔴" if urgency == "CRITICAL" else "🟡" if urgency == "HIGH" else "🔵"
            print(f"  {icon} [{a.get('agent_name','?')}] net={a.get('_net_score',0):.1f}  {a.get('reason','')[:70]}")
