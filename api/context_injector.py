"""
api/context_injector.py — Context Injection API.

THIS IS THE CORE PRODUCT.

Any AI system calls build_context() and immediately becomes:
- company-aware
- tone-aware
- client-aware
- priority-aware

Usage (Python):
    from api.context_injector import build_context, get_context_string
    ctx = build_context()

Usage (CLI):
    python api/context_injector.py          # Print formatted context
    python api/context_injector.py --json   # Print raw JSON
    python api/context_injector.py --prompt # Print as prompt-ready string
"""
import json
import sys
from pathlib import Path

_HERE = Path(__file__).parent
_ROOT = _HERE.parent

sys.path.insert(0, str(_ROOT))

from context_engine.engine import load_company_brain, get_recent_memory, get_context_snapshot


def get_system_constraints() -> dict:
    constraints_path = _ROOT / "constraints.json"
    if constraints_path.exists():
        try:
            return json.loads(constraints_path.read_text())
        except Exception:
            pass
    return {}


def build_context(memory_limit: int = 20) -> dict:
    """
    Return full context package.

    {
        "brain":       all company_brain JSON files,
        "memory":      last N memory entries (newest first),
        "state":       current context snapshot,
        "constraints": system constraints
    }
    """
    return {
        "brain":       load_company_brain(),
        "memory":      get_recent_memory(limit=memory_limit),
        "state":       get_context_snapshot(),
        "constraints": get_system_constraints(),
    }


def get_context_string(memory_limit: int = 10) -> str:
    """
    Return context as a compact, prompt-ready string.
    Use this to inject context into any AI system prompt.
    """
    ctx = build_context(memory_limit=memory_limit)
    state = ctx["state"]
    brain = ctx["brain"]
    identity = brain.get("identity", {})
    tone = brain.get("tone_of_voice", {})
    constraints = ctx["constraints"]

    lines = [
        f"COMPANY: {state.get('company', '')}",
        f"MISSION: {identity.get('mission', '')}",
        f"POSITIONING: {identity.get('positioning', '')}",
        f"",
        f"CURRENT STATE:",
        f"  Focus: {state.get('focus', '')}",
        f"  Revenue: {state.get('revenue_state', '').upper()}",
        f"  Operations: {state.get('operational_state', '').upper()}",
        f"  Active clients: {state.get('active_clients', 0)} ({state.get('at_risk_clients', 0)} at risk)",
        f"",
        f"TOP PRIORITIES:",
    ]
    for i, p in enumerate(state.get("top_priorities", []), 1):
        lines.append(f"  {i}. {p}")

    active_risks = identity.get("active_risks", [])
    if active_risks:
        lines.append("")
        lines.append("ACTIVE RISKS:")
        for r in active_risks:
            lines.append(f"  - {r}")

    lines.extend([
        "",
        "TONE:",
        f"  Style: {tone.get('style', '')}",
        f"  Avoid: {', '.join(tone.get('avoid', [])[:3])}",
    ])

    max_p = constraints.get("max_active_priorities", 3)
    forbidden = constraints.get("forbidden_behaviors", [])
    if forbidden:
        lines.extend([
            "",
            "CONSTRAINTS:",
            f"  Max active priorities: {max_p}",
            f"  Never: {', '.join(forbidden[:3])}",
        ])

    recent_memory = ctx["memory"][:5]
    if recent_memory:
        lines.extend(["", "RECENT CONTEXT:"])
        for e in recent_memory:
            tag_str = f" [{', '.join(e.get('tags', [])[:2])}]" if e.get("tags") else ""
            lines.append(f"  [{e.get('entity', '?')}] {e.get('content', '')[:120]}{tag_str}")

    return "\n".join(lines)


# ── CLI ────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    args = sys.argv[1:]

    if "--json" in args:
        print(json.dumps(build_context(), indent=2, default=str))

    elif "--prompt" in args:
        print(get_context_string())

    else:
        ctx = build_context()
        state = ctx["state"]
        memory = ctx["memory"]

        print(f"\n  Context Injector — Banoo Company Brain")
        print(f"  {'═' * 56}")
        print(f"\n  STATE")
        print(f"  {'─' * 40}")
        print(f"  Company     : {state.get('company')}")
        print(f"  Revenue     : {state.get('revenue_state', '').upper()}")
        print(f"  Operations  : {state.get('operational_state', '').upper()}")
        print(f"  Clients     : {state.get('active_clients')} active / {state.get('at_risk_clients')} at risk")
        print(f"  Tone        : {state.get('communication_tone')}")

        print(f"\n  PRIORITIES")
        print(f"  {'─' * 40}")
        for i, p in enumerate(state.get("top_priorities", []), 1):
            print(f"  {i}. {p}")

        print(f"\n  RECENT MEMORY ({len(memory)} entries)")
        print(f"  {'─' * 40}")
        for e in memory[:5]:
            folder = e.get("_folder", "?")
            tags = e.get("tags", [])
            tag_str = f"  [{', '.join(tags[:2])}]" if tags else ""
            print(f"  [{folder}/{e.get('entity', '?')}] {e.get('content', '')[:80]}{tag_str}")

        print(f"\n  BRAIN FILES: {', '.join(ctx['brain'].keys())}")
        print(f"\n  → build_context()  — full dict for AI system integration")
        print(f"  → get_context_string()  — prompt-ready string injection")
