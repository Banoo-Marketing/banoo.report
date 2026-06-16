"""
strategic_context.py — Atlas Strategic Context Engine.

Provides read/write access to Emod's current life+business context.
Other agents call get_context() to inject strategic awareness into their outputs.

Usage:
  python strategic_context.py                   Show current context
  python strategic_context.py update '{"key":"value"}'  Update fields
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

_HERE = Path(__file__).parent        # atlas/context/
_ATLAS = _HERE.parent                 # atlas/
_CHIEF = _ATLAS.parent / "chief"

sys.path.insert(0, str(_CHIEF))
sys.path.insert(0, str(_ATLAS))

try:
    from dotenv import load_dotenv
    load_dotenv(_ATLAS.parent.parent / "company-brain" / ".env")
except ImportError:
    pass

import db


def get_context() -> dict:
    """Return current strategic context from DB. Always returns a valid dict."""
    db.init()
    ctx = db.get_strategic_context()
    # Parse JSON fields
    for field in ("active_focus", "deprioritized", "current_constraints"):
        val = ctx.get(field)
        if isinstance(val, str):
            try:
                ctx[field] = json.loads(val)
            except (json.JSONDecodeError, TypeError):
                ctx[field] = []
    return ctx


def update_context(updates: dict):
    """Update specific context fields."""
    db.init()
    db.upsert_strategic_context(updates)


def context_summary() -> str:
    """One-paragraph English summary for prompt injection."""
    ctx = get_context()
    focus = ", ".join(ctx.get("active_focus") or []) or "not set"
    constraints = ", ".join(ctx.get("current_constraints") or []) or "none"
    return (
        f"Life phase: {ctx.get('life_phase','?')}. "
        f"Primary goal: {ctx.get('primary_goal','?')}. "
        f"Active focus: {focus}. "
        f"Stress tolerance: {ctx.get('stress_tolerance','?')}. "
        f"Financial pressure: {ctx.get('financial_pressure','?')}. "
        f"Current constraints: {constraints}."
    )


def is_high_stress() -> bool:
    """True if stress_tolerance is low/very_low or financial_pressure is high/critical."""
    ctx = get_context()
    stress = (ctx.get("stress_tolerance") or "").lower()
    pressure = (ctx.get("financial_pressure") or "").lower()
    return stress in ("low", "very_low", "critical") or pressure in ("high", "critical", "very_high")


def get_active_focus() -> list[str]:
    """Return active_focus list from context."""
    ctx = get_context()
    return ctx.get("active_focus") or []


def _print_context():
    ctx = get_context()
    print(f"\n  Atlas Strategic Context\n  {'─'*52}")
    print(f"  Life phase         : {ctx.get('life_phase','?')}")
    print(f"  Primary goal       : {ctx.get('primary_goal','?')}")
    print(f"  Active focus       : {', '.join(ctx.get('active_focus') or [])}")
    print(f"  Deprioritized      : {', '.join(ctx.get('deprioritized') or [])}")
    print(f"  Stress tolerance   : {ctx.get('stress_tolerance','?')}")
    print(f"  Financial pressure : {ctx.get('financial_pressure','?')}")
    print(f"  Constraints        : {', '.join(ctx.get('current_constraints') or [])}")
    last_date = ctx.get('last_date_night')
    print(f"  Last date night    : {last_date or 'not logged'}")
    print(f"  Updated            : {ctx.get('updated_at','?')[:16]}")


if __name__ == "__main__":
    db.init()
    args = sys.argv[1:]
    if args and args[0] == "update":
        if len(args) < 2:
            print("Usage: strategic_context.py update '<json>'")
        else:
            try:
                updates = json.loads(args[1])
                update_context(updates)
                print("  Context updated.")
                _print_context()
            except json.JSONDecodeError as e:
                print(f"  Invalid JSON: {e}")
    else:
        _print_context()
