"""
api/context.py — Context Injection API.

THE PRODUCT INTERFACE.

Usage (Python):
    from api.context import build_context, get_context_string

    ctx    = build_context()                  # full structured dict
    prompt = get_context_string()             # default format
    prompt = get_context_string(fmt="claude") # claude / chatgpt / gemini

Usage (CLI):
    python api/context.py                # Formatted summary
    python api/context.py --json         # Raw JSON
    python api/context.py --chatgpt      # ChatGPT-optimized string
    python api/context.py --claude       # Claude-optimized string
    python api/context.py --gemini       # Gemini compact string
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
    Full context package.

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


# ── Format renderers ───────────────────────────────────────────────────────────

def _resolve(ctx: dict) -> tuple:
    """Extract commonly used values from context dict."""
    state       = ctx["context"]
    profile     = ctx["company_profile"]
    identity    = profile.get("identity", {})
    tone_data   = profile.get("tone", {})
    constraints = ctx["constraints"]

    s       = state.get("state", {})
    clients = state.get("clients", [])
    at_risk = [c for c in clients if c.get("health") == "at_risk"]

    # what_we_do / target_customers are the onboarding field names;
    # mission / positioning are the legacy field names — support both
    mission     = identity.get("mission") or identity.get("what_we_do", "")
    positioning = identity.get("positioning") or identity.get("target_customers", "")

    return state, s, clients, at_risk, mission, positioning, tone_data, constraints


def _fmt_default(ctx: dict) -> str:
    """Clean labeled text — works with any AI."""
    state, s, clients, at_risk, mission, positioning, tone_data, constraints = _resolve(ctx)

    lines = [f"COMPANY: {state.get('company', '')}"]
    if mission:
        lines.append(f"WHAT WE DO: {mission}")
    if positioning:
        lines.append(f"CUSTOMERS: {positioning}")

    lines += [
        "",
        "CURRENT STATE:",
        f"  Focus: {state.get('focus', '')}",
        f"  Revenue: {s.get('revenue', '').upper()}",
        f"  Operations: {s.get('operations', '').upper()}",
        f"  Clients: {len(clients)} active ({len(at_risk)} at risk)",
    ]

    priorities = state.get("top_priorities", [])
    if priorities:
        lines += ["", "TOP PRIORITIES:"]
        for i, p in enumerate(priorities, 1):
            lines.append(f"  {i}. {p}")

    risks = state.get("risks", [])
    if risks:
        lines += ["", "ACTIVE RISKS:"]
        for r in risks:
            lines.append(f"  - {r}")

    avoid = tone_data.get("avoid", [])
    lines += ["", f"TONE: {state.get('tone', '')}"]
    if avoid:
        lines.append(f"AVOID: {', '.join(avoid[:3])}")

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
        lines += ["", "RECENT:"]
        for e in recent:
            lines.append(f"  [{e.get('entity', '?')}] {e.get('content', '')[:100]}")

    return "\n".join(lines)


def _fmt_chatgpt(ctx: dict) -> str:
    """Markdown format — optimized for ChatGPT."""
    state, s, clients, at_risk, mission, positioning, tone_data, _ = _resolve(ctx)

    lines = [f"### Business Context: {state.get('company', '')}"]
    if mission:
        lines.append(f"**What we do:** {mission}")
    if positioning:
        lines.append(f"**Customers:** {positioning}")
    if state.get("focus"):
        lines.append(f"**Current focus:** {state['focus']}")

    lines += [
        "",
        f"**State:** Revenue {s.get('revenue','').upper()} | "
        f"Operations {s.get('operations','').upper()} | "
        f"Clients {len(clients)} active ({len(at_risk)} at risk)",
    ]

    priorities = state.get("top_priorities", [])
    if priorities:
        lines += ["", "**Top priorities:**"]
        for i, p in enumerate(priorities, 1):
            lines.append(f"{i}. {p}")

    risks = state.get("risks", [])
    if risks:
        lines += ["", "**Active risks:**"]
        for r in risks:
            lines.append(f"- {r}")

    avoid = tone_data.get("avoid", [])
    tone_line = f"**Tone:** {state.get('tone', '')}"
    if avoid:
        tone_line += f" | Avoid: {', '.join(avoid[:3])}"
    lines += ["", tone_line]

    recent = ctx["memory"][:5]
    if recent:
        lines += ["", "**Recent:**"]
        for e in recent:
            lines.append(f"- [{e.get('entity','?')}] {e.get('content','')[:100]}")

    return "\n".join(lines)


def _fmt_claude(ctx: dict) -> str:
    """XML-tagged format — optimized for Claude."""
    state, s, clients, at_risk, mission, positioning, tone_data, _ = _resolve(ctx)

    avoid = ", ".join(tone_data.get("avoid", [])[:3])
    lines = [f'<business_context company="{state.get("company", "")}">']

    lines.append("  <identity>")
    if mission:
        lines.append(f"    <what_we_do>{mission}</what_we_do>")
    if positioning:
        lines.append(f"    <customers>{positioning}</customers>")
    if state.get("focus"):
        lines.append(f"    <focus>{state['focus']}</focus>")
    lines.append("  </identity>")

    lines.append(
        f'  <state revenue="{s.get("revenue","")}" '
        f'operations="{s.get("operations","")}" '
        f'clients="{len(clients)} active, {len(at_risk)} at risk" />'
    )

    priorities = state.get("top_priorities", [])
    if priorities:
        lines.append("  <priorities>")
        for p in priorities:
            lines.append(f"    <item>{p}</item>")
        lines.append("  </priorities>")

    risks = state.get("risks", [])
    if risks:
        lines.append("  <risks>")
        for r in risks:
            lines.append(f"    <item>{r}</item>")
        lines.append("  </risks>")

    lines.append(f'  <tone style="{state.get("tone","")}" avoid="{avoid}" />')

    recent = ctx["memory"][:5]
    if recent:
        lines.append("  <memory>")
        for e in recent:
            lines.append(
                f'    <event entity="{e.get("entity","")}">'
                f'{e.get("content","")[:100]}</event>'
            )
        lines.append("  </memory>")

    lines.append("</business_context>")
    return "\n".join(lines)


def _fmt_gemini(ctx: dict) -> str:
    """Compact key-value format — token-efficient for Gemini."""
    state, s, clients, at_risk, mission, positioning, tone_data, _ = _resolve(ctx)

    header_parts = [
        f"COMPANY:{state.get('company','')}",
        f"FOCUS:{state.get('focus','')}",
        f"REVENUE:{s.get('revenue','').upper()}",
        f"CLIENTS:{len(clients)}({len(at_risk)} at risk)",
        f"TONE:{state.get('tone','')}",
    ]
    lines = ["|".join(p for p in header_parts if not p.endswith(":"))]

    if mission:
        lines.append(f"WHAT WE DO: {mission}")
    if positioning:
        lines.append(f"CUSTOMERS: {positioning}")

    for i, p in enumerate(state.get("top_priorities", []), 1):
        lines.append(f"PRIORITY{i}: {p}")

    for r in state.get("risks", []):
        lines.append(f"RISK: {r}")

    avoid = tone_data.get("avoid", [])
    if avoid:
        lines.append(f"AVOID: {', '.join(avoid[:3])}")

    for e in ctx["memory"][:5]:
        lines.append(f"MEMORY: [{e.get('entity','?')}] {e.get('content','')[:100]}")

    return "\n".join(lines)


_RENDERERS = {
    "default": _fmt_default,
    "chatgpt": _fmt_chatgpt,
    "claude":  _fmt_claude,
    "gemini":  _fmt_gemini,
}


# ── Public API ─────────────────────────────────────────────────────────────────

def get_context_string(memory_limit: int = 10, fmt: str = "default",
                       include_decisions: bool = False) -> str:
    """
    Prompt-ready context string. Prepend to any AI system prompt.

    fmt: "default" | "chatgpt" | "claude" | "gemini"
    include_decisions: append TODAY'S BUSINESS ACTIONS below context string
    """
    ctx    = build_context(memory_limit=memory_limit)
    result = _RENDERERS.get(fmt, _fmt_default)(ctx)

    if include_decisions:
        from decision_engine.decision_engine import generate_actions
        result = result + "\n\n" + generate_actions(context_string=result,
                                                    memory=ctx["memory"])
    return result


# ── CLI ────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    args = sys.argv[1:]

    fmt = "default"
    for flag in ("--chatgpt", "--claude", "--gemini"):
        if flag in args:
            fmt = flag.lstrip("-")
            break

    if "--json" in args:
        print(json.dumps(build_context(), indent=2, default=str))
    elif "--decisions" in args:
        print(get_context_string(fmt=fmt, include_decisions=True))
    elif "--prompt" in args or any(f in args for f in ("--chatgpt", "--claude", "--gemini")):
        print(get_context_string(fmt=fmt))
    else:
        ctx     = build_context()
        state   = ctx["context"]
        s       = state.get("state", {})
        memory  = ctx["memory"]
        clients = state.get("clients", [])
        at_risk = [c for c in clients if c.get("health") == "at_risk"]

        print(f"\n  SMB Context Pack — {state.get('company') or '(company not set)'}")
        print(f"  {'═' * 50}")
        print(f"  Company       : {state.get('company') or '(not set)'}")
        print(f"  Focus         : {state.get('focus') or '(not set)'}")
        print(f"  Revenue       : {s.get('revenue','').upper()}")
        print(f"  Operations    : {s.get('operations','').upper()}")
        print(f"  Relationships : {s.get('relationships','').upper()}")
        print(f"  Clients       : {len(clients)} active / {len(at_risk)} at risk")
        print(f"  Tone          : {state.get('tone','')}")
        if state.get("top_priorities"):
            print(f"\n  Priorities:")
            for i, p in enumerate(state["top_priorities"], 1):
                print(f"    {i}. {p}")
        if state.get("risks"):
            print(f"\n  Risks:")
            for r in state["risks"]:
                print(f"    - {r}")
        print(f"\n  Memory: {len(memory)} entries")
        if memory:
            for e in memory[:3]:
                print(f"    [{e.get('entity','?')}] {e.get('content','')[:70]}")
        print(f"\n  get_context_string()        — default")
        print(f"  get_context_string(fmt=...) — chatgpt / claude / gemini")
