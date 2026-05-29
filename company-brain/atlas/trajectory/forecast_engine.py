"""
FROZEN — Not required for core product. Do not extend or activate.

forecast_engine.py — Probability-weighted multi-horizon forecasts.

Pure math + heuristics. No LLM calls.
Causality detection: identifies correlated declining domains.

Usage:
  python forecast_engine.py report     # Trajectory report (all domains)
  python forecast_engine.py forecast   # 7/30/90d projections
  python forecast_engine.py causality  # Cross-domain correlation patterns
"""
from __future__ import annotations
import sys
from pathlib import Path

_HERE = Path(__file__).parent
_ATLAS = _HERE.parent
_CHIEF = _ATLAS.parent / "chief"

sys.path.insert(0, str(_CHIEF))
sys.path.insert(0, str(_ATLAS))

try:
    from dotenv import load_dotenv
    load_dotenv(_ATLAS.parent / ".env")
except ImportError:
    pass

import db

_RISK_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}

_CORRELATED_GROUPS = {
    "revenue":            ["business_momentum", "client_engagement", "followthrough"],
    "stress":             ["cognitive_load", "family_bandwidth", "sleep_consistency"],
    "focus_quality":      ["cognitive_load", "operational_debt"],
    "relationship_decay": ["client_engagement"],
    "business_momentum":  ["revenue", "followthrough"],
}


def project_domain(domain: str, horizon_days: int) -> dict:
    """
    Return probability-weighted projection for a domain at a given horizon.
    suppress_escalation=True if confidence < 0.3.
    """
    db.init()
    state = db.get_trajectory_state(domain)
    if not state:
        return {
            "domain":              domain,
            "horizon_days":        horizon_days,
            "projected_value":     None,
            "probability":         0.1,
            "confidence":          0.0,
            "risk_trajectory":     "unknown",
            "reasoning":           ["No data available for this domain."],
            "suppress_escalation": True,
        }

    current_value  = state.get("current_value") or 0.0
    score          = state.get("trajectory_score") or 0.0
    confidence     = state.get("confidence_score") or 0.0
    trend          = state.get("trend_direction") or "unknown"
    risk           = state.get("risk_level") or "low"

    daily_delta     = score * 0.02
    projected_value = round(current_value * (1 + daily_delta * horizon_days), 4)

    probability = confidence * (1 - abs(daily_delta) * horizon_days * 0.5)
    probability = round(max(0.1, min(0.95, probability)), 3)

    if score > 0.1:
        risk_trajectory = "improving"
    elif score < -0.1:
        risk_trajectory = "worsening"
    else:
        risk_trajectory = "stable"

    reasoning = _build_reasoning(domain, score, trend, risk, horizon_days, confidence)

    return {
        "domain":              domain,
        "horizon_days":        horizon_days,
        "projected_value":     projected_value,
        "probability":         probability,
        "confidence":          confidence,
        "risk_trajectory":     risk_trajectory,
        "reasoning":           reasoning,
        "suppress_escalation": confidence < 0.3,
    }


def _build_reasoning(domain: str, score: float, trend: str, risk: str,
                      horizon: int, confidence: float) -> list[str]:
    lines = []

    if risk in ("critical", "high"):
        lines.append(f"{domain} is at {risk} risk based on current trajectory score ({score:+.2f}).")
    elif risk == "medium":
        lines.append(f"{domain} shows moderate concern (score {score:+.2f}).")
    else:
        lines.append(f"{domain} is within acceptable range (score {score:+.2f}).")

    if trend == "declining":
        lines.append(f"Trend is declining. At current rate, value continues downward over {horizon} days.")
    elif trend == "improving":
        lines.append(f"Trend is improving. Trajectory is positive over the {horizon}-day horizon.")
    elif trend == "stable":
        lines.append("No directional change detected. Current conditions expected to hold.")

    if confidence < 0.3:
        lines.append("Insufficient data for reliable projection. Treat as indicative only.")

    return lines[:3]


