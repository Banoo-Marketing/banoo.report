#!/usr/bin/env python3
"""
Company Brain — Email Analyzer
───────────────────────────────
Usage:
  python main.py fetch       # Pull emails from Gmail into local cache
  python main.py process     # Categorize cached emails with Claude
  python main.py report      # Generate HTML/JSON/Markdown reports
  python main.py all         # Run all three steps end-to-end
  python main.py status      # Show cache stats
  python main.py demo        # Process a small sample (50 emails) as a demo
"""
import sys
import json
from pathlib import Path

import config
import cache


def cmd_status():
    cache.init()
    st = cache.stats()
    print("\n=== Email Analyzer Cache Status ===")
    print(f"  Total emails fetched : {st['total']:,}")
    print(f"  Emails processed     : {st['processed']:,}")
    print(f"  Date range           : {st['oldest']} → {st['newest']}")
    print(f"  Cache location       : {config.CACHE_DB}")
    print(f"  Reports directory    : {config.REPORTS_DIR}")
    remaining = st["total"] - st["processed"]
    if remaining:
        print(f"\n  {remaining:,} emails still need processing (run: python main.py process)")
    else:
        print(f"\n  All emails processed. Run: python main.py report")


def cmd_fetch(max_emails: int = 0, lookback_days: int = None):
    import gmail_fetcher
    print("\n=== Step 1: Fetch Emails from Gmail ===")
    result = gmail_fetcher.fetch_emails(
        max_emails=max_emails,
        lookback_days=lookback_days,
        verbose=True,
    )
    print(f"\nResult: {result}")


def cmd_process(max_to_process: int = None):
    import processor
    print("\n=== Step 2: Analyse Emails with Claude ===")
    result = processor.process_emails(
        max_to_process=max_to_process,
        verbose=True,
    )
    print(f"\nResult: {result}")


def cmd_report():
    import report_generator
    print("\n=== Step 3: Generate Report ===")
    data = report_generator.build_report_data()

    if "error" in data:
        print(f"Error: {data['error']}")
        return

    json_path = report_generator.write_json_report(data)
    print(f"  JSON report  → {json_path}")

    md_path = report_generator.write_markdown_report(data)
    if md_path:
        print(f"  Markdown     → {md_path}")

    html_path = report_generator.write_html_report(data)
    if html_path:
        print(f"  HTML report  → {html_path}")

    # Print quick summary to console
    print("\n" + "=" * 60)
    print("QUICK SUMMARY")
    print("=" * 60)
    st = data["stats"]
    print(f"  Analysed    : {st['emails_processed']:,} emails")
    print(f"  Date range  : {st['date_range']}")
    print()
    print("  CATEGORIES:")
    for key, info in data["category_summary"].items():
        if info["count"] > 0:
            print(f"    {info['label'][:40]:40} {info['count']:>5}")
    print()
    print("  TOP THEMES:")
    for t in data["theme_analysis"][:8]:
        print(f"    {t['theme'][:40]:40} ×{t['count']}")
    print()
    print(f"  Reconnect contacts   : {len(data['contact_recommendations']['reconnect'])}")
    print(f"  Nurture prospects    : {len(data['contact_recommendations']['nurture_for_conversion'])}")
    print(f"  Banoo leads          : {len(data['contact_recommendations']['banoo_related'])}")
    print()
    print(f"  Open the HTML report for the full interactive view:")
    if html_path:
        print(f"  {html_path}")


def cmd_all(max_emails: int = 0):
    cmd_fetch(max_emails=max_emails)
    cmd_process()
    cmd_report()


def cmd_demo():
    """Fetch 50 emails, process them, generate report — quick demo."""
    print("\n=== DEMO MODE (50 emails) ===")
    print("This fetches your 50 most recent emails, categorizes them with Claude,")
    print("and generates a full report. Full 10-year run: python main.py all\n")
    cmd_fetch(max_emails=50, lookback_days=365)
    cmd_process(max_to_process=50)
    cmd_report()


def main():
    args = sys.argv[1:]

    if not args or args[0] in ("-h", "--help", "help"):
        print(__doc__)
        return

    cmd = args[0]

    # Validate config
    if cmd not in ("status",) and not config.ANTHROPIC_API_KEY:
        print("ERROR: ANTHROPIC_API_KEY not set. Add it to .env")
        sys.exit(1)
    if cmd not in ("status", "process", "report") and not config.GOOGLE_CLIENT_ID:
        print("ERROR: GOOGLE_CLIENT_ID not set. Add it to .env")
        sys.exit(1)

    cache.init()

    if cmd == "status":
        cmd_status()
    elif cmd == "fetch":
        max_emails = int(args[1]) if len(args) > 1 else 0
        lookback = int(args[2]) if len(args) > 2 else None
        cmd_fetch(max_emails=max_emails, lookback_days=lookback)
    elif cmd == "process":
        max_p = int(args[1]) if len(args) > 1 else None
        cmd_process(max_to_process=max_p)
    elif cmd == "report":
        cmd_report()
    elif cmd == "all":
        max_emails = int(args[1]) if len(args) > 1 else 0
        cmd_all(max_emails=max_emails)
    elif cmd == "demo":
        cmd_demo()
    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
