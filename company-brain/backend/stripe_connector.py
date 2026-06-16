"""
Stripe Connector
────────────────
Integrates Stripe billing data with the Company Brain database.

Functions:
  get_stripe_client()          → configured stripe module (lazy import)
  sync_customers(limit)        → upsert Stripe customers into contacts table
  get_subscription_health()    → active subscriptions with payment flags
  detect_failed_payments()     → queue failed payments into action_queue
  get_mrr()                    → current MRR from active subscriptions
  sync_all()                   → runs sync_customers + detect_failed_payments
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from config import settings
import database as db


# ── Client ────────────────────────────────────────────────────────────────────

def get_stripe_client():
    """Return the stripe module configured with the secret key (lazy import)."""
    import stripe  # noqa: PLC0415
    stripe.api_key = settings.stripe_secret_key
    return stripe


# ── Customers / Contacts Sync ─────────────────────────────────────────────────

def _ensure_stripe_customer_id_column() -> None:
    """Add stripe_customer_id column to contacts if it doesn't already exist."""
    db.execute(
        """
        ALTER TABLE contacts
        ADD COLUMN IF NOT EXISTS stripe_customer_id TEXT
        """
    )


def sync_customers(limit: int = 100) -> list[dict]:
    """
    Fetch up to `limit` Stripe customers and upsert them into the contacts table,
    matching on email address.

    Returns a list of dicts describing each synced contact.
    """
    stripe = get_stripe_client()
    _ensure_stripe_customer_id_column()

    customers = stripe.Customer.list(limit=limit)
    synced: list[dict] = []

    for customer in customers.auto_paging_iter():
        if not customer.email:
            continue

        email: str = customer.email.lower().strip()
        stripe_id: str = customer.id
        name: str = customer.name or ""

        existing = db.fetchone(
            "SELECT * FROM contacts WHERE email = %s",
            (email,),
        )

        if existing:
            # Update stripe_customer_id (and name if blank)
            db.execute(
                """
                UPDATE contacts
                SET stripe_customer_id = %s,
                    name = COALESCE(NULLIF(name, ''), %s)
                WHERE email = %s
                """,
                (stripe_id, name, email),
            )
            contact = db.fetchone("SELECT * FROM contacts WHERE email = %s", (email,))
        else:
            # Insert a minimal new contact
            import uuid  # noqa: PLC0415
            contact_id = f"contact_{uuid.uuid4().hex[:8]}"
            db.execute(
                """
                INSERT INTO contacts (id, name, email, stripe_customer_id)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (email) DO UPDATE
                    SET stripe_customer_id = EXCLUDED.stripe_customer_id,
                        name = COALESCE(NULLIF(contacts.name, ''), EXCLUDED.name)
                """,
                (contact_id, name, email, stripe_id),
            )
            contact = db.fetchone("SELECT * FROM contacts WHERE email = %s", (email,))

        if contact:
            synced.append(dict(contact))

        # Stop if we've reached the caller-requested limit
        if len(synced) >= limit:
            break

    return synced


# ── Subscription Health ───────────────────────────────────────────────────────

