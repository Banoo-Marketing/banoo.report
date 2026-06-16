"""
FROZEN — Not required for core product. Do not extend or activate.

trajectory_engine.py — Domain state tracker.

Reads existing data sources and writes trajectory_state rows.
Never fabricates data. No data → confidence_score = 0.0.

Usage:
  python trajectory_engine.py update   # Refresh all 11 domains
  python trajectory_engine.py status   # Print current domain states
  python trajectory_engine.py <domain> # Single-domain update + print
"""
from __future__ import annotations
import sys
from pathlib import Path

_HERE = Path(__file__).parent       # atlas/trajectory/
_ATLAS = _HERE.parent               # atlas/
_CHIEF = _ATLAS.parent / "chief"    # company-brain/chief/

sys.path.insert(0, str(_CHIEF))
sys.path.insert(0, str(_ATLAS))

try:
    from dotenv import load_dotenv
    load_dotenv(_ATLAS.parent / ".env")
except ImportError:
    pass

import db

_DOMAINS = [
    "revenue", "stress", "cognitive_load", "relationship_decay",
    "client_engagement", "family_bandwidth", "operational_debt",
    "focus_quality", "followthrough", "sleep_consistency", "business_momentum",
]

_RISK_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


# ── Shared helpers ─────────────────────────────────────────────────────────────

def _trajectory_score(normalized: float) -> float:
    return round(max(-1.0, min(1.0, normalized * 2 - 1)), 3)


def _risk_level(score: float, confidence: float) -> str:
    if confidence < 0.1:
        return "low"
    if score < -0.5:
        return "critical"
    if score < -0.1:
        return "high"
    if score < 0.2:
        return "medium"
    return "low"


def _compute_trend(current_norm: float, previous_score: float | None) -> str:
    if previous_score is None:
        return "unknown"
    previous_norm = (previous_score + 1) / 2
    delta = (current_norm - previous_norm) / max(previous_norm, 0.001)
    if delta > 0.05:
        return "improving"
    if delta < -0.05:
        return "declining"
    return "stable"


def _project(current_value: float, score: float, horizon: int) -> float:
    daily_delta = score * 0.02
    return round(current_value * (1 + daily_delta * horizon), 4)


# ── Domain data functions ──────────────────────────────────────────────────────

def _data_revenue() -> dict:
    try:
        streams = db.get_revenue_streams()
        total = sum(s.get("monthly_revenue", 0) for s in streams)
        target = 15_000.0
        normalized = min(1.0, total / target) if target > 0 else 0.0
        confidence = min(1.0, len(streams) / 3)
        return {"current_value": total, "normalized": normalized, "confidence": confidence}
    except Exception:
        return {"current_value": 0.0, "normalized": 0.0, "confidence": 0.0}


def _data_stress() -> dict:
    try:
        log = db.get_attention_log(days=14)
        if not log:
            return {"current_value": 0.0, "normalized": 1.0, "confidence": 0.0}
        overload_frac = sum(1 for e in log if e.get("overload_flag")) / len(log)
        fp_boost = {"critical": 0.2, "high": 0.1, "medium": 0.0, "low": -0.1}.get(
            (db.get_strategic_context() or {}).get("financial_pressure", "medium"), 0.0
        )
        raw = min(1.0, max(0.0, overload_frac + fp_boost))
        normalized = 1.0 - raw  # bad domain: invert
        confidence = min(1.0, len(log) / 7)
        return {"current_value": round(overload_frac, 3), "normalized": normalized, "confidence": confidence}
    except Exception:
        return {"current_value": 0.0, "normalized": 0.5, "confidence": 0.0}


def _data_cognitive_load() -> dict:
    try:
        log = db.get_attention_log(days=7)
        if not log:
            return {"current_value": 0.0, "normalized": 1.0, "confidence": 0.0}
        avg_events = sum(e.get("task_switches", 0) + e.get("interruptions", 0) for e in log) / len(log)
        raw = min(1.0, avg_events / 20.0)
        normalized = 1.0 - raw
        confidence = min(1.0, len(log) / 7)
        return {"current_value": round(avg_events, 2), "normalized": normalized, "confidence": confidence}
    except Exception:
        return {"current_value": 0.0, "normalized": 0.5, "confidence": 0.0}


def _data_relationship_decay() -> dict:
    try:
        rels = db.get_relationships()
        if not rels:
            return {"current_value": 0.0, "normalized": 1.0, "confidence": 0.0}
        avg_decay = sum(r.get("risk_of_decay", 0) for r in rels) / len(rels)
        normalized = 1.0 - avg_decay
        confidence = min(1.0, len(rels) / 5)
        return {"current_value": round(avg_decay, 3), "normalized": normalized, "confidence": confidence}
    except Exception:
        return {"current_value": 0.0, "normalized": 0.5, "confidence": 0.0}


