"""
onboarding/validator.py — Validate onboarding completeness.

Checks identity.json, quick_facts.json, and at least 1 memory entry.

Usage:
    python onboarding/validator.py   # exits 0 if all pass, 1 if any fail
"""
import json
import sys
from pathlib import Path

_HERE    = Path(__file__).parent
_ROOT    = _HERE.parent
_PROFILE = _ROOT / "company_profile"
_ENTRIES = _ROOT / "memory" / "entries"

_IDENTITY_FIELDS   = ["company_name", "what_we_do", "main_offer", "target_customers", "tone"]
_QUICK_FACTS_FIELDS = ["top_clients", "main_revenue_source", "current_problem",
                       "biggest_opportunity", "current_focus"]


def validate_identity() -> tuple[bool, list[str]]:
    path = _PROFILE / "identity.json"
    if not path.exists():
        return False, ["identity.json missing"]
    try:
        data = json.loads(path.read_text())
    except Exception:
        return False, ["identity.json is not valid JSON"]
    missing = [f for f in _IDENTITY_FIELDS if not str(data.get(f, "")).strip()]
    return (not missing), missing


def validate_quick_facts() -> tuple[bool, list[str]]:
    path = _PROFILE / "quick_facts.json"
    if not path.exists():
        return False, ["quick_facts.json missing"]
    try:
        data = json.loads(path.read_text())
    except Exception:
        return False, ["quick_facts.json is not valid JSON"]
    missing = []
    for f in _QUICK_FACTS_FIELDS:
        val = data.get(f)
        if val is None or (isinstance(val, (str, list)) and not val):
            missing.append(f)
    return (not missing), missing


def validate_memory() -> tuple[bool, int]:
    if not _ENTRIES.exists():
        return False, 0
    count = len(list(_ENTRIES.glob("*.json")))
    return count >= 1, count


def run_validation() -> bool:
    results = []

    ok_id, missing_id = validate_identity()
    if ok_id:
        print("  ✓ Identity: complete")
    else:
        print(f"  ✗ Identity: missing fields: {', '.join(missing_id)}")
    results.append(ok_id)

    ok_qf, missing_qf = validate_quick_facts()
    if ok_qf:
        print("  ✓ Quick facts: complete")
    else:
        print(f"  ✗ Quick facts: {', '.join(missing_qf)}")
    results.append(ok_qf)

    ok_mem, count = validate_memory()
    if ok_mem:
        print(f"  ✓ Memory: {count} {'entry' if count == 1 else 'entries'}")
    else:
        print("  ✗ Memory: no entries found")
    results.append(ok_mem)

    return all(results)


if __name__ == "__main__":
    passed = run_validation()
    sys.exit(0 if passed else 1)