def get_subscription_health() -> list[dict]:
    """
    Fetch all active Stripe subscriptions and return enriched health records.

    Each record includes:
      customer_id, customer_email, plan_name, amount, status,
      current_period_end, days_until_renewal, payment_status, urgency
    """
    stripe = get_stripe_client()

    subscriptions = stripe.Subscription.list(
        status="all",
        limit=100,
        expand=["data.customer", "data.latest_invoice"],
    )

    now_ts = datetime.now(tz=timezone.utc).timestamp()
    results: list[dict] = []

    for sub in subscriptions.auto_paging_iter():
        customer = sub.customer  # expanded object
        customer_id: str = customer.id if hasattr(customer, "id") else str(customer)
        customer_email: str = getattr(customer, "email", "") or ""

        # Plan / price details
        plan_name = ""
        amount_usd: float = 0.0
        if sub.items and sub.items.data:
            item = sub.items.data[0]
            price = item.price
            plan_name = (
                getattr(price, "nickname", None)
                or getattr(price, "lookup_key", None)
                or price.id
            )
            unit_amount = price.unit_amount or 0
            # Convert from cents; handle recurring intervals
            interval = getattr(price.recurring, "interval", "month") if price.recurring else "month"
            interval_count = getattr(price.recurring, "interval_count", 1) if price.recurring else 1
            monthly_divisor = {"day": 30, "week": 4, "month": 1, "year": 12}.get(interval, 1)
            amount_usd = (unit_amount / 100) / (monthly_divisor * interval_count) if monthly_divisor else unit_amount / 100

        current_period_end: int = sub.current_period_end or 0
        days_until_renewal = max(0, int((current_period_end - now_ts) / 86400)) if current_period_end else 0

        # Payment status from latest invoice
        latest_invoice = sub.latest_invoice
        payment_status = "ok"
        if latest_invoice and hasattr(latest_invoice, "payment_intent"):
            pi = latest_invoice.payment_intent
            if pi:
                pi_status = getattr(pi, "status", "")
                if pi_status in ("requires_payment_method", "requires_action"):
                    payment_status = "failed"
                elif pi_status == "processing":
                    payment_status = "processing"

        # Urgency
        is_bad_status = sub.status in ("past_due", "unpaid")
        is_failed_payment = payment_status == "failed"
        urgency = "HIGH" if (is_bad_status or is_failed_payment) else "LOW"

        period_end_dt = (
            datetime.fromtimestamp(current_period_end, tz=timezone.utc).isoformat()
            if current_period_end
            else None
        )

        results.append(
            {
                "customer_id": customer_id,
                "customer_email": customer_email,
                "plan_name": plan_name,
                "amount": round(amount_usd, 2),
                "status": sub.status,
                "current_period_end": period_end_dt,
                "days_until_renewal": days_until_renewal,
                "payment_status": payment_status,
                "urgency": urgency,
                "subscription_id": sub.id,
            }
        )

    return results


# ── Failed Payment Detection ──────────────────────────────────────────────────

def _payment_already_queued(stripe_ref: str) -> bool:
    """Return True if a payment_failed action for this stripe_ref is already queued."""
    row = db.fetchone(
        """
        SELECT id FROM action_queue
        WHERE action_type = 'payment_failed'
          AND payload::jsonb ->> 'stripe_ref' = %s
          AND status IN ('PENDING_APPROVAL', 'APPROVED', 'EXECUTED')
        LIMIT 1
        """,
        (stripe_ref,),
    )
    return row is not None