def detect_causality(domains: list[str]) -> list[dict]:
    """
    Cross-domain analysis. Returns correlated declining patterns.
    Only flags patterns where confidence >= 0.7 (7 days of data).
    """
    db.init()
    declining: list[tuple[str, dict, int]] = []

    for d in domains:
        state = db.get_trajectory_state(d)
        if not state:
            continue
        if state.get("trend_direction") == "declining" and (state.get("confidence_score") or 0) >= 0.7:
            days_obs = round((state.get("confidence_score") or 0) * 7)
            if days_obs >= 5:
                declining.append((d, state, days_obs))

    if len(declining) < 2:
        return []

    declining_names = {d for d, _, _ in declining}
    results = []
    seen_primaries: set[str] = set()

    for primary, _, primary_days in declining:
        if primary in seen_primaries:
            continue
        correlated = [
            d for d in _CORRELATED_GROUPS.get(primary, [])
            if d in declining_names and d != primary
        ]
        if correlated:
            min_days = min(primary_days, *[
                days for d, _, days in declining if d in correlated
            ])
            results.append({
                "primary_domain":     primary,
                "correlated_domains": correlated,
                "pattern":            f"{primary} and {', '.join(correlated)} declining simultaneously",
                "days_observed":      min_days,
            })
            seen_primaries.add(primary)
            seen_primaries.update(correlated)

    return results


def generate_trajectory_report() -> str:
    """
    Plain-text trajectory report. No LLM.
    Only lists domains with risk >= medium OR declining trend.
    Max 10 lines + causality block.
    """
    db.init()
    states = db.get_all_trajectory_states()
    if not states:
        return "No trajectory data. Run: atlas trajectory update"

    states.sort(key=lambda x: (_RISK_ORDER.get(x.get("risk_level", "low"), 3), x.get("domain", "")))

    trend_sym = {"improving": "↑", "declining": "↓", "stable": "→", "unknown": "?"}
    lines = []

    for s in states:
        risk = s.get("risk_level", "low")
        trend = s.get("trend_direction", "unknown")
        if risk not in ("medium", "high", "critical") and trend != "declining":
            continue
        conf_pct = round((s.get("confidence_score") or 0) * 100)
        score = s.get("trajectory_score") or 0.0
        sym = trend_sym.get(trend, "?")
        # project 30d
        cv = s.get("current_value") or 0.0
        daily_delta = score * 0.02
        proj = round(cv * (1 + daily_delta * 30), 3)

        lines.append(
            f"{s['domain']:<18}: {risk:<8} {sym} {trend:<10} "
            f"(conf {conf_pct}%)  30d→{proj}"
        )

    if not lines:
        return "All systems nominal. No domains at elevated risk."

    report = "\n".join(lines[:10])

    # Add causality patterns
    all_domains = [s["domain"] for s in states]
    patterns = detect_causality(all_domains)
    if patterns:
        report += "\n\nCORRELATED PATTERNS:"
        for p in patterns:
            report += f"\n  {p['pattern']} ({p['days_observed']}d observed)"

    return report


# ── CLI ────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    db.init()
    args = sys.argv[1:]
    cmd = args[0] if args else "report"

    if cmd == "report":
        print(f"\n  Trajectory Report\n  {'─'*60}")
        print(generate_trajectory_report())

    elif cmd == "forecast":
        states = db.get_all_trajectory_states()
        if not states:
            print("  No trajectory data. Run: atlas trajectory update")
        else:
            print(f"\n  7 / 30 / 90-Day Forecasts\n  {'─'*60}")
            for s in states:
                d = s["domain"]
                f7  = project_domain(d, 7)
                f30 = project_domain(d, 30)
                f90 = project_domain(d, 90)
                if f7.get("suppress_escalation") and f30.get("risk_trajectory") == "stable":
                    continue
                sym = {"improving": "↑", "worsening": "↓", "stable": "→", "unknown": "?"}.get(
                    f30["risk_trajectory"], "?")
                print(f"  {d:<18} 7d={f7['projected_value']}  30d={f30['projected_value']}  "
                      f"90d={f90['projected_value']}  {sym} prob={f30['probability']:.0%}")

    elif cmd == "causality":
        states = db.get_all_trajectory_states()
        patterns = detect_causality([s["domain"] for s in states])
        print(f"\n  Causality Patterns\n  {'─'*50}")
        if not patterns:
            print("  No correlated declining patterns detected.")
        for p in patterns:
            print(f"  {p['pattern']}")
            print(f"  Observed: {p['days_observed']} days")

    else:
        print("Usage: forecast_engine.py [report | forecast | causality]")
