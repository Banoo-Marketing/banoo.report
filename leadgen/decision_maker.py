import json
import re

import requests
from bs4 import BeautifulSoup

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"


def _fetch_text(url, timeout=15):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    resp = requests.get(url, headers=headers, timeout=timeout, verify=False)
    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer"]):
        tag.decompose()
    return soup.get_text(separator=" ", strip=True)[:8000]


def find_decision_maker(url, anthropic_key):
    text = _fetch_text(url)
    resp = requests.post(
        ANTHROPIC_URL,
        headers={
            "x-api-key": anthropic_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": "claude-haiku-4-5-20251001",
            "max_tokens": 200,
            "messages": [{
                "role": "user",
                "content": (
                    "From the following business website text, identify the owner, founder, "
                    "managing partner, or principal decision-maker. Respond with strict JSON only, "
                    'no other text: {"name": "...", "title": "..."} or '
                    '{"name": null, "title": null} if not found.\n\n'
                    f"WEBSITE TEXT:\n{text}"
                ),
            }],
        },
        timeout=30,
    )
    data = resp.json()
    content = data["content"][0]["text"]
    match = re.search(r"\{.*\}", content, re.DOTALL)
    return json.loads(match.group(0)) if match else {"name": None, "title": None}
