import csv
import os
import sys

from places import search_places, get_place_details
from ads_detector import detect_google_ads
from decision_maker import find_decision_maker

GOOGLE_MAPS_API_KEY = os.environ["GOOGLE_MAPS_API_KEY"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]


def run(query, industry, limit, out_path):
    places = search_places(query, GOOGLE_MAPS_API_KEY, max_results=limit)
    rows = []
    for p in places:
        details = get_place_details(p["place_id"], GOOGLE_MAPS_API_KEY)
        name = details.get("name", p.get("name"))
        website = details.get("website")
        phone = details.get("international_phone_number") or details.get("formatted_phone_number")
        address = details.get("formatted_address", p.get("formatted_address"))

        print(f"-> {name} | {website or 'NO WEBSITE'}", file=sys.stderr)

        if not website:
            rows.append({
                "industry": industry, "company": name, "address": address,
                "phone": phone, "website": "", "ads_detected": "",
                "decision_maker": "",
            })
            continue

        ads = detect_google_ads(website)
        decision_maker = ""
        if ads["ads_detected"]:
            try:
                dm = find_decision_maker(website, ANTHROPIC_API_KEY)
                decision_maker = f"{dm.get('name')} ({dm.get('title')})" if dm.get("name") else ""
            except Exception as e:
                decision_maker = f"ERROR: {e}"

        rows.append({
            "industry": industry,
            "company": name,
            "address": address,
            "phone": phone,
            "website": website,
            "ads_detected": ads["ads_detected"],
            "decision_maker": decision_maker,
        })

    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "industry", "company", "address", "phone", "website",
            "ads_detected", "decision_maker",
        ])
        writer.writeheader()
        writer.writerows(rows)

    return rows


if __name__ == "__main__":
    rows = run(
        query="immigration lawyer in Toronto",
        industry="Immigration Law",
        limit=8,
        out_path="poc_immigration_law_toronto.csv",
    )
    print(f"\n{len(rows)} businesses processed, {sum(1 for r in rows if r['ads_detected'] is True)} with Google Ads detected")
