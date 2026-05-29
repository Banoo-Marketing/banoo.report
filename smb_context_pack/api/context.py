"""
api/context.py — Context Injection API.

THE PRODUCT INTERFACE.

Any AI system calls build_context() or get_context_string() and
immediately becomes company-aware, tone-aware, client-aware, priority-aware.

Usage (Python):
    import sys
    sys.path.insert(0, "/path/to/smb_context_pack")
    from api.context import build_context, get_context_string

    ctx    = build_context()           # full structured dict
    prompt = get_context_string()      # paste into any AI system prompt

Usage (CLI):
    python api/context.py          # Formatted summary
    python api/context.py --json   # Raw JSON
    python api/context.py --prompt # Prompt-ready string
"""
import json
import sys
from pathlib import Path

_HERE = Path(__file__).parent
_ROOT = _HERE.parent

sys.path.insert(0, str(_ROOT))

from context_engine.engine import load_profile, get_recent_memory, generate_snapshot


def get_constraints() -> dict:
    path = _ROOT / "constraints.json"
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            pass
    return {}


def build_context(memory_limit: int = 20) -> dict:
    """
    Full context package for AI integration.

    {
        "company_profile": all company_profile JSON files,
        "memory":          last N memory entries (newest first),
        "context":         current state snapshot,
        "constraints":     system constraints
    }
    """
    return {
        "company_profile": load_profile(),
        "memory":          get_recent_memory(limit=memory_limit),
        "context":         generate_snapshot(),
        "constraints":     get_constraints(),
    }


def get_context_string(memory_limit: int = 10) -> str:
    """
    Prompt-ready context string.
    Prepend to any AI system prompt to make it instantly company-aware.
    """
    ctx         = build_context(memory_limit=memory_limit)
    state       = ctx["context"]
    profile     = ctx["company_profile"]
    identity    = profile.get("identity", {})
    tone_data   = profile.get("tone", {})
    constraints = ctx["constraints"]

    s        = state.get("state", {})
    clients  = state.get("clients", [])
    at_risk  = [c for c in clients if c.get("health") == "at_risk"]

    lines = [
        f"COMPANY: {state.get('company', '')}",
        f"MISSION: {identity.get('mission', '')}",
        f"POSITIONING: {identity.get('positioning', '')}",
        "",
        "CURRENT STATE:",
        f"  Focus: {state.get('focus', '')}",
        f"  Revenue: {s.get('revenue', '').upper()}",
        f"  Operations: {s.get('operations', '').upper()}",
        f"  Relationships: {s.get('relationships', '').upper()}",
        f"  Active clients: {len(clients)} ({len(at_risk)} at risk)",
        "",
        "TOP PRIORITIES:",
    ]
    for i, p in enumerate(state.get("top_priorities", []), 1):
        lines.append(f"  {i}. {p}")

    risks = state.get("risks", [])
    if risks:
        lines += ["", "ACTIVE RISKS:"]
        for r in risks:
            lines.append(f"  - {r}")

    avoid = tone_data.get("avoid", [])
    lines += ["", "TONE:", f"  Style: {state.get('tone', '')}"]
    if avoid:
        lines.append(f"  Avoid: {', '.join(avoid[:3])}")

    forbidden = constraints.get("forbidden_behaviors", [])
    if forbidden:
        lines += [
            "",
            "CONSTRAINTS:",
            f"  Max priorities: {constraints.get('max_priorities', 3)}",
            f"  Never: {', '.join(forbidden[:3])}",
        ]

    recent = ctx["memory"][:5]
    if recent:
        lines += ["", "RECENT CONTEXT:"]
        for e in recent:
            lines.append(f"  [{e.get('entity', '?')}] {e.get('content', '')[:120]}")

    return "\n".join(lines)


# ── CLI ────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    args = sys.argv[1:]

    if "--json" in args:
        print(json.dumps(build_context(), indent=2, default=str))

    elif "--prompt" in args:
        print(get_context_string())

    else:
        ctx     = build_context()
        state   = ctx["context"]
        s       = state.get("state", {})
        memory  = ctx["memory"]
        clients = state.get("clients", [])
        at_risk = [c for c in clients if c.get("health") == "at_risk"]

        print(f"\n  SMB Context Pack — {state.get('company') or '(company not set)'}")
        print(f"  {'═' * 56}")
        print(f"\n  STATE")
        print(f"  {'─' * 40}")
        print(f"  Company       : {state.get('company') or '(not set)'}")
        print(f"  Focus         : {state.get('focus') or '(not set)'}")
        print(f"  Revenue       : {s.get('revenue', '').upper()}")
        print(f"  Operations    : {s.get('operations', '').upper()}")
        print(f"  Relationships : {s.get('relationships', '').upper()}")
        print(f"  Clients       : {len(clients)} active / {len(at_risk)} at risk")
        print(f"  Tone          : {state.get('tone', '')}")

        if state.get("top_priorities"):
            print(f"\n  PRIORITIES")
            print(f"  {'─' * 40}")
            for i, p in enumerate(state["top_priorities"], 1):
                print(f"  {i}. {p}")

        if state.get("risks"):
            print(f"\n  RISKS")
            print(f"  {'─' * 40}")
            for r in state["risks"]:
                print(f"  - {r}")

        print(f"\n  MEMORY ({len(memory)} entries)")
        print(f"  {'─' * 40}")
        if memory:
            for e in memory[:5]:
                print(f"  [{e.get('type', '?')}/{e.get('entity', '?')}] {e.get('content', '')[:80]}")
        else:
            print("  (empty — add entries with: python memory/log.py)")

        print(f"\n  → build_context()      — full dict for AI integration")
        print(f"  → get_context_string() — prompt-ready string injection")
