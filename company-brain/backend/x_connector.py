"""
X (Twitter) Connector
─────────────────────
Posts tweets and drafts deal-win announcements via the X API v2.

Safety contract:
  - Tweets are NEVER posted automatically.
  - All tweets are queued to action_queue for human approval first.
  - execute_approved_tweet() raises PermissionError if the action is not APPROVED.
  - Every post is logged to audit_log.

OAuth 1.0a signing is built with stdlib only (hmac, hashlib, time, urllib, base64).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
import urllib.parse
import uuid
from typing import Any

import database as db
from config import settings

# ── X API v2 base URL ────────────────────────────────────────────────────────

_X_API_BASE = "https://api.twitter.com/2"
_TWEETS_URL = f"{_X_API_BASE}/tweets"


# ── OAuth 1.0a signer ────────────────────────────────────────────────────────

def _oauth1_header(method: str, url: str, params: dict | None = None) -> str:
    """
    Build an OAuth 1.0a Authorization header using HMAC-SHA1.

    Uses settings.x_api_key (consumer key), settings.x_api_key_secret (consumer secret),
    settings.x_access_token and settings.x_access_token_secret.

    Args:
        method: HTTP method in uppercase, e.g. "POST".
        url:    Full request URL, e.g. "https://api.twitter.com/2/tweets".
        params: Optional dict of *extra* query/body params to include in the
                signature base string (not typically needed for JSON body posts).

    Returns:
        The value for the Authorization header, beginning with "OAuth ".
    """
    oauth_params: dict[str, str] = {
        "oauth_consumer_key":     settings.x_api_key,
        "oauth_nonce":            uuid.uuid4().hex,
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp":        str(int(time.time())),
        "oauth_token":            settings.x_access_token,
        "oauth_version":          "1.0",
    }

    # Merge any additional params for the signature base (query params, form fields)
    all_params: dict[str, str] = {}
    if params:
        all_params.update({str(k): str(v) for k, v in params.items()})
    all_params.update(oauth_params)

    # Percent-encode keys and values, then sort lexicographically
    encoded_pairs = sorted(
        (urllib.parse.quote(k, safe=""), urllib.parse.quote(v, safe=""))
        for k, v in all_params.items()
    )
    param_string = "&".join(f"{k}={v}" for k, v in encoded_pairs)

    # Build the signature base string
    sig_base = "&".join([
        urllib.parse.quote(method.upper(), safe=""),
        urllib.parse.quote(url, safe=""),
        urllib.parse.quote(param_string, safe=""),
    ])

    # Build the signing key
    signing_key = "&".join([
        urllib.parse.quote(settings.x_api_key_secret, safe=""),
        urllib.parse.quote(settings.x_access_token_secret, safe=""),
    ])

    # HMAC-SHA1 → base64
    hashed = hmac.new(
        signing_key.encode("ascii"),
        sig_base.encode("ascii"),
        hashlib.sha1,
    )
    oauth_params["oauth_signature"] = base64.b64encode(hashed.digest()).decode("ascii")

    # Build the Authorization header value
    header_parts = ", ".join(
        f'{urllib.parse.quote(k, safe="")}="{urllib.parse.quote(v, safe="")}"'
        for k, v in sorted(oauth_params.items())
    )
    return f"OAuth {header_parts}"


# ── Core tweet post ──────────────────────────────────────────────────────────

def post_tweet(text: str) -> dict:
    """
    POST a tweet to https://api.twitter.com/2/tweets.

    Uses OAuth 1.0a for authentication (required for write operations).
    Never call this directly from business logic – go through
    execute_approved_tweet() so there is always a human-approval gate.

    Returns:
        {"tweet_id": "...", "text": "..."}
    """
    import httpx  # lazy – already installed

    body = {"text": text}
    auth_header = _oauth1_header("POST", _TWEETS_URL)

    headers = {
        "Authorization": auth_header,
        "Content-Type":  "application/json",
        "Accept":        "application/json",
    }

    response = httpx.post(_TWEETS_URL, headers=headers, json=body, timeout=15)

    if response.status_code not in (200, 201):
        raise RuntimeError(
            f"X API error {response.status_code}: {response.text}"
        )

    data = response.json()
    tweet_data = data.get("data", {})
    return {
        "tweet_id": tweet_data.get("id", ""),
        "text":     tweet_data.get("text", text),
    }


# ── Claude-powered tweet drafter ─────────────────────────────────────────────

def draft_deal_win_tweet(deal: dict, llm_client=None) -> str:
    """
    Use Claude to draft a celebratory tweet for a closed deal.

    Args:
        deal:       Deal dict (expects keys: company, amount, industry, name).
        llm_client: Optional pre-constructed anthropic.Anthropic client.
                    If None, one is created from settings.anthropic_api_key.

    Returns:
        Tweet text string (under 280 characters).
    """
    if llm_client is None:
        import anthropic  # lazy
        llm_client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    company  = deal.get("company", "a new client")
    industry = deal.get("industry", "their industry")
    deal_name = deal.get("name", "a new deal")

    # We deliberately avoid mentioning the exact dollar amount in the prompt to
    # keep the tweet confidentiality-safe, but we do pass the deal size bucket.
    amount = float(deal.get("amount") or 0)
    if amount >= 100_000:
        size_hint = "a major enterprise deal"
    elif amount >= 25_000:
        size_hint = "a significant deal"
    else:
        size_hint = "a new deal"

    prompt = f"""
Draft a single tweet celebrating a newly closed B2B sales deal.

Details:
- New client company: {company}
- Industry: {industry}
- Deal type: {deal_name}
- Deal size: {size_hint}

