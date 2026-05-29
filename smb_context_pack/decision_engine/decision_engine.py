"""
decision_engine/decision_engine.py

Converts SMB context into specific daily actions.

Usage:
    python decision_engine/decision_engine.py           # Context + actions
    python decision_engine/decision_engine.py --only    # Actions only
    python decision_engine/decision_engine.py --claude  # Claude-formatted context + actions
"""
import sys
from pathlib import Path
from typing import Optional

_HERE = Path(__file__).parent
_ROOT = _HERE.parent
sys.path.insert(0, str(_ROOT))

from api.context import build_context, get_context_string
from decision_engine.prompt_templates import DIVIDER, HEADER, LABELS, NO_CONTEXT


# ── Data helpers ───────────────────────────────────────────────────────────────

def _active(profile: dict) -> list:
    return profile.get("clients", {}).get("active", [])

def _leads(profile: dict) -> list:
    return profile.get("clients", {}).get("warm_leads", [])

def _on_hold(profile: dict) -> list:
    return [c for c in _active(profile) if "hold" in c.get("note", "").lower()]

def _at_risk(profile: dict) -> list:
    return [c for c in _active(profile) if c.get("health") == "at_risk"]

def _real_active(profile: dict) -> list:
    return [c for c in _active(profile)
            if c.get("health") == "ok" and "hold" not in c.get("note", "").lower()]


# ── Decision rules ─────────────────────────────────────────────────────────────

def _revenue_action(snapshot: dict, profile: dict, memory: list) -> str:
    leads      = _leads(profile)
    on_hold    = _on_hold(profile)
    rev_state  = snapshot.get("state", {}).get("revenue", "stable")

    # Proposal already sent → follow up first
    sent = [l for l in leads if "proposal sent" in l.get("status", "").lower()]
    if sent:
        l = sent[0]
        svcs = ", ".join(l.get("services_proposed", [])) or "the proposal"
        return (
            f"Follow up with {l['name']} — your {svcs} proposal is open with no response. "
            f"Send a 2-line email today: ask if they have questions and suggest a 15-min call to close."
        )

    # Other warm leads + revenue is weak → push them forward
    in_convo = [l for l in leads if l not in sent]
    if in_convo and rev_state == "weak":
        names = " and ".join(l["name"] for l in in_convo[:2])
        return (
            f"Send a next-step proposal to {names} today. "
            f"Revenue is weak — leads sitting in conversation don't close on their own."
        )

    # On-hold client → reactivation
    if on_hold:
        c = on_hold[0]
        return (
            f"Reach out to {c['name']} — check if their situation has resolved. "
            f"One short message reopens revenue with zero cold-start cost."
        )

    # Stable → find upsell
    real = _real_active(profile)
    if real:
        return (
            f"Identify one upsell channel {real[0]['name']} isn't running yet "
            f"and pitch it in your next check-in."
        )

    return "Contact your most recent warm prospect and propose a first call today."


def _risk_action(snapshot: dict, profile: dict, memory: list) -> str:
    at_risk = _at_risk(profile)
    real    = _real_active(profile)

    # At-risk client → call immediately
    if at_risk:
        c = at_risk[0]
        return (
            f"Call {c['name']} today — health is flagged at-risk. "
            f"Do not email. A direct call resets the relationship faster."
        )

    # Thin active base → proactive retention
    if len(real) <= 2:
        names = " and ".join(c["name"] for c in real[:2])
        return (
            f"Send a proactive performance update to {names} this week. "
            f"With only {len(real)} active retainer{'s' if len(real) != 1 else ''}, "
            f"one cancellation is a cashflow crisis — make them feel the value before they question it."
        )

    # Memory: silent signals
    _silent_words = {"silent", "no response", "no reply", "ghosted", "unresponsive"}
    silent = [e for e in memory[:10]
              if any(w in e.get("content", "").lower() for w in _silent_words)]
    if silent:
        entity = silent[0].get("entity", "client")
        return (
            f"Re-engage {entity} — memory shows silence. "
            f"Send one short direct message: no pitch, just a check-in."
        )

    return (
        "Confirm all active retainers received their deliverables on time this month "
        "before they have a reason to raise a concern."
    )


