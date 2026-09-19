"""Purge local dummy / seed data while preserving CRM leads.

Preserves:
  - crm_leads (all rows, all columns)
  - leads (website visitor leads)
  - admin_users, system_config, pricing_tariffs, pricing_zones, promotions

Usage:
    cd apps/api && PYTHONPATH=src python scripts/purge_dummy_data.py
    cd apps/api && PYTHONPATH=src python scripts/purge_dummy_data.py --dry-run
"""

from __future__ import annotations

import argparse

from sqlalchemy import text

from porterchain_api.db import SessionLocal, init_db

# Tables cleared entirely (operational / demo data).
PURGE_TABLES = [
    # Orders & booking flow
    "order_events",
    "order_exceptions",
    "domain_events",
    "payments",
    "invoices",
    "orders",
    "bookings",
    "quotes",
    "booking_draft_audits",
    "booking_drafts",
    "abandoned_checkouts",
    "visitor_sessions",
    "customers",
    # Fleet / dispatch
    "driver_shift_activities",
    "driver_shifts",
    "driver_stop_meta",
    "driver_offline_actions",
    "driver_location_pings",
    "driver_incidents",
    "driver_bonuses",
    "driver_wallet_transactions",
    "driver_payouts",
    "vehicles",
    "drivers",
    # Merchant dev / demo
    "merchant_webhook_deliveries",
    "merchant_webhooks",
    "merchant_api_usage_logs",
    "merchant_api_keys",
    "merchant_audit_logs",
    "merchant_booking_templates",
    "bulk_import_jobs",
    "merchant_recipients",
    "saved_addresses",
    "merchant_users",
    "merchants",
    "merchant_contracts",
    # Support / claims / ops
    "claims",
    "support_tickets",
    "crm_tasks",
    "crm_notes",
    # Notifications
    "notification_delivery_logs",
    "notification_devices",
    "notification_preferences",
    "notification_records",
    # Fleetbase sync
    "fleetbase_sync_audit",
    "fleetbase_sync_jobs",
    # Billing / identity
    "billing_ledger_entries",
    "identity_links",
    # CRM sales artifacts (not leads)
    "crm_documents",
    "crm_invoices",
    "crm_activities",
    "crm_sales_tasks",
    "crm_contracts",
    "crm_quotations",
    "crm_deals",
    "crm_contacts",
    # Admin audit trail (dummy ops)
    "admin_audit_logs",
]

SEED_COMPANY_NAMES = (
    "Maple Leaf Distributors Inc.",
    "Northern Medical Supplies Ltd.",
    "GTA BuildMat Supply Co.",
    "Riverside Coffee Roasters",
)


def _count(db, table: str) -> int:
    try:
        return db.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar() or 0
    except Exception:
        return -1


def purge(*, dry_run: bool) -> None:
    init_db()
    db = SessionLocal()
    try:
        lead_count = _count(db, "crm_leads")
        website_leads = _count(db, "leads")
        print(f"Preserving crm_leads: {lead_count} rows")
        print(f"Preserving leads:      {website_leads} rows")

        # crm_leads rows are never modified — only preserved.

        deleted_companies = 0
        for name in SEED_COMPANY_NAMES:
            row = db.execute(
                text("SELECT id FROM crm_companies WHERE legal_name = :n"),
                {"n": name},
            ).first()
            if row:
                deleted_companies += 1
                print(f"Removing seed company: {name}")
                if not dry_run:
                    db.execute(text("DELETE FROM crm_companies WHERE id = :id"), {"id": row[0]})

        # Companies with no lead pointing at them (seed orphans).
        orphan_count = db.execute(
            text(
                """
                SELECT COUNT(*) FROM crm_companies c
                WHERE NOT EXISTS (SELECT 1 FROM crm_leads l WHERE l.company_id = c.id)
                """
            )
        ).scalar()
        if orphan_count:
            print(f"Removing {orphan_count} crm_companies not linked to any lead")
            if not dry_run:
                db.execute(
                    text(
                        """
                        DELETE FROM crm_companies
                        WHERE id NOT IN (
                            SELECT DISTINCT company_id FROM crm_leads WHERE company_id IS NOT NULL
                        )
                        """
                    )
                )

        total_purged = 0
        for table in PURGE_TABLES:
            n = _count(db, table)
            if n <= 0:
                continue
            print(f"{'Would purge' if dry_run else 'Purging'} {table}: {n} rows")
            total_purged += n
            if not dry_run:
                db.execute(text(f"DELETE FROM {table}"))

        if dry_run:
            print(f"\nDry run complete — would purge ~{total_purged} rows (+ seed companies)")
            db.rollback()
        else:
            db.commit()
            print(f"\nDone. Purged ~{total_purged} rows. Removed {deleted_companies} seed companies.")
            print(f"crm_leads preserved: {_count(db, 'crm_leads')}")
            print(f"leads preserved:      {_count(db, 'leads')}")
            print(f"crm_companies kept:   {_count(db, 'crm_companies')} (linked to leads)")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Purge dummy data, keep CRM leads")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without deleting")
    args = parser.parse_args()
    purge(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