Rules:
- Under 280 characters (strict limit)
- Professional but genuinely exciting tone
- Do NOT mention specific dollar amounts or confidential figures
- Can include 1-2 relevant emojis
- No hashtag spam (at most 2 hashtags if they add value)
- Return ONLY the tweet text, nothing else – no quotes, no explanation

Example style: "Thrilled to welcome Acme Corp to the family! Excited to help the manufacturing sector unlock new efficiency gains. Big things ahead. 🚀"
""".strip()

    response = llm_client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=150,
        messages=[{"role": "user", "content": prompt}],
    )

    tweet_text = response.content[0].text.strip().strip('"').strip("'")

    # Hard-truncate to 280 chars as a safety net
    if len(tweet_text) > 280:
        tweet_text = tweet_text[:277] + "..."

    return tweet_text


# ── Queue for human approval ─────────────────────────────────────────────────

def queue_tweet_for_approval(text: str, context: dict, deal_id: str | None = None) -> int:
    """
    Insert a tweet into action_queue with status=PENDING_APPROVAL.

    Args:
        text:    Draft tweet text.
        context: Arbitrary context dict (e.g. deal info) stored in payload.
        deal_id: Optional deal ID to associate with the queue item.

    Returns:
        The action_queue row id.
    """
    payload = json.dumps({"text": text, "context": context})

    db.execute(
        """
        INSERT INTO action_queue
            (action_type, deal_id, payload, urgency, reason, status)
        VALUES
            ('post_tweet', %s, %s, 'LOW', 'Deal win tweet pending approval', 'PENDING_APPROVAL')
        """,
        (deal_id, payload),
    )

    row = db.fetchone(
        "SELECT id FROM action_queue WHERE deal_id=%s AND action_type='post_tweet' "
        "ORDER BY created_at DESC LIMIT 1",
        (deal_id,),
    )
    return row["id"] if row else -1


# ── Execute an approved tweet ─────────────────────────────────────────────────

def execute_approved_tweet(action_id: int) -> dict:
    """
    Post a tweet that a human has approved in action_queue.

    Safety gate: raises PermissionError if action is not in APPROVED status.
    Marks the action as EXECUTED and writes to audit_log on success.

    Returns:
        {"tweet_id": "...", "text": "...", "action_id": action_id}
    """
    # ── Safety gate ───────────────────────────────────────────────────────────
    action = db.fetchone(
        "SELECT * FROM action_queue WHERE id=%s AND status='APPROVED'",
        (action_id,),
    )
    if not action:
        raise PermissionError(
            f"Action {action_id} is not APPROVED. "
            "A human must approve this tweet before it can be posted."
        )

    # ── Extract tweet text from payload ───────────────────────────────────────
    payload = action["payload"]
    if isinstance(payload, str):
        payload = json.loads(payload)
    tweet_text = payload.get("text", "")

    if not tweet_text:
        raise ValueError(f"Action {action_id} has no tweet text in payload.")

    # ── Post the tweet ────────────────────────────────────────────────────────
    result = post_tweet(tweet_text)

    # ── Mark as EXECUTED ──────────────────────────────────────────────────────
    db.execute(
        "UPDATE action_queue SET status='EXECUTED', executed_at=NOW() WHERE id=%s",
        (action_id,),
    )

    # ── Audit log ─────────────────────────────────────────────────────────────
    db.execute(
        """
        INSERT INTO audit_log (action_type, deal_id, actor, details)
        VALUES ('tweet_posted', %s, 'system', %s)
        """,
        (
            action.get("deal_id"),
            json.dumps({
                "action_id": action_id,
                "tweet_id":  result["tweet_id"],
                "text":      tweet_text,
            }),
        ),
    )

    print(f"  Tweet posted → tweet_id={result['tweet_id']}")
    return {**result, "action_id": action_id}


# ── High-level orchestrator ───────────────────────────────────────────────────

def draft_and_queue_win_tweet(deal_id: str) -> dict:
    """
    Load a deal, draft a win tweet via Claude, and queue it for human approval.

    Only proceeds if deal.stage == 'closed_won'.

    Returns:
        {"action_id": int, "draft": str}

    Raises:
        ValueError if deal not found or not closed_won.
    """
    deal = db.fetchone(
        """
        SELECT d.*, c.name AS contact_name, c.email AS contact_email,
               c.clv_tier, c.industry
        FROM deals d
        LEFT JOIN contacts c ON c.id = d.contact_id
        WHERE d.id = %s
        """,
        (deal_id,),
    )
    if not deal:
        raise ValueError(f"Deal {deal_id} not found.")

    if deal.get("stage") != "closed_won":
        raise ValueError(
            f"Deal {deal_id} is in stage '{deal.get('stage')}', not 'closed_won'. "
            "Only closed deals get a win tweet."
        )

    tweet_text = draft_deal_win_tweet(deal)

    context: dict[str, Any] = {
        "deal_id":   deal_id,
        "deal_name": deal.get("name"),
        "company":   deal.get("company"),
        "industry":  deal.get("industry"),
        "stage":     deal.get("stage"),
        "amount":    float(deal.get("amount") or 0),
    }

    action_id = queue_tweet_for_approval(tweet_text, context, deal_id=deal_id)

    db.execute(
        """
        INSERT INTO audit_log (action_type, deal_id, actor, details)
        VALUES ('win_tweet_queued', %s, 'system', %s)
        """,
        (deal_id, json.dumps({"action_id": action_id, "draft": tweet_text})),
    )

    print(f"  Win tweet queued for deal {deal_id} → action #{action_id}")
    return {"action_id": action_id, "draft": tweet_text}
