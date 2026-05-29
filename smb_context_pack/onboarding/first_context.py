"""
onboarding/first_context.py — Display generated context after onboarding.

Validates setup is complete, then prints a copy-paste-ready AI context block.

Usage:
    python onboarding/first_context.py
"""
import sys
from pathlib import Path

_HERE = Path(__file__).parent
_ROOT = _HERE.parent

sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_HERE))

from api.context import build_context, get_context_string
from validator import run_validation

_W = 54


def main() -> None:
    if not run_validation():
        print("\n  Run setup.py first.")
        sys.exit(1)

    ctx     = build_context()
    state   = ctx["context"]
    s       = state.get("state", {})
    clients = state.get("clients", [])
    at_risk = [c for c in clients if c.get("health") == "at_risk"]

    print()
    print("═" * _W)
    print("  YOUR COMPANY CONTEXT IS READY")
    print("═" * _W)
    print()
    print(f"  COMPANY : {state.get('company', '(not set)')}")
    print(f"  FOCUS   : {state.get('focus', '(not set)')}")
    print(f"  REVENUE : {s.get('revenue', '').upper()}")
    print(f"  CLIENTS : {len(clients)} active ({len(at_risk)} at risk)")
    print(f"  TONE    : {state.get('tone', '')}")
    print()
    print("─" * _W)
    print("  COPY THIS INTO ANY AI TOOL")
    print("─" * _W)
    print()
    print(get_context_string())
    print()
    print("─" * _W)


if __name__ == "__main__":
    main()
