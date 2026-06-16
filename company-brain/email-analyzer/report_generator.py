"""
report_generator.py — Generates JSON, Markdown, and HTML reports
                       from the processed email cache.
"""
import json
import re
from collections import defaultdict, Counter
from datetime import datetime, timezone
from pathlib import Path
import cache
import config


def _parse_json_field(value, default=None):
    if default is None:
        default = []
    if isinstance(value, (list, dict)):
        return value
    if not value:
        return default
    try:
        return json.loads(value)
    except Exception:
        return default


def build_report_data() -> dict:
    """Read all processed emails from cache and build the report data structure."""
    emails = cache.get_all_emails()
    processed = [e for e in emails if e.get("categories")]

    if not processed:
        return {"error": "No processed emails found. Run `python main.py process` first."}

    # ── Category buckets ──────────────────────────────────────────────────────
    category_buckets = defaultdict(list)
    all_themes = []
    all_key_people = {}   # email → {name, email, role, count}
    reconnect_list = []
    nurture_list = []
    banoo_list = []
    yearly_categories = defaultdict(lambda: defaultdict(int))

    for e in processed:
        cats = _parse_json_field(e.get("categories"), [])
        themes = _parse_json_field(e.get("themes"), [])
        key_people = _parse_json_field(e.get("key_people"), [])
        action_items = _parse_json_field(e.get("action_items"), [])

        year = None
        if e.get("date_ts"):
            try:
                year = datetime.fromtimestamp(e["date_ts"], tz=timezone.utc).year
            except Exception:
                pass

        all_themes.extend(themes)

        for person in key_people:
            addr = person.get("email", "").lower().strip()
            if addr and "@" in addr:
                if addr not in all_key_people:
                    all_key_people[addr] = {**person, "email": addr, "count": 0, "categories": set()}
                all_key_people[addr]["count"] += 1
                all_key_people[addr]["categories"].update(cats)

        for cat in cats:
            item = {
                "gmail_id": e["gmail_id"],
                "from": e.get("sender", ""),
                "subject": e.get("subject", ""),
                "date": e.get("date_str", "")[:10],
                "summary": e.get("summary", ""),
                "sentiment": e.get("sentiment", "neutral"),
                "action_items": action_items,
            }
            category_buckets[cat].append(item)
            if year:
                yearly_categories[year][cat] += 1

        # Special collections
        if "reconnect" in cats:
            reconnect_list.append({
                "from": e.get("sender", ""),
                "subject": e.get("subject", ""),
                "date": e.get("date_str", "")[:10],
                "summary": e.get("summary", ""),
                "reason": e.get("reconnect_reason") or "Lost touch — worth reconnecting",
                "key_people": key_people,
            })

        if "business_owner_nurture" in cats:
            nurture_list.append({
                "from": e.get("sender", ""),
                "subject": e.get("subject", ""),
                "date": e.get("date_str", "")[:10],
                "summary": e.get("summary", ""),
                "notes": e.get("nurture_notes") or "Business owner — potential Banoo prospect",
                "key_people": key_people,
            })

        if "banoo_clients" in cats:
            banoo_list.append({
                "from": e.get("sender", ""),
                "subject": e.get("subject", ""),
                "date": e.get("date_str", "")[:10],
                "summary": e.get("summary", ""),
                "key_people": key_people,
            })

    # ── Theme analysis ─────────────────────────────────────────────────────────
    theme_counter = Counter(t.lower().strip() for t in all_themes if t)
    top_themes = [{"theme": t, "count": c} for t, c in theme_counter.most_common(30)]

    # ── Category summary ───────────────────────────────────────────────────────
    category_summary = {}
    for key, label in config.CATEGORIES.items():
        items = category_buckets.get(key, [])
        # Sort by date desc, take top 5 examples
        items_sorted = sorted(items, key=lambda x: x.get("date", ""), reverse=True)
        category_summary[key] = {
            "label": label,
            "count": len(items),
            "top_examples": items_sorted[:5],
        }

    # ── Key people ─────────────────────────────────────────────────────────────
    key_people_list = sorted(
        [
            {**p, "categories": sorted(p["categories"])}
            for p in all_key_people.values()
        ],
        key=lambda x: x["count"],
        reverse=True,
    )[:50]

    # ── Timeline ───────────────────────────────────────────────────────────────
    timeline = {}
    for year in sorted(yearly_categories.keys()):
        timeline[str(year)] = dict(yearly_categories[year])

    # ── Stats ─────────────────────────────────────────────────────────────────
    st = cache.stats()

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "stats": {
            "total_emails_cached": st["total"],
            "emails_processed": st["processed"],
            "date_range": f"{st['oldest']} → {st['newest']}",
        },
        "category_summary": category_summary,
        "theme_analysis": top_themes,
        "contact_recommendations": {
            "reconnect": sorted(reconnect_list, key=lambda x: x.get("date", ""), reverse=True)[:20],
            "nurture_for_conversion": sorted(nurture_list, key=lambda x: x.get("date", ""), reverse=True)[:20],
            "banoo_related": sorted(banoo_list, key=lambda x: x.get("date", ""), reverse=True)[:20],
            "key_people": key_people_list,
        },
        "timeline_insights": timeline,
    }


