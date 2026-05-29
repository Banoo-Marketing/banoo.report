"""
validate.py — Lightweight schema validation for SMB Context Pack.

Checks profile files, memory entries, and context output.
Returns plain English errors only — no technical output.

Usage:
    python validate.py       # Check all (exits 0 if clean, 1 if issues)
"""
import json
import sys
from pathlib import Path

_ROOT    = Path(__file__).parent
_PROFILE = _ROOT / "company_profile"
_ENTRIES = _ROOT / "memory" / "entries"

_IDENTITY_REQUIRED    = ["company_name", "what_we_do", "main_offer", "target_customers"]
_MEMORY_REQUIRED      = ["timestamp", "type", "entity", "content", "source"]
_CONTEXT_REQUIRED     = ["company", "focus", "clients", "risks", "state", "tone", "top_priorities"]
_VALID_REVENUE        = {"strong", "stable", "weak"}
_VALID_OPERATIONS     = {"stable", "overloaded", "underutilized"}
_VALID_RELATIONSHIPS  = {"healthy", "at_risk", "fragile"}


def validate_identity() -> list[str]:
    path = _PROFILE / "identity.json"
    if not path.exists():
        return ["Company profile not found — run: python onboarding/setup.py"]
    try:
        data = json.loads(path.read_text())
    except Exception:
        return ["Company profile is corrupted — run: python onboarding/setup.py"]
    errors = []
    for field in _IDENTITY_REQUIRED:
        if not str(data.get(field, "")).strip():
            errors.append(f"Missing {field.replace('_', ' ').title()}")
    return errors


def validate_tone() -> list[str]:
    path = _PROFILE / "tone.json"
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text())
    except Exception:
        return ["Tone file is corrupted — delete and re-run setup"]
    if not str(data.get("style", "")).strip():
        return ["Tone style is empty"]
    return []


def validate_memory_entries() -> list[str]:
    if not _ENTRIES.exists():
        return []
    errors = []
    for f in sorted(_ENTRIES.glob("*.json")):
        try:
            data = json.loads(f.read_text())
        except Exception:
            errors.append(f"Memory file {f.name} is corrupted")
            continue
        for field in _MEMORY_REQUIRED:
            if not str(data.get(field, "")).strip():
                errors.append(f"Memory entry {f.name} missing: {field}")
    return errors


def validate_context_output(snapshot: dict) -> list[str]:
    errors = []
    for field in _CONTEXT_REQUIRED:
        if snapshot.get(field) is None:
            errors.append(f"Context output missing required field: {field}")
    state = snapshot.get("state", {})
    rev = state.get("revenue", "")
    if rev and rev not in _VALID_REVENUE:
        errors.append(f"Invalid revenue state '{rev}' — expected: strong, stable, or weak")
    ops = state.get("operations", "")
    if ops and ops not in _VALID_OPERATIONS:
        errors.append(f"Invalid operations state '{ops}' — expected: stable, overloaded, or underutilized")
    rel = state.get("relationships", "")
    if rel and rel not in _VALID_RELATIONSHIPS:
        errors.append(f"Invalid relationships state '{rel}' — expected: healthy, at_risk, or fragile")
    return errors


def run_all(verbose: bool = True) -> bool:
    all_errors = []
    all_errors += validate_identity()
    all_errors += validate_tone()
    all_errors += validate_memory_entries()

    try:
        sys.path.insert(0, str(_ROOT))
        from context_engine.engine import generate_snapshot
        snapshot = generate_snapshot()
        all_errors += validate_context_output(snapshot)
    except Exception:
        all_errors.append("Context engine could not run — check your installation")

    if verbose:
        if all_errors:
            print(f"\n  {len(all_errors)} issue{'s' if len(all_errors) > 1 else ''} found:\n")
            for e in all_errors:
                print(f"  ✗ {e}")
            print()
        else:
            print("\n  ✓ All checks passed\n")

    return len(all_errors) == 0


if __name__ == "__main__":
    ok = run_all()
    sys.exit(0 if ok else 1)
