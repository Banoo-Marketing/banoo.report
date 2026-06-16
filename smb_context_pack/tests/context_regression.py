"""
tests/context_regression.py — Context stability regression tests.

Ensures:
- same profile + memory always produces same output (deterministic)
- required fields always exist in snapshot
- state values are always valid
- memory entries always have correct schema
- all four format renderers produce non-empty output

Usage:
    python tests/context_regression.py
"""
import json
import sys
from pathlib import Path

_HERE = Path(__file__).parent
_ROOT = _HERE.parent
sys.path.insert(0, str(_ROOT))

from context_engine.engine import generate_snapshot, load_profile, get_recent_memory
from api.context import build_context, get_context_string

_SNAPSHOT_REQUIRED    = ["company", "focus", "clients", "risks", "state", "tone", "top_priorities"]
_STATE_REQUIRED       = ["revenue", "operations", "relationships"]
_VALID_REVENUE        = {"strong", "stable", "weak"}
_VALID_OPERATIONS     = {"stable", "overloaded", "underutilized"}
_VALID_RELATIONSHIPS  = {"healthy", "at_risk", "fragile"}
_MEMORY_REQUIRED      = ["timestamp", "type", "entity", "content", "source"]
_FORMATS              = ["default", "chatgpt", "claude", "gemini"]

_passed = 0
_failed = 0


def _check(name: str, condition: bool, detail: str = "") -> None:
    global _passed, _failed
    if condition:
        print(f"  ✓ {name}")
        _passed += 1
    else:
        msg = f" — {detail}" if detail else ""
        print(f"  ✗ {name}{msg}")
        _failed += 1


def test_deterministic_output() -> None:
    s1 = generate_snapshot()
    s2 = generate_snapshot()
    _check("Deterministic output", s1 == s2, "Two consecutive runs differ")


def test_snapshot_required_fields() -> None:
    snap = generate_snapshot()
    for field in _SNAPSHOT_REQUIRED:
        _check(f"Snapshot field: {field}", field in snap, f"Missing from snapshot")


def test_state_structure() -> None:
    snap  = generate_snapshot()
    state = snap.get("state", {})
    for field in _STATE_REQUIRED:
        _check(f"State field: {field}", field in state, "Missing from state")


def test_valid_state_values() -> None:
    snap  = generate_snapshot()
    state = snap.get("state", {})
    rev = state.get("revenue", "")
    _check("Revenue value valid", rev in _VALID_REVENUE,
           f"Got '{rev}', expected: {', '.join(sorted(_VALID_REVENUE))}")
    ops = state.get("operations", "")
    _check("Operations value valid", ops in _VALID_OPERATIONS,
           f"Got '{ops}', expected: {', '.join(sorted(_VALID_OPERATIONS))}")
    rel = state.get("relationships", "")
    _check("Relationships value valid", rel in _VALID_RELATIONSHIPS,
           f"Got '{rel}', expected: {', '.join(sorted(_VALID_RELATIONSHIPS))}")


def test_memory_schema() -> None:
    entries_dir = _ROOT / "memory" / "entries"
    if not entries_dir.exists():
        _check("Memory entries dir exists", False, "memory/entries/ not found")
        return
    files = list(entries_dir.glob("*.json"))
    if not files:
        _check("Memory schema (no entries)", True, "0 entries — skipped")
        return
    for f in files[:10]:
        try:
            data = json.loads(f.read_text())
        except Exception:
            _check(f"Memory file readable: {f.name}", False, "JSON parse error")
            continue
        for field in _MEMORY_REQUIRED:
            _check(
                f"Memory {f.name[:20]}: {field}",
                bool(str(data.get(field, "")).strip()),
                f"Empty or missing",
            )


def test_context_string_formats() -> None:
    for fmt in _FORMATS:
        try:
            text = get_context_string(fmt=fmt)
            _check(f"Format '{fmt}' non-empty", bool(text.strip()), "Returned empty string")
        except Exception as e:
            _check(f"Format '{fmt}' no exception", False, str(e))


def test_build_context_keys() -> None:
    ctx = build_context()
    for key in ("company_profile", "memory", "context", "constraints"):
        _check(f"build_context key: {key}", key in ctx)


def test_clients_structure() -> None:
    snap    = generate_snapshot()
    clients = snap.get("clients", [])
    _check("Clients is a list", isinstance(clients, list))
    for c in clients[:5]:
        _check(f"Client has name: {c.get('name', '?')}", bool(c.get("name", "")))
        _check(
            f"Client health valid: {c.get('name', '?')}",
            c.get("health", "ok") in {"ok", "at_risk"},
            f"Got '{c.get('health', '')}'",
        )


def run() -> bool:
    print(f"\n  SMB Context Pack — Regression Tests")
    print(f"  {'─' * 46}\n")

    test_deterministic_output()
    test_snapshot_required_fields()
    test_state_structure()
    test_valid_state_values()
    test_memory_schema()
    test_context_string_formats()
    test_build_context_keys()
    test_clients_structure()

    print(f"\n  {'─' * 46}")
    print(f"  {_passed} passed, {_failed} failed")
    print()
    return _failed == 0


if __name__ == "__main__":
    ok = run()
    sys.exit(0 if ok else 1)