def write_json_report(data: dict, out_dir: Path = None) -> Path:
    if out_dir is None:
        out_dir = config.REPORTS_DIR
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = out_dir / f"report_{ts}.json"
    path.write_text(json.dumps(data, indent=2, default=str))
    return path


def write_markdown_report(data: dict, out_dir: Path = None) -> Path:
    if out_dir is None:
        out_dir = config.REPORTS_DIR

    if "error" in data:
        return None

    stats = data["stats"]
    cats = data["category_summary"]
    themes = data["theme_analysis"]
    contacts = data["contact_recommendations"]
    timeline = data["timeline_insights"]

    lines = [
        "# Company Brain — Email Intelligence Report",
        f"*Generated: {data['generated_at']}*",
        "",
        "---",
        "",
        "## Overview",
        f"- **Emails analysed:** {stats['emails_processed']:,} (of {stats['total_emails_cached']:,} fetched)",
        f"- **Date range:** {stats['date_range']}",
        "",
        "---",
        "",
        "## Category Summary",
        "",
    ]

    for key, info in cats.items():
        if info["count"] == 0:
            continue
        lines.append(f"### {info['label']} ({info['count']} emails)")
        for ex in info["top_examples"][:3]:
            lines.append(f"- **{ex['date']}** | {ex['from'][:40]} | _{ex['subject'][:60]}_")
            if ex.get("summary"):
                lines.append(f"  > {ex['summary']}")
        lines.append("")

    lines += [
        "---",
        "",
        "## Theme Analysis (Top 20)",
        "",
    ]
    for t in themes[:20]:
        lines.append(f"- **{t['theme']}** ({t['count']} mentions)")

    lines += [
        "",
        "---",
        "",
        "## Who Should You Reconnect With?",
        "",
    ]
    for r in contacts["reconnect"][:10]:
        lines.append(f"### {r['from']}")
        lines.append(f"- Last email: {r['date']} — _{r['subject']}_")
        lines.append(f"- **Why reconnect:** {r['reason']}")
        lines.append("")

    lines += [
        "---",
        "",
        "## Business Owners — Nurture for Conversion",
        "",
    ]
    for n in contacts["nurture_for_conversion"][:10]:
        lines.append(f"### {n['from']}")
        lines.append(f"- Email: {n['date']} — _{n['subject']}_")
        lines.append(f"- **Notes:** {n['notes']}")
        lines.append("")

    lines += [
        "---",
        "",
        "## Banoo-Related Clients & Leads",
        "",
    ]
    for b in contacts["banoo_related"][:10]:
        lines.append(f"- **{b['date']}** | {b['from']} | _{b['subject']}_")
        if b.get("summary"):
            lines.append(f"  > {b['summary']}")

    lines += [
        "",
        "---",
        "",
        "## Timeline Insights",
        "",
        "| Year | " + " | ".join(config.CATEGORIES.keys())[:60] + " |",
        "|------|" + "--------|" * 5,
    ]
    for year, year_data in sorted(timeline.items()):
        row = f"| {year} |"
        for key in list(config.CATEGORIES.keys())[:5]:
            row += f" {year_data.get(key, 0)} |"
        lines.append(row)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = out_dir / f"report_{ts}.md"
    path.write_text("\n".join(lines))
    return path


def write_html_report(data: dict, out_dir: Path = None) -> Path:
    if out_dir is None:
        out_dir = config.REPORTS_DIR

    tmpl_path = Path(__file__).parent / "templates" / "report.html"
    if not tmpl_path.exists():
        return write_markdown_report(data, out_dir)

    try:
        from jinja2 import Template
        tmpl = Template(tmpl_path.read_text())
        html = tmpl.render(**data, categories=config.CATEGORIES)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = out_dir / f"report_{ts}.html"
        path.write_text(html)
        return path
    except ImportError:
        print("jinja2 not installed — falling back to Markdown report.")
        return write_markdown_report(data, out_dir)
