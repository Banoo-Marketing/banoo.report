"""
Seed the database with realistic mock data for development/demo.
Run: python seed_data.py
"""
import random
from datetime import date, timedelta, datetime
import database as db

COMPANIES = [
    "Acme Corp", "Globex Inc", "Initech", "Umbrella Ltd",
    "Soylent Corp", "Vandalay Industries", "Prestige Worldwide",
    "Bluth Company", "Sterling Cooper", "Dunder Mifflin",
]

CONTACTS = [
    ("Alice Chen", "alice@acme.com", "Acme Corp", "SaaS"),
    ("Bob Martinez", "bob@globex.com", "Globex Inc", "Manufacturing"),
    ("Carol White", "carol@initech.com", "Initech", "Finance"),
    ("David Kim", "david@umbrella.com", "Umbrella Ltd", "Healthcare"),
    ("Eva Torres", "eva@soylent.com", "Soylent Corp", "FoodTech"),
    ("Frank Bell", "frank@vandalay.com", "Vandalay Industries", "Retail"),
    ("Grace Liu", "grace@prestige.com", "Prestige Worldwide", "Consulting"),
    ("Hiro Tanaka", "hiro@bluth.com", "Bluth Company", "Real Estate"),
    ("Iris Okonkwo", "iris@sterling.com", "Sterling Cooper", "Advertising"),
    ("James Park", "james@dunder.com", "Dunder Mifflin", "Office Supplies"),
]

REPS = [
    ("rep_001", "Sarah Johnson", "sarah@company.com"),
    ("rep_002", "Mike Thompson", "mike@company.com"),
    ("rep_003", "Lisa Wang", "lisa@company.com"),
]

STAGES = ["prospecting", "qualification", "proposal", "negotiation", "closed_won", "closed_lost"]

DEAL_NAMES = [
    "Enterprise License", "Pro Plan Annual", "Growth Suite",
    "Starter Pack", "Custom Integration", "Support Contract",
    "Platform Access", "Team Plan", "API License",
]


def seed():
    print("🌱 Seeding database...")

    # Reps
    for rep_id, name, email in REPS:
        db.execute(
            """INSERT INTO reps (id, name, email) VALUES (%s, %s, %s)
               ON CONFLICT (id) DO NOTHING""",
            (rep_id, name, email),
        )
    print(f"  ✓ {len(REPS)} reps")

    # Contacts
    contact_ids = []
    for i, (name, email, company, industry) in enumerate(CONTACTS):
        cid = f"contact_{i+1:03d}"
        contact_ids.append(cid)
        clv = round(random.uniform(1000, 120000), 2)
        tier = (
            "PLATINUM" if clv > 50000 else
            "GOLD" if clv > 15000 else
            "SILVER" if clv > 5000 else "STANDARD"
        )
        db.execute(
            """INSERT INTO contacts (id, name, email, company, clv_score, clv_tier, industry)
               VALUES (%s, %s, %s, %s, %s, %s, %s)
               ON CONFLICT (id) DO NOTHING""",
            (cid, name, email, company, clv, tier, industry),
        )
    print(f"  ✓ {len(CONTACTS)} contacts")

    # Deals  (some with renewals coming up soon for demo purposes)
    today = date.today()
    deal_count = 0
    for i in range(30):
        did = f"deal_{i+1:03d}"
        contact_idx = i % len(CONTACTS)
        cid = contact_ids[contact_idx]
        rep_id = random.choice([r[0] for r in REPS])
        stage = random.choice(STAGES)
        amount = round(random.uniform(2000, 80000), 2)
        close_date = today - timedelta(days=random.randint(30, 500))

        # Make some renewals imminent (for demo)
        if i < 8:
            days_away = random.choice([3, 5, 7, 10, 14, 20, 25, 28])
            renewal_date = today + timedelta(days=days_away)
            stage = "closed_won"
        else:
            renewal_date = close_date + timedelta(days=365) if stage == "closed_won" else None

        last_activity = datetime.utcnow() - timedelta(days=random.randint(1, 30))

        db.execute(
            """INSERT INTO deals
               (id, name, company, contact_id, owner_id, owner_name, amount, stage,
                close_date, renewal_date, last_activity_at, crm_source)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'mock')
               ON CONFLICT (id) DO NOTHING""",
            (
                did,
                f"{random.choice(DEAL_NAMES)} – {CONTACTS[contact_idx][2]}",
                CONTACTS[contact_idx][2],
                cid,
                rep_id,
                next(r[1] for r in REPS if r[0] == rep_id),
                amount,
                stage,
                close_date,
                renewal_date,
                last_activity,
            ),
        )
        deal_count += 1
    print(f"  ✓ {deal_count} deals (8 with imminent renewals)")

    # Sample knowledge chunks (no embeddings yet – seeded as plain text)
    chunks = [
        ("Sales Playbook v3", "sop",
         "When a deal enters negotiation stage, always send a ROI summary within 48 hours. "
         "Use the case study closest to the client's industry."),
        ("Sales Playbook v3", "sop",
         "For PLATINUM clients, escalate stalled deals to the VP of Sales after 5 business days "
         "of no activity. Never let a 6-figure renewal go cold."),
        ("Renewal Playbook", "sop",
         "Send first renewal outreach 30 days before expiry. Use first-name only, "
         "reference one specific win they had with the product, and include a one-click link to book a call."),
        ("Renewal Playbook", "sop",
         "If no response to 30-day email, send a 14-day reminder with a short video testimonial. "
         "If still no response at 7 days, escalate to account manager."),
        ("Email Templates", "email_template",
         "Subject: Quick check-in on [Product]\nHi [Name], just wanted to touch base "
         "ahead of your [renewal_date] renewal date..."),
        ("Refund Policy", "document",
         "Refunds are issued within 30 days of purchase for annual plans. Pro-rated refunds "
         "apply after 30 days. No refunds for monthly plans after 7 days."),
    ]
    for source_name, source_type, content in chunks:
        db.execute(
            """INSERT INTO knowledge_chunks (source_name, source_type, content)
               VALUES (%s, %s, %s)""",
            (source_name, source_type, content),
        )
    print(f"  ✓ {len(chunks)} knowledge chunks")

    print("\n✅ Seed complete! Run the API and visit http://localhost:3000")


if __name__ == "__main__":
    seed()
