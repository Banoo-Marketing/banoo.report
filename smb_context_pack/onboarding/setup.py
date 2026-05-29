"""
onboarding/setup.py — SMB Context Pack onboarding.

3 steps. ~5 minutes. Outputs a ready-to-use AI context string.

Usage:
    python onboarding/setup.py
"""
import json
import sys
import subprocess
from pathlib import Path

_HERE = Path(__file__).parent
_ROOT = _HERE.parent

sys.path.insert(0, str(_ROOT))

from memory.log import log_entry

_PROFILE = _ROOT / "company_profile"


def _ask(label: str, default: str = "") -> str:
    val = input(f"  {label}: ").strip()
    if not val:
        val = input(f"  {label}: ").strip()
    return val or default


def _ask_choice(label: str, choices: list[str], default: str) -> str:
    opts = " / ".join(choices)
    val = input(f"  {label} ({opts}) [{default}]: ").strip().lower()
    return val if val in choices else default


def _step1_identity() -> dict:
    print("\n── STEP 1: COMPANY IDENTITY ──\n")
    return {
        "company_name":     _ask("Company name"),
        "what_we_do":       _ask("What we do"),
        "main_offer":       _ask("Main offer"),
        "target_customers": _ask("Target customers"),
        "tone":             _ask_choice("Tone", ["direct", "casual", "simple"], "direct"),
    }


def _step2_quick_facts() -> dict:
    print("\n── STEP 2: QUICK FACTS ──\n")
    raw = _ask("Top clients (comma-separated, max 3)", "")
    clients = [c.strip() for c in raw.split(",") if c.strip()][:3]
    return {
        "top_clients":         clients,
        "main_revenue_source": _ask("Main revenue source"),
        "current_problem":     _ask("Current problem"),
        "biggest_opportunity": _ask("Biggest opportunity"),
        "current_focus":       _ask("Current focus"),
    }


def _step3_memory() -> None:
    print("\n── STEP 3: FIRST MEMORY ENTRY ──\n")
    entity  = _ask("Entity (client name, topic, or project)")
    content = _ask("What happened?")
    log_entry(entity, "manual", content, source="onboarding")


def run() -> None:
    print("\n  SMB Context Pack — Onboarding")
    print("  Getting you AI-ready in under 10 minutes.\n")

    # Step 1
    identity = _step1_identity()
    _PROFILE.mkdir(exist_ok=True)
    (_PROFILE / "identity.json").write_text(json.dumps(identity, indent=2))
    (_PROFILE / "tone.json").write_text(json.dumps({
        "style": identity["tone"],
        "avoid": ["corporate language", "long explanations"],
    }, indent=2))
    print("\n  ✓ Saved.")

    # Step 2
    quick = _step2_quick_facts()
    (_PROFILE / "quick_facts.json").write_text(json.dumps(quick, indent=2))
    # Patch identity with current_focus so the context engine surfaces it
    identity["current_focus"] = quick["current_focus"]
    (_PROFILE / "identity.json").write_text(json.dumps(identity, indent=2))
    print("\n  ✓ Saved.")

    # Step 3
    _step3_memory()
    print("\n  ✓ Saved.")

    print("\n  Generating your context...\n")
    subprocess.run([sys.executable, str(_HERE / "first_context.py")])


if __name__ == "__main__":
    run()
