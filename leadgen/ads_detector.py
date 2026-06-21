import re

from playwright.sync_api import sync_playwright

AD_SIGNAL_PATTERNS = [
    "googleadservices.com",
    "googlesyndication.com",
    "/pagead/",
    "doubleclick.net/pagead",
    "google_ads_conversion",
    "googletagmanager.com/gtag/js?id=AW-",
]

AW_ID_RE = re.compile(r"AW-\d{6,}")


def detect_google_ads(url, timeout_ms=25000):
    hits = set()
    aw_ids = set()
    error = None
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(args=["--ignore-certificate-errors"])
            page = browser.new_page(ignore_https_errors=True)

            def on_request(request):
                req_url = request.url
                for pattern in AD_SIGNAL_PATTERNS:
                    if pattern in req_url:
                        hits.add(pattern)
                for m in AW_ID_RE.findall(req_url):
                    aw_ids.add(m)

            page.on("request", on_request)
            page.goto(url, timeout=timeout_ms, wait_until="domcontentloaded")
            page.wait_for_timeout(6000)
            try:
                page.mouse.wheel(0, 2000)
                page.wait_for_timeout(2000)
            except Exception:
                pass
            content = page.content()
            for m in AW_ID_RE.findall(content):
                aw_ids.add(m)
            browser.close()
    except Exception as e:
        error = str(e)
    return {
        "ads_detected": len(hits) > 0 or len(aw_ids) > 0,
        "signals": sorted(hits),
        "aw_ids": sorted(aw_ids),
        "error": error,
    }