def _client_action(snapshot: dict, profile: dict, memory: list) -> str:
    real = _real_active(profile)

    if not real:
        return (
            "Define the monthly client experience — what does every Banoo client "
            "receive beyond ad management? Document it and deliver it."
        )

    # Detect missing high-value service → upsell
    for c in real:
        svcs  = [s.lower() for s in c.get("services", [])]
        name  = c["name"]
        paid  = any(x in s for s in svcs for x in ("ads", "ppc", "google", "meta"))
        seo   = any("seo" in s for s in svcs)
        email = any("email" in s for s in svcs)

        if paid and not email:
            return (
                f"Pitch email marketing to {name} — they're already spending on paid ads. "
                f"An email retainer stacks revenue without adding to their ad budget."
            )
        if paid and not seo:
            return (
                f"Propose SEO to {name} — they're paying for paid ads; "
                f"SEO is the natural complement and raises their LTV for Banoo."
            )
        if (seo or email) and not paid:
            return (
                f"Propose Google Ads to {name} — they're already buying organic and content services; "
                f"paid search closes the funnel and shows faster results."
            )

    # Default: send a value-add wins summary
    c = real[0]
    return (
        f"Send {c['name']} a short monthly wins summary — what worked, one insight, "
        f"one recommendation. Keeps the retainer sticky and justifies the fee."
    )


def _quick_win(snapshot: dict, profile: dict, memory: list) -> Optional[str]:
    leads = _leads(profile)
    team  = profile.get("team", {}).get("members", [])

    # Cold caller on team → direct task
    callers = [m["name"] for m in team if "cold" in m.get("role", "").lower()]
    unconverted = [l for l in leads if "proposal sent" not in l.get("status", "").lower()]
    if callers and unconverted:
        caller = callers[0]
        names  = " and ".join(l["name"] for l in unconverted[:2])
        return (
            f"Have {caller} call {names} today — use Fosters Law or 416-Flowers as social proof. "
            f"Same-vertical proof closes faster than any pitch."
        )

    # Positive memory signal → act on momentum
    _positive_words = {"jv", "interested", "signed", "closed", "renewal", "paid", "ready"}
    positive = [e for e in memory[:10]
                if any(w in e.get("content", "").lower() for w in _positive_words)]
    if positive:
        entity = positive[0].get("entity", "")
        if entity:
            return f"Act on {entity}'s recent positive signal today — momentum fades fast."

    # Default quick win
    real = _real_active(profile)
    if real:
        c = real[0]
        return (
            f"Ask {c['name']} for one referral — frame it as: "
            f"'Do you know anyone who'd benefit from what we do for you?' "
            f"One warm referral beats ten cold calls."
        )

    return None


# ── Output formatter ───────────────────────────────────────────────────────────

def _format(rev: str, risk: str, client: str, quick: Optional[str]) -> str:
    lines = [
        DIVIDER,
        HEADER,
        DIVIDER,
        "",
        LABELS["revenue"],
        f"→ {rev}",
        "",
        LABELS["risk"],
        f"→ {risk}",
        "",
        LABELS["client"],
        f"→ {client}",
    ]
    if quick:
        lines += ["", LABELS["quick"], f"→ {quick}"]
    lines.append(DIVIDER)
    return "\n".join(lines)


# ── Public API ─────────────────────────────────────────────────────────────────

def generate_actions(context_string: str = "", memory: list = None) -> str:
    """
    Returns TODAY'S BUSINESS ACTIONS block.

    context_string: output of get_context_string() — accepted but not parsed;
                    structured data is read directly from the context pack.
    memory:         optional list of parsed memory entries; defaults to recent entries.
    """
    try:
        ctx = build_context()
    except Exception:
        return NO_CONTEXT

    snapshot = ctx.get("context", {})
    profile  = ctx.get("company_profile", {})

    if not snapshot or not profile:
        return NO_CONTEXT

    if memory is None:
        memory = ctx.get("memory", [])

    try:
        rev    = _revenue_action(snapshot, profile, memory)
        risk   = _risk_action(snapshot, profile, memory)
        client = _client_action(snapshot, profile, memory)
        quick  = _quick_win(snapshot, profile, memory)
    except Exception:
        return NO_CONTEXT

    return _format(rev, risk, client, quick)


def get_full_output(fmt: str = "default") -> str:
    """Context string + decision actions — the complete daily briefing."""
    context_str = get_context_string(fmt=fmt)
    actions     = generate_actions(context_string=context_str)
    return context_str + "\n\n" + actions


# ── CLI ────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    args = sys.argv[1:]

    fmt = "default"
    for flag in ("--chatgpt", "--claude", "--gemini"):
        if flag in args:
            fmt = flag.lstrip("-")
            break

    if "--only" in args:
        print(generate_actions())
    else:
        print(get_full_output(fmt=fmt))
