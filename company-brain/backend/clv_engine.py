"""
CLV Engine
──────────
Calculates Customer Lifetime Value from closed_won deals.
Updates contacts.clv_score and contacts.clv_tier in Postgres.
"""
from datetime import date
from typing import Any
import anthropic
import database as db
from config import settings


def calculate_clv(contact_id: str) -> dict[str, Any]:
    """
    CLV = Avg Deal × Frequency/yr × 3-year projection.
    Simple revenue-based model (good enough for MVP).
    """
    deals = db.fetchall(
        """
        SELECT amount, close_date FROM deals
        WHERE contact_id = %s AND stage = 'closed_won'
        ORDER BY close_date ASC
        """,
        (contact_id,),
    )

    if not deals:
        return {"clv": 0.0, "tier": "NONE", "deal_count": 0}

    total_revenue = sum(float(d["amount"]) for d in deals)
    deal_count = len(deals)
    avg_deal = total_revenue / deal_count

    dates = [d["close_date"] for d in deals]
    lifespan_days = max(1, (dates[-1] - dates[0]).days)
    lifespan_years = max(1.0, lifespan_days / 365)
    frequency_per_year = deal_count / lifespan_years

    projected_clv = avg_deal * frequency_per_year * 3

    tier = (
        "PLATINUM" if projected_clv > 50_000 else
        "GOLD"     if projected_clv > 15_000 else
        "SILVER"   if projected_clv > 5_000  else
        "STANDARD"
    )

    return {
        "contact_id": contact_id,
        "total_revenue": round(total_revenue, 2),
        "deal_count": deal_count,
        "avg_deal_size": round(avg_deal, 2),
        "projected_3yr_clv": round(projected_clv, 2),
        "tier": tier,
    }


def refresh_all_clv() -> int:
    """Recalculate CLV for every contact and persist to DB. Returns updated count."""
    contacts = db.fetchall("SELECT id FROM contacts")
    updated = 0

    for c in contacts:
        result = calculate_clv(c["id"])
        db.execute(
            "UPDATE contacts SET clv_score=%s, clv_tier=%s WHERE id=%s",
            (result["projected_3yr_clv"], result["tier"], c["id"]),
        )
        updated += 1

    return updated


def get_top_clients(pct: float = 0.20) -> list[dict]:
    """Return the top `pct`% clients by projected CLV."""
    all_contacts = db.fetchall(
        "SELECT * FROM contacts ORDER BY clv_score DESC"
    )
    cutoff = max(1, int(len(all_contacts) * pct))
    return all_contacts[:cutoff]


def suggest_nurture_action(contact: dict[str, Any]) -> str:
    """Use Claude to suggest one specific follow-up action for a high-value client."""
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    prompt = f"""
High-value client profile:
- Name: {contact.get("name", "Unknown")}
- Company: {contact.get("company", "Unknown")}
- Tier: {contact.get("clv_tier", "GOLD")}
- Total revenue: ${contact.get("clv_score", 0):,.0f} (projected 3yr CLV)
- Industry: {contact.get("industry", "Unknown")}

Suggest ONE specific, actionable follow-up for this client (2 sentences max).
Be specific to their industry and tier. Do NOT suggest vague "check-ins".
Example of good output: "Send the Q2 benchmark report for the SaaS sector —
CFOs in this space respond well to peer comparison data before renewal discussions."
""".strip()

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=150,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text.strip()
