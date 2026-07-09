"""Purge operational / transactional data — keep all users and vehicles.

Preserves:
  - admin_users, customers, drivers, merchants, merchant_users
  - porterchain_users, user_invitations, identity_links
  - vehicles
  - system_config, pricing_tariffs, pricing_zones, promotions

Clears orders, quotes, CRM pipeline, routes, notifications, support, etc.

Usage:
    cd apps/api && PYTHONPATH=src python scripts/purge_operational_data.py
    cd apps/api && PYTHONPATH=src python scripts/purge_operational_data.py --dry-run
"""

from __future__ import annotations

import argparse

from sqlalchemy import text

from porterchain_api.db import SessionLocal, init_db

PRESERVE_TABLES = frozenset(
    {
        "alembic_version",
        "admin_users",
        "customers",
        "drivers",
        "merchants",
        "merchant_users",
        "porterchain_users",
        "user_invitations",
        "identity_links",
        "vehicles",
        "system_config",
        "pricing_tariffs",
        "pricing_zones",
        "promotions",
    }
)

# Child tables first (FK-safe delete order).
PURGE_TABLES = [
    "notification_delivery_logs",
    "notification_devices",
    "notification_preferences",
    "notification_records",
    "order_events",
    "order_exceptions",
    "payments",
    "invoices",
    "bookings",
    "orders",
    "booking_draft_audits",
    "booking_drafts",
    "abandoned_checkouts",
    "quotes",
    "visitor_sessions",
    "leads",
    "domain_events",
    "stripe_webhook_events",
    "billing_ledger_entries",
    "driver_shift_activities",
    "driver_shifts",
    "driver_stop_meta",
    "driver_offline_actions",
    "driver_location_pings",
    "driver_incidents",
    "driver_bonuses",
    "driver_wallet_transactions",
    "driver_payouts",
    "route_center_plans",
    "route_center_templates",
    "fleetbase_sync_audit",
    "fleetbase_sync_jobs",
    "merchant_webhook_deliveries",
    "merchant_webhooks",
    "merchant_api_usage_logs",
    "merchant_api_keys",
    "merchant_audit_logs",
    "merchant_booking_templates",
    "bulk_import_jobs",
    "merchant_recipients",
    "saved_addresses",
    "merchant_contracts",
    "claims",
    "support_tickets",
    "crm_tasks",
    "crm_notes",
    "crm_documents",
    "crm_invoices",
    "crm_activities",
    "crm_sales_tasks",
    "crm_contracts",
    "crm_quotations",
    "crm_deals",
    "crm_contacts",
    "crm_leads",
    "crm_companies",
    "admin_audit_logs",
]


def _count(db, table: str) -> int:
    try:
        return db.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar() or 0
    except Exception:
        return -1


def _list_tables(db) -> list[str]:
    rows = db.execute(
        text(
            """
            SELECT tablename FROM pg_tables
            WHERE schemaname = 'public'
            ORDER BY tablename
            """
        )
    ).fetchall()
    return [r[0] for r in rows]


def purge(*, dry_run: bool) -> None:
    init_db()
    db = SessionLocal()
    try:
        all_tables = _list_tables(db)
        unknown_purge = [t for t in PURGE_TABLES if t not in all_tables]
        if unknown_purge:
            raise RuntimeError(f"Unknown purge tables: {unknown_purge}")

        print("Preserving:")
        for table in sorted(PRESERVE_TABLES):
            if table in all_tables:
                print(f"  {table}: {_count(db, table)} rows")

        total_purged = 0
        for table in PURGE_TABLES:
            n = _count(db, table)
            if n <= 0:
                continue
            print(f"{'Would purge' if dry_run else 'Purging'} {table}: {n} rows")
            total_purged += n
            if not dry_run:
                db.execute(text(f"DELETE FROM {table}"))

        if not dry_run:
            db.execute(
                text(
                    """
                    UPDATE drivers
                    SET wallet_balance_cents = 0,
                        is_online = false,
                        availability = 'offline'
                    """
                )
            )
            print("Reset driver wallet / online flags")

        unlisted = [t for t in all_tables if t not in PRESERVE_TABLES and t not in PURGE_TABLES]
        if unlisted:
            print("\nWarning: tables not in preserve or purge lists (left unchanged):")
            for t in unlisted:
                print(f"  {t}: {_count(db, t)} rows")

        if dry_run:
            print(f"\nDry run complete — would purge ~{total_purged} rows")
            db.rollback()
        else:
            db.commit()
            print(f"\nDone. Purged ~{total_purged} rows.")
            print("\nRemaining:")
            for table in sorted(PRESERVE_TABLES):
                if table in all_tables and table != "alembic_version":
                    print(f"  {table}: {_count(db, table)} rows")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Purge operational data; keep users and vehicles")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without deleting")
    args = parser.parse_args()
    purge(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
