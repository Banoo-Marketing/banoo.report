"""
onboarding/setup.py — SMB Context Pack onboarding.

Standard : python onboarding/setup.py
Quick    : python onboarding/setup.py --quick
"""
import json
import sys
from pathlib import Path

_HERE = Path(__file__).parent
_ROOT = _HERE.parent
sys.path.insert(0, str(_ROOT))

_PROFILE = _ROOT / "company_profile"
_ENTRIES = _ROOT / "memory" / "entries"
_W = 54


# ── Safe imports ───────────────────────────────────────────────────────────────

try:
    from memory.log import log_entry
    from api.context import build_context, get_context_string
except Exception:
    print("\n  Cannot start — system files are missing.")
    print("  Make sure you are running from the smb_context_pack/ folder.")
    sys.exit(1)


# ── Load existing data ─────────────────────────────────────────────────────────

def _load_existing() -> dict:
    data = {}
    for fname in ("identity.json", "quick_facts.json"):
        p = _PROFILE / fname
        if not p.exists():
            continue
        try:
            for k, v in json.loads(p.read_text()).items():
                if isinstance(v, list):
                    if v:
                        data[k] = v
                elif v and str(v).strip():
                    data[k] = str(v).strip()
        except Exception:
            pass
    return data


def _count_memory() -> int:
    if not _ENTRIES.exists():
        return 0
    return len(list(_ENTRIES.glob("*.json")))


# ── Prompt helpers ─────────────────────────────────────────────────────────────

def _ask(label: str, hint: str = "", default: str = "") -> str:
    if hint:
        print(f"  ({hint})")
    val = input(f"  {label}: ").strip()
    if not val:
        val = input(f"  {label}: ").strip()
    return val or default


def _ask_prefill(label: str, current: str) -> str:
    print(f"  {label}")
    print(f"  Current: {current}")
    val = input("  Press ENTER to keep, or type new value: ").strip()
    return val if val else current


def _get_field(existing: dict, key: str, label: str, hint: str, quick: bool) -> str:
    current = existing.get(key, "")
    if current:
        if quick:
            return current
        print()
        return _ask_prefill(label, current)
    return _ask(label, hint=hint)


# ── Context preview ────────────────────────────────────────────────────────────

def _show_preview(data: dict) -> None:
    lines = []
    if data.get("company_name"):
        lines.append(f"  Company : {data['company_name']}")
    if data.get("main_offer"):
        lines.append(f"  Offer   : {data['main_offer']}")
    if data.get("current_focus"):
        lines.append(f"  Focus   : {data['current_focus']}")
    if not lines:
        return
    print(f"\n  {'─' * 40}")
    print("  CONTEXT PREVIEW")
    for line in lines:
        print(line)
    print(f"  {'─' * 40}")


# ── Write profile files ────────────────────────────────────────────────────────

def _write_profile(data: dict) -> None:
    _PROFILE.mkdir(exist_ok=True)

    identity = {
        "company_name":     data.get("company_name", ""),
        "what_we_do":       data.get("what_we_do", ""),
        "main_offer":       data.get("main_offer", ""),
        "target_customers": data.get("target_customers", ""),
        "tone":             data.get("tone", "direct"),
        "current_focus":    data.get("current_focus", ""),
    }
    (_PROFILE / "identity.json").write_text(json.dumps(identity, indent=2))

    (_PROFILE / "tone.json").write_text(json.dumps({
        "style": data.get("tone", "direct"),
        "avoid": ["corporate language", "long explanations"],
    }, indent=2))

    quick_facts = {
        "top_clients":         data.get("top_clients", []),
        "main_revenue_source": data.get("main_revenue_source", ""),
        "current_problem":     data.get("current_problem", ""),
        "biggest_opportunity": data.get("biggest_opportunity", ""),
        "current_focus":       data.get("current_focus", ""),
    }
    (_PROFILE / "quick_facts.json").write_text(json.dumps(quick_facts, indent=2))


# ── Final output ───────────────────────────────────────────────────────────────

def _show_final_output() -> None:
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
        print("\n  Context saved. Run: python onboarding/first_context.py")


# ── Main flow ──────────────────────────────────────────────────────────────────

def run(quick: bool = False) -> None:
    existing  = _load_existing()
    mem_count = _count_memory()

    # Greeting
    print()
    if existing.get("company_name"):
        print(f"  Welcome back — {existing['company_name']}")
        if mem_count:
            print(f"  {mem_count} memory {'entry' if mem_count == 1 else 'entries'} on file.")
        if quick:
            print("  Quick mode: auto-filling what we already know.\n")
        else:
            print()
    else:
        print("  Let's get your business AI-ready.")
        if quick:
            print("  Quick mode — just what we need.\n")
        else:
            print("  5 questions. Under 3 minutes.\n")

    data = dict(existing)

    try:
        # Company name — ask only if missing
        if not existing.get("company_name"):
            data["company_name"] = _ask(
                "Company name",
                hint="e.g. Acme Corp",
            )
            print()

        # Q1
        data["what_we_do"] = _get_field(
            existing, "what_we_do",
            "What does your business do?",
            "e.g. We help local businesses run Google Ads",
            quick,
        )

        # Q2
        data["main_offer"] = _get_field(
            existing, "main_offer",
            "What is your main offer?",
            "e.g. Monthly ads management at $1,500/month",
            quick,
        )

        # Q3
        data["target_customers"] = _get_field(
            existing, "target_customers",
            "Who are your customers?",
            "e.g. Local service businesses — plumbers, contractors",
            quick,
        )

        # Preview after first 3 questions
        if not quick:
            _show_preview(data)
            print()

        # Q4
        data["current_focus"] = _get_field(
            existing, "current_focus",
            "What matters most right now?",
            "e.g. Close 2 new clients this month",
            quick,
        )

        if quick:
            _show_preview(data)

        # Write profile
        _write_profile(data)

        # Q5: One recent event
        print("\n── RECENT EVENT ──\n")
        print("  Add one real event — a client update, a deal, an issue.")
        if quick and mem_count > 0:
            print(f"  (You already have {mem_count} {'entry' if mem_count == 1 else 'entries'} — press ENTER to skip)")

        entity = input("  Who or what is this about? ").strip()
        if not entity and quick and mem_count > 0:
            print("  Skipped.")
        else:
            if not entity:
                entity = input("  Who or what is this about? ").strip()
            if entity:
                content = input(f"  What happened with {entity}? ").strip()
                if not content:
                    content = input(f"  What happened? ").strip()
                if content:
                    try:
                        log_entry(entity, "manual", content, source="onboarding")
                    except Exception:
                        pass  # Memory entry failure never blocks onboarding

        print("\n  Building your context...\n")
        _show_final_output()

    except KeyboardInterrupt:
        print("\n\n  Paused. Run again to continue.")
        sys.exit(0)
    except Exception:
        print("\n  Something went wrong. Try running setup again.")
        sys.exit(1)


if __name__ == "__main__":
    run(quick="--quick" in sys.argv)