def _data_client_engagement() -> dict:
    try:
        actions = db.get_actions(status="OPEN", limit=100)
        active_client_actions = sum(1 for a in actions if a.get("from_name"))
        client_rels = db.get_relationships(type="client")
        touchpoints = active_client_actions + len(client_rels)
        normalized = min(1.0, touchpoints / 10.0)
        confidence = min(1.0, touchpoints / 5.0)
        return {"current_value": float(touchpoints), "normalized": normalized, "confidence": confidence}
    except Exception:
        return {"current_value": 0.0, "normalized": 0.5, "confidence": 0.0}


def _data_family_bandwidth() -> dict:
    try:
        log = db.get_attention_log(days=7)
        if not log:
            return {"current_value": 0.5, "normalized": 0.5, "confidence": 0.0}
        overload_frac = sum(1 for e in log if e.get("overload_flag")) / len(log)
        bandwidth = 1.0 - overload_frac
        confidence = min(1.0, len(log) / 7)
        return {"current_value": round(bandwidth, 3), "normalized": bandwidth, "confidence": confidence}
    except Exception:
        return {"current_value": 0.5, "normalized": 0.5, "confidence": 0.0}


def _data_operational_debt() -> dict:
    try:
        open_actions = db.get_actions(status="OPEN", limit=200)
        agents = db.get_agents("active")
        total_exceptions = sum(a.get("exception_count", 0) for a in agents)
        debt = len(open_actions) + total_exceptions
        raw = min(1.0, debt / 30.0)
        normalized = 1.0 - raw
        confidence = min(1.0, (len(open_actions) + len(agents)) / 10.0)
        return {"current_value": float(debt), "normalized": normalized, "confidence": confidence}
    except Exception:
        return {"current_value": 0.0, "normalized": 0.5, "confidence": 0.0}


def _data_focus_quality() -> dict:
    try:
        from attention_engine import get_focus_score
        score = get_focus_score(days=7)
        normalized = score / 10.0
        log = db.get_attention_log(days=7)
        confidence = min(1.0, len(log) / 7)
        return {"current_value": round(score, 2), "normalized": normalized, "confidence": confidence}
    except Exception:
        return {"current_value": 5.0, "normalized": 0.5, "confidence": 0.0}


def _data_followthrough() -> dict:
    try:
        feedback = db.get_all_feedback(days=30)
        if not feedback:
            return {"current_value": 0.5, "normalized": 0.5, "confidence": 0.0}
        executed = sum(1 for f in feedback if f.get("outcome") == "executed")
        failed = sum(1 for f in feedback if f.get("outcome") == "failed")
        total = executed + failed
        if total == 0:
            return {"current_value": 0.5, "normalized": 0.5, "confidence": 0.0}
        rate = executed / total
        confidence = min(1.0, total / 10.0)
        return {"current_value": round(rate, 3), "normalized": rate, "confidence": confidence}
    except Exception:
        return {"current_value": 0.5, "normalized": 0.5, "confidence": 0.0}


def _data_sleep_consistency() -> dict:
    # No direct sleep data — keyword scan of attention_log notes only
    try:
        log = db.get_attention_log(days=7)
        if not log:
            return {"current_value": 0.5, "normalized": 0.5, "confidence": 0.0}
        sleep_kw = {"sleep", "tired", "exhausted", "rested", "groggy", "fatigue"}
        bad_kw = {"tired", "exhausted", "groggy", "fatigue", "poor sleep"}
        mentions = [e for e in log if any(w in (e.get("notes") or "").lower() for w in sleep_kw)]
        if not mentions:
            return {"current_value": 0.5, "normalized": 0.5, "confidence": 0.0}
        bad = sum(1 for e in mentions if any(w in (e.get("notes") or "").lower() for w in bad_kw))
        bad_ratio = bad / len(mentions)
        normalized = 1.0 - bad_ratio
        confidence = min(0.5, len(mentions) / 7)  # indirect data → max 0.5
        return {"current_value": round(1.0 - bad_ratio, 3), "normalized": normalized, "confidence": confidence}
    except Exception:
        return {"current_value": 0.5, "normalized": 0.5, "confidence": 0.0}


def _data_business_momentum() -> dict:
    try:
        streams = db.get_revenue_streams()
        avg_growth = sum(s.get("growth_rate", 0) for s in streams) / max(len(streams), 1)
        growth_norm = min(1.0, max(0.0, 0.3 + avg_growth * 5))

        agents = db.get_agents("active")
        agents_ran = sum(1 for a in agents if (a.get("run_count") or 0) > 0)
        agent_norm = agents_ran / max(len(agents), 1)

        feedback = db.get_all_feedback(days=7)
        if feedback:
            executed = sum(1 for f in feedback if f.get("outcome") == "executed")
            completion_norm = min(1.0, executed / max(len(feedback), 1))
        else:
            completion_norm = 0.5

        composite = round(growth_norm * 0.4 + agent_norm * 0.3 + completion_norm * 0.3, 3)
        confidence = min(1.0, (len(streams) + len(agents)) / 10.0)
        return {"current_value": composite, "normalized": composite, "confidence": confidence}
    except Exception:
        return {"current_value": 0.5, "normalized": 0.5, "confidence": 0.0}


