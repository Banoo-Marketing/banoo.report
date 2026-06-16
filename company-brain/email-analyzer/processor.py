"""
processor.py — Uses Claude to understand, categorize, and extract insights
               from emails in batches. Results are cached in SQLite.

Batches 20 emails per Claude call to minimize cost.
Uses claude-sonnet-4-6 with prompt caching on the system prompt.
"""
import json
import time
import anthropic
import cache
import config

_client = None

SYSTEM_PROMPT = f"""You are an expert email analyst. You will receive batches of emails and return structured JSON analysis.

For each email, classify it into one or more of these categories:
{json.dumps(config.CATEGORIES, indent=2)}

Category rules:
- "job_hiring": emails about job applications, interviews, recruiting, hiring, candidates, HR
- "business_ideas": pitches, brainstorming, startup concepts, innovation proposals
- "real_estate": property buying/selling/renting, deals, listings, agents, mortgages
- "family": emails from or about family members (parents, siblings, children, spouse, relatives)
- "key_people": important professional contacts, CEOs, investors, mentors, partners worth keeping close
- "reconnect": people the user hasn't heard from in a while, lost connections, "let's catch up" emails
- "business_deals": B2B negotiations, contracts, partnerships, sales, proposals, NDAs
- "friends": personal (non-family) social emails, casual conversation
- "marketing_leadgen": marketing strategies, lead generation tactics, advertising, SEO, campaigns
- "banoo_clients": any mention of "Banoo", digital marketing services, web design/development clients
- "business_owner_nurture": emails from business owners who could benefit from digital marketing — look for signals: they run a business, mention website/social/ads needs, or could be a Banoo prospect

You must return ONLY valid JSON in this exact format:
{{
  "results": [
    {{
      "gmail_id": "...",
      "categories": ["category_key1", "category_key2"],
      "summary": "One sentence summary of this email.",
      "sentiment": "positive|neutral|negative",
      "action_items": ["action 1", "action 2"],
      "key_people": [{{"name": "...", "email": "...", "role": "..."}}],
      "themes": ["theme1", "theme2"],
      "reconnect_reason": "Why you should reconnect (only if reconnect category)",
      "nurture_notes": "Why they need digital marketing nurturing (only if business_owner_nurture)"
    }}
  ]
}}"""


def _get_client():
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    return _client


def _process_batch(emails: list[dict]) -> list[dict]:
    """Send a batch of emails to Claude and return structured results."""
    batch_input = []
    for e in emails:
        batch_input.append({
            "gmail_id": e["gmail_id"],
            "from": e.get("sender", ""),
            "subject": e.get("subject", ""),
            "date": e.get("date_str", ""),
            "body": (e.get("body_text") or e.get("snippet", ""))[:800],
        })

    user_content = f"Analyze these {len(emails)} emails and return JSON:\n\n{json.dumps(batch_input, indent=2)}"

    for attempt in range(4):
        try:
            response = _get_client().messages.create(
                model="claude-sonnet-4-6",
                max_tokens=4096,
                system=[
                    {
                        "type": "text",
                        "text": SYSTEM_PROMPT,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                messages=[{"role": "user", "content": user_content}],
            )

            text = response.content[0].text.strip()
            # Strip markdown code fences if present
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
                text = text.rsplit("```", 1)[0]

            parsed = json.loads(text.strip())
            return parsed.get("results", [])

        except json.JSONDecodeError as e:
            print(f"\n  JSON parse error (attempt {attempt+1}): {e}")
            if attempt == 3:
                # Return empty results for this batch rather than crashing
                return [{"gmail_id": e["gmail_id"], "categories": [], "summary": "", "sentiment": "neutral",
                          "action_items": [], "key_people": [], "themes": []} for e in emails]
            time.sleep(2 ** attempt)
        except Exception as e:
            if "overloaded" in str(e).lower() or "529" in str(e):
                wait = 30 * (attempt + 1)
                print(f"\n  Claude overloaded. Waiting {wait}s...")
                time.sleep(wait)
            else:
                print(f"\n  Error in batch: {e}")
                time.sleep(2 ** attempt)

    return []


def process_emails(
    batch_size: int = None,
    max_to_process: int = None,
    verbose: bool = True,
) -> dict:
    """
    Process all unprocessed emails from cache using Claude.
    Results are saved back to the cache.

    Returns: {"processed": N, "skipped": N}
    """
    if batch_size is None:
        batch_size = config.CLAUDE_BATCH_SIZE
    if max_to_process is None:
        max_to_process = config.MAX_EMAILS_PER_RUN or 999999

    unprocessed = cache.get_unprocessed(limit=max_to_process)

    if not unprocessed:
        if verbose:
            print("All emails already processed.")
        return {"processed": 0, "skipped": 0}

    if verbose:
        print(f"Processing {len(unprocessed)} emails with Claude (batch size={batch_size})...")

    processed = 0
    errors = 0

    for i in range(0, len(unprocessed), batch_size):
        batch = unprocessed[i : i + batch_size]
        batch_num = i // batch_size + 1
        total_batches = (len(unprocessed) + batch_size - 1) // batch_size

        if verbose:
            pct = int(processed / len(unprocessed) * 100) if unprocessed else 0
            print(f"  Batch {batch_num}/{total_batches} ({pct}% done)...", end="\r")

        try:
            results = _process_batch(batch)
            for result in results:
                cache.save_processing(result)
                processed += 1
        except Exception as e:
            print(f"\n  Batch {batch_num} failed: {e}")
            errors += 1

        # Rate limiting: pause between batches
        time.sleep(0.5)

    if verbose:
        print(f"\nProcessed {processed} emails. Errors: {errors}")

    return {"processed": processed, "errors": errors}
