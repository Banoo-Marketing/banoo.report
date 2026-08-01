import re
import warnings

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

AW_ID_RE = re.compile(r"AW-\d{6,}")
GTM_ID_RE = re.compile(r"GTM-[A-Z0-9]{4,8}")

AD_SIGNALS_RE = [
    re.compile(r"googleadservices\.com"),
    re.compile(r"googlesyndication\.com"),
    re.compile(r"/pagead/"),
    re.compile(r"doubleclick\.net/pagead"),
    re.compile(r"google_ads_conversion"),
]


def _fetch(url, timeout=15):
    resp = requests.get(url, headers=HEADERS, timeout=timeout, verify=False)
    return resp.text


def detect_google_ads(url, timeout=15):
    aw_ids = set()
    signals = set()
    error = None
    gtm_ids = set()

    try:
        html = _fetch(url, timeout=timeout)
    except Exception as e:
        return {"ads_detected": False, "signals": [], "aw_ids": [], "error": str(e)}

    # Look for AW- IDs and signal patterns directly in the HTML
    for m in AW_ID_RE.findall(html):
        aw_ids.add(m)
    for pattern in AD_SIGNALS_RE:
        if pattern.search(html):
            signals.add(pattern.pattern)

    # Extract GTM container IDs and fetch each container to find Google Ads tags
    for gtm_id in GTM_ID_RE.findall(html):
        gtm_ids.add(gtm_id)

    for gtm_id in gtm_ids:
        try:
            container_url = f"https://www.googletagmanager.com/gtm.js?id={gtm_id}"
            container_js = _fetch(container_url, timeout=timeout)
            for m in AW_ID_RE.findall(container_js):
                aw_ids.add(m)
            for pattern in AD_SIGNALS_RE:
                if pattern.search(container_js):
                    signals.add(pattern.pattern)
        except Exception:
            pass

    return {
        "ads_detected": len(aw_ids) > 0 or len(signals) > 0,
        "signals": sorted(signals),
        "aw_ids": sorted(aw_ids),
        "gtm_ids": sorted(gtm_ids),
        "error": error,
    }