_DOMAIN_FUNCS = {
    "revenue":            _data_revenue,
    "stress":             _data_stress,
    "cognitive_load":     _data_cognitive_load,
    "relationship_decay": _data_relationship_decay,
    "client_engagement":  _data_client_engagement,
    "family_bandwidth":   _data_family_bandwidth,
    "operational_debt":   _data_operational_debt,
    "focus_quality":      _data_focus_quality,
    "followthrough":      _data_followthrough,
    "sleep_consistency":  _data_sleep_consistency,
    "business_momentum":  _data_business_momentum,
}


# ── Public API ─────────────────────────────────────────────────────────────────

def update_domain(domain: str) -> dict:
    """Compute trajectory state for one domain and persist it."""
    db.init()
    if domain not in _DOMAIN_FUNCS:
        raise ValueError(f"Unknown domain '{domain}'. Valid: {', '.join(_DOMAINS)}")

    prev_row = db.get_trajectory_state(domain)
    prev_score = prev_row.get("trajectory_score") if prev_row else None

    data = _DOMAIN_FUNCS[domain]()
    current_value = data["current_value"]
    normalized = data["normalized"]
    confidence = data["confidence"]

    trend = _compute_trend(normalized, prev_score)
    score = _trajectory_score(normalized)
    risk = _risk_level(score, confidence)

    proj_7d  = _project(current_value, score, 7)
    proj_30d = _project(current_value, score, 30)
    proj_90d = _project(current_value, score, 90)

    row = {
        "domain":           domain,
        "metric_name":      domain,
        "current_value":    current_value,
        "previous_value":   prev_row.get("current_value") if prev_row else None,
        "trend_direction":  trend,
        "trajectory_score": score,
        "risk_level":       risk,
        "projected_7d":     proj_7d,
        "projected_30d":    proj_30d,
        "projected_90d":    proj_90d,
        "confidence_score": round(confidence, 3),
    }
    db.upsert_trajectory_state(row)
    return row


def update_all_domains() -> list[dict]:
    """Update all 11 domains. Returns list of rows (or error dicts)."""
    db.init()
    results = []
    for domain in _DOMAINS:
        try:
            results.append(update_domain(domain))
        except Exception as e:
            results.append({"domain": domain, "error": str(e)})
    return results


def get_domain_state(domain: str) -> dict | None:
    """Read-only. Returns latest trajectory_state row for domain."""
    db.init()
    return db.get_trajectory_state(domain)


def get_system_trajectory() -> dict:
    """All 11 domain states sorted by risk, plus overall_health score."""
    db.init()
    states = db.get_all_trajectory_states()
    states.sort(key=lambda x: (_RISK_ORDER.get(x.get("risk_level", "low"), 3), x.get("domain", "")))

    scored = [s.get("trajectory_score", 0.0) for s in states if (s.get("confidence_score") or 0) > 0.1]
    overall = round(sum(scored) / len(scored), 3) if scored else 0.0

    return {
        "domains":        states,
        "overall_health": overall,
        "domain_count":   len(states),
    }


# ── CLI ────────────────────────────────────────────────────────────────────────

def _print_states(states: list[dict]):
    icons = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}
    trend_arrows = {"improving": "↑", "declining": "↓", "stable": "→", "unknown": "?"}
    for s in states:
        icon = icons.get(s.get("risk_level", "low"), "?")
        arrow = trend_arrows.get(s.get("trend_direction", "unknown"), "?")
        score = s.get("trajectory_score", 0.0) or 0.0
        conf = s.get("confidence_score", 0.0) or 0.0
        print(f"  {icon} {s['domain']:<18} score={score:+.2f}  conf={conf:.0%}  {arrow} {s.get('trend_direction','?')}")


if __name__ == "__main__":
    db.init()
    args = sys.argv[1:]
    cmd = args[0] if args else "status"

    if cmd == "update":
        print(f"\n  Trajectory Engine — updating all {len(_DOMAINS)} domains\n  {'─'*54}")
        results = update_all_domains()
        for r in results:
            if "error" in r:
                print(f"  ✗ {r['domain']}: {r['error']}")
        traj = get_system_trajectory()
        print(f"  Overall health: {traj['overall_health']:+.3f}\n")
        _print_states(traj["domains"])

    elif cmd == "status":
        traj = get_system_trajectory()
        print(f"\n  Trajectory Status — overall health: {traj['overall_health']:+.3f}\n  {'─'*54}")
        if not traj["domains"]:
            print("  No data. Run: python trajectory_engine.py update")
        else:
            _print_states(traj["domains"])

    elif cmd in _DOMAINS:
        row = update_domain(cmd)
        print(f"\n  {cmd}: score={row['trajectory_score']:+.3f}  risk={row['risk_level']}  "
              f"conf={row['confidence_score']:.0%}  trend={row['trend_direction']}")

    else:
        print("Usage: trajectory_engine.py [update | status | <domain>]")
        print(f"Domains: {', '.join(_DOMAINS)}")
