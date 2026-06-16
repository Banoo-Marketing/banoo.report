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

    try:
        ctx     = build_context()
        state   = ctx["context"]
        s       = state.get("state", {})
        clients = state.get("clients", [])
        at_risk = [c for c in clients if c.get("health") == "at_risk"]

        print()
        print("═" * _W)
        print("  YOUR AI BUSINESS CONTEXT IS READY")
        print("═" * _W)
        print()
        print(f"  Company : {state.get('company') or '(not set)'}")
        print(f"  Focus   : {state.get('focus') or '(not set)'}")
        print(f"  Revenue : {s.get('revenue', '').upper()}")
        print(f"  Clients : {len(clients)} active ({len(at_risk)} at risk)")
        print()
        print("  HOW TO USE")
        print(f"  {'─' * 40}")
        print("  1. Copy the text below")
        print("  2. Open ChatGPT or Claude")
        print("  3. Paste it BEFORE your question")
        print()
        print("  Example:")
        print('  Paste → then ask: "Write a follow-up email for my top client"')
        print('  Paste → then ask: "What should I focus on this week?"')
        print()
        print("─" * _W)
        print("  COPY FROM HERE")
        print("─" * _W)
        print()
        print(get_context_string())
        print()
        print("─" * _W)

    except Exception:
        print("\n  Could not generate context. Try: python onboarding/setup.py")
        sys.exit(1)


if __name__ == "__main__":
    main()