def detect_failed_payments() -> list[dict]:
    """
    Fetch recent Stripe payment failures and queue them into action_queue.

    Checks:
      • PaymentIntents with status='requires_payment_method'
      • Invoices with status='open' that have a past-due payment

    Skips entries already queued. Returns list of newly queued items.
    """
    stripe = get_stripe_client()
    newly_queued: list[dict] = []

    # ── 1. Failed PaymentIntents ──────────────────────────────────────────────
    failed_pis = stripe.PaymentIntent.list(limit=50)
    for pi in failed_pis.auto_paging_iter():
        if pi.status not in ("requires_payment_method", "requires_action"):
            continue
        if _payment_already_queued(pi.id):
            continue

        customer_email = ""
        if pi.customer:
            try:
                cust = stripe.Customer.retrieve(pi.customer)
                customer_email = cust.email or ""
            except Exception:
                pass

        # Look up contact_id by email
        contact_id: str | None = None
        if customer_email:
            row = db.fetchone("SELECT id FROM contacts WHERE email = %s", (customer_email.lower().strip(),))
            contact_id = row["id"] if row else None

        payload: dict[str, Any] = {
            "stripe_ref": pi.id,
            "customer_id": pi.customer or "",
            "customer_email": customer_email,
            "amount": (pi.amount or 0) / 100,
            "currency": pi.currency or "usd",
            "failure_reason": (
                pi.last_payment_error.message if pi.last_payment_error else "Payment method required"
            ),
            "source": "payment_intent",
        }

        db.execute(
            """
            INSERT INTO action_queue
                (action_type, contact_id, payload, urgency, reason, status)
            VALUES
                ('payment_failed', %s, %s, 'HIGH', %s, 'PENDING_APPROVAL')
            """,
            (
                contact_id,
                json.dumps(payload),
                f"Payment failed for {customer_email or pi.customer or pi.id}",
            ),
        )

        row = db.fetchone(
            """
            SELECT id FROM action_queue
            WHERE action_type = 'payment_failed'
              AND payload::jsonb ->> 'stripe_ref' = %s
            ORDER BY created_at DESC LIMIT 1
            """,
            (pi.id,),
        )

        newly_queued.append(
            {
                "action_queue_id": row["id"] if row else None,
                "stripe_ref": pi.id,
                "customer_email": customer_email,
                "amount": (pi.amount or 0) / 100,
                "failure_reason": payload["failure_reason"],
                "urgency": "HIGH",
            }
        )

    # ── 2. Open Invoices (past-due) ───────────────────────────────────────────
    open_invoices = stripe.Invoice.list(status="open", limit=50)
    for inv in open_invoices.auto_paging_iter():
        stripe_ref = f"inv_{inv.id}"
        if _payment_already_queued(stripe_ref):
            continue

        customer_email = ""
        if inv.customer_email:
            customer_email = inv.customer_email
        elif inv.customer:
            try:
                cust = stripe.Customer.retrieve(inv.customer)
                customer_email = cust.email or ""
            except Exception:
                pass

        contact_id = None
        if customer_email:
            row = db.fetchone("SELECT id FROM contacts WHERE email = %s", (customer_email.lower().strip(),))
            contact_id = row["id"] if row else None

        payload = {
            "stripe_ref": stripe_ref,
            "invoice_id": inv.id,
            "customer_id": inv.customer or "",
            "customer_email": customer_email,
            "amount": (inv.amount_due or 0) / 100,
            "currency": inv.currency or "usd",
            "failure_reason": "Invoice past due / open",
            "source": "invoice",
        }

        db.execute(
            """
            INSERT INTO action_queue
                (action_type, contact_id, payload, urgency, reason, status)
            VALUES
                ('payment_failed', %s, %s, 'HIGH', %s, 'PENDING_APPROVAL')
            """,
            (
                contact_id,
                json.dumps(payload),
                f"Invoice past due for {customer_email or inv.customer or inv.id}",
            ),
        )

        row = db.fetchone(
            """
            SELECT id FROM action_queue
            WHERE action_type = 'payment_failed'
              AND payload::jsonb ->> 'stripe_ref' = %s
            ORDER BY created_at DESC LIMIT 1
            """,
            (stripe_ref,),
        )

        newly_queued.append(
            {
                "action_queue_id": row["id"] if row else None,
                "stripe_ref": stripe_ref,
                "customer_email": customer_email,
                "amount": (inv.amount_due or 0) / 100,
                "failure_reason": "Invoice past due / open",
                "urgency": "HIGH",
            }
        )

    return newly_queued


# ── MRR ───────────────────────────────────────────────────────────────────────

def get_mrr() -> dict:
    """
    Calculate current Monthly Recurring Revenue from active Stripe subscriptions.

    Returns {"mrr": float, "active_subscriptions": int, "currency": "usd"}.
    """
    stripe = get_stripe_client()

    subscriptions = stripe.Subscription.list(status="active", limit=100)
    total_mrr: float = 0.0
    active_count: int = 0

    for sub in subscriptions.auto_paging_iter():
        active_count += 1
        for item in (sub.items.data if sub.items else []):
            price = item.price
            unit_amount: int = price.unit_amount or 0
            quantity: int = getattr(item, "quantity", 1) or 1
            recurring = price.recurring

            if not recurring:
                continue

            interval: str = recurring.interval  # day, week, month, year
            interval_count: int = recurring.interval_count or 1

            # Normalise to monthly
            multipliers = {
                "day": 1 / 30,
                "week": 1 / 4,
                "month": 1,
                "year": 12,
            }
            monthly_factor = multipliers.get(interval, 1) / interval_count
            monthly_amount = (unit_amount / 100) * quantity * monthly_factor
            total_mrr += monthly_amount

    return {
        "mrr": round(total_mrr, 2),
        "active_subscriptions": active_count,
        "currency": "usd",
    }


# ── Sync All ──────────────────────────────────────────────────────────────────

def sync_all() -> dict:
    """
    Run a full Stripe sync:
      1. Sync customers → contacts
      2. Detect failed payments → action_queue

    Returns a summary dict.
    """
    synced_contacts = sync_customers()
    failed_payments = detect_failed_payments()

    return {
        "synced_contacts": len(synced_contacts),
        "failed_payments": len(failed_payments),
        "newly_queued_actions": failed_payments,
    }
