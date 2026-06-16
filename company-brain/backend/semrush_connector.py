"""
SEMrush integration module for Company Brain.

Provides domain-level SEO data by calling the SEMrush API and surfacing the
results through helper functions used by the coaching engine and FastAPI routes.

All HTTP calls use httpx (lazy-imported inside functions to keep the module
lightweight and avoid import-time side-effects).
"""

import csv
import io
import json
import time

import database as db
from config import settings

# ── SEMrush API constants ─────────────────────────────────────────────────────

_BASE_URL = "https://api.semrush.com/"
_DATABASE = "us"


# ── Internal helpers ──────────────────────────────────────────────────────────

def _api_key() -> str:
    """Return the configured SEMrush API key, raising clearly if absent."""
    key = settings.semrush_api_key
    if not key:
        raise RuntimeError(
            "SEMRUSH_API_KEY is not set. Add it to your .env file."
        )
    return key


def _get(params: dict) -> str:
    """
    Make a GET request to the SEMrush API root with the given query params.
    Returns the raw response text.  Raises on HTTP errors.
    """
    import httpx  # lazy import

    params["key"] = _api_key()
    resp = httpx.get(_BASE_URL, params=params, timeout=30.0)
    resp.raise_for_status()
    return resp.text


def _parse_csv(text: str) -> list[dict]:
    """
    Parse SEMrush semicolon-delimited CSV response into a list of dicts.
    The first line is always the header row.
    Returns an empty list when the response body is empty or has no data rows.
    """
    text = text.strip()
    if not text:
        return []
    reader = csv.DictReader(io.StringIO(text), delimiter=";")
    return [row for row in reader]


# ── Public functions ──────────────────────────────────────────────────────────

def get_domain_overview(domain: str) -> dict:
    """
    Fetch the SEMrush domain_ranks overview for *domain*.

    Returns a dict with the keys:
        domain, rank, organic_keywords, organic_traffic,
        organic_cost, adwords_keywords

    On any failure (network error, bad API key, unknown domain, …) the error is
    caught and returned as {"domain": domain, "error": "<message>"} so callers
    can continue without crashing.
    """
    try:
        raw = _get(
            {
                "type": "domain_ranks",
                "export_columns": "Dn,Rk,Or,Ot,Oc,Ad",
                "domain": domain,
                "database": _DATABASE,
            }
        )
        rows = _parse_csv(raw)
        if not rows:
            return {"domain": domain, "error": "No data returned for domain"}

        row = rows[0]
        return {
            "domain": row.get("Domain", domain),
            "rank": _int(row.get("Rank")),
            "organic_keywords": _int(row.get("Organic Keywords")),
            "organic_traffic": _int(row.get("Organic Traffic")),
            "organic_cost": _float(row.get("Organic Cost")),
            "adwords_keywords": _int(row.get("Adwords Keywords")),
        }
    except Exception as e:
        return {"domain": domain, "error": str(e)}


def get_top_keywords(domain: str, limit: int = 10) -> list[dict]:
    """
    Fetch the top organic keywords for *domain* from SEMrush domain_organic.

    Returns a list of dicts, each containing:
        keyword, position, search_volume, cpc, competition, traffic

    On failure, returns a list with a single error dict so callers stay robust.
    """
    try:
        raw = _get(
            {
                "type": "domain_organic",
                "export_columns": "Ph,Po,Nq,Cp,Co,Tr,Td,Dn",
                "domain": domain,
                "database": _DATABASE,
                "display_limit": limit,
            }
        )
        rows = _parse_csv(raw)
        results = []
        for row in rows:
            results.append(
                {
                    "keyword": row.get("Keyword", ""),
                    "position": _int(row.get("Position")),
                    "search_volume": _int(row.get("Search Volume")),
                    "cpc": _float(row.get("CPC")),
                    "competition": _float(row.get("Competition")),
                    "traffic": _float(row.get("Traffic (%)")),
                }
            )
        return results
    except Exception as e:
        return [{"error": str(e)}]


def enrich_contact_domain(contact_id: str) -> dict:
    """
    Look up the contact by *contact_id*, derive their company domain from the
    stored email address, call get_domain_overview, and persist the result as
    JSON in contacts.raw_data (merged with any existing value).

    Returns the enrichment result dict (same shape as get_domain_overview).
    """
    contact = db.fetchone(
        "SELECT id, email, raw_data FROM contacts WHERE id = %s",
        (contact_id,),
    )
    if not contact:
        raise ValueError(f"Contact {contact_id!r} not found")

    email: str = contact.get("email") or ""
    if "@" not in email:
        raise ValueError(
            f"Contact {contact_id!r} has no valid email (got {email!r})"
        )

    domain = email.split("@", 1)[1].lower().strip()
    enrichment = get_domain_overview(domain)

    # Merge into existing raw_data
    existing_raw = contact.get("raw_data")
    if isinstance(existing_raw, str):
        try:
            existing = json.loads(existing_raw)
        except (json.JSONDecodeError, TypeError):
            existing = {}
    elif isinstance(existing_raw, dict):
        existing = existing_raw
    else:
        existing = {}

    existing["semrush"] = enrichment

    db.execute(
        "UPDATE contacts SET raw_data = %s WHERE id = %s",
        (json.dumps(existing), contact_id),
    )

    return enrichment


def enrich_all_contacts() -> list[dict]:
    """
    Run enrich_contact_domain for every contact in the database.

    Inserts a 0.5-second sleep between calls to respect SEMrush rate limits.
    Returns a list of enrichment result dicts, one per contact.
    """
    contacts = db.fetchall("SELECT id FROM contacts ORDER BY id")
    results = []
    for i, row in enumerate(contacts):
        try:
            result = enrich_contact_domain(str(row["id"]))
        except Exception as e:
            result = {"contact_id": str(row["id"]), "error": str(e)}
        results.append(result)
        if i < len(contacts) - 1:
            time.sleep(0.5)
    return results


def get_client_seo_health(contact_id: str) -> dict:
    """
    Return a combined SEO health snapshot for a contact: domain overview plus
    the top 5 keywords.  Suitable for inclusion in coaching engine context.

    Returns:
        {
            "contact_id": str,
            "domain": str,
            "overview": {...},      # from get_domain_overview
            "top_keywords": [...],  # from get_top_keywords(limit=5)
        }
    """
    contact = db.fetchone(
        "SELECT id, email FROM contacts WHERE id = %s",
        (contact_id,),
    )
    if not contact:
        raise ValueError(f"Contact {contact_id!r} not found")

    email: str = contact.get("email") or ""
    if "@" not in email:
        raise ValueError(
            f"Contact {contact_id!r} has no valid email (got {email!r})"
        )

    domain = email.split("@", 1)[1].lower().strip()
    overview = get_domain_overview(domain)
    keywords = get_top_keywords(domain, limit=5)

    return {
        "contact_id": contact_id,
        "domain": domain,
        "overview": overview,
        "top_keywords": keywords,
    }


# ── Type-coercion helpers ─────────────────────────────────────────────────────

def _int(value) -> int | None:
    """Safely convert a string to int; return None on failure."""
    if value is None:
        return None
    try:
        return int(str(value).replace(",", "").strip())
    except (ValueError, TypeError):
        return None


def _float(value) -> float | None:
    """Safely convert a string to float; return None on failure."""
    if value is None:
        return None
    try:
        return float(str(value).replace(",", "").strip())
    except (ValueError, TypeError):
        return None
