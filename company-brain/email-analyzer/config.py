"""
config.py — loads settings from the shared .env or environment variables.
"""
import os
import json
from pathlib import Path

_HERE = Path(__file__).parent
_ENV_PATHS = [_HERE / ".env", _HERE.parent / ".env", _HERE.parent.parent / ".env"]


def _load_env():
    for path in _ENV_PATHS:
        if path.exists():
            for line in path.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    os.environ.setdefault(k.strip(), v.strip())


_load_env()

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")

# Token file (shared with Company Brain)
TOKEN_FILE = _HERE.parent / ".gmail_token.json"

# SQLite cache
CACHE_DB = _HERE / "email_cache.db"

# How many emails to send per Claude batch call (20 is a good balance)
CLAUDE_BATCH_SIZE = 20

# Max emails to process per run (set to 0 for unlimited)
MAX_EMAILS_PER_RUN = int(os.environ.get("MAX_EMAILS_PER_RUN", "500"))

# How far back to fetch (days)
LOOKBACK_DAYS = int(os.environ.get("LOOKBACK_DAYS", "3650"))  # ~10 years

# Report output directory
REPORTS_DIR = _HERE / "reports"
REPORTS_DIR.mkdir(exist_ok=True)

# The 11 categories (key → display label)
CATEGORIES = {
    "job_hiring":             "Job Related / Hiring Process",
    "business_ideas":         "Business Ideas",
    "real_estate":            "Real Estate Deal",
    "family":                 "Family Member",
    "key_people":             "Key People",
    "reconnect":              "Who Should I Be In Touch With",
    "business_deals":         "Business Deals",
    "friends":                "Friends",
    "marketing_leadgen":      "Marketing / Lead Gen",
    "banoo_clients":          "Clients for Banoo",
    "business_owner_nurture": "Business Owner – Nurture for Conversion",
}
