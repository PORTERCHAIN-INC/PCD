"""Production go-live empty slate — wipe demo/test business data.

Preserves staff + commercial config only:
  - admin_users, staff_webauthn_credentials
  - alembic_version
  - system_config, pricing_tariffs, pricing_zones, promotions
  - blog_posts (marketing CMS)

Clears customers, merchants, drivers, orders, quotes, CRM, payments, etc.
Retail settlement remains Stripe-only (no Interac path in this product).

Usage (local / droplet API container):
  PYTHONPATH=src python scripts/go_live_empty_slate.py --dry-run
  PYTHONPATH=src python scripts/go_live_empty_slate.py --confirm GO_LIVE
"""

from __future__ import annotations

import argparse
import os
import sys

from sqlalchemy import text

from porterchain_api.db import SessionLocal, init_db

PRESERVE_TABLES = frozenset(
    {
        "alembic_version",
        "admin_users",
        "staff_webauthn_credentials",
        "system_config",
        "pricing_tariffs",
        "pricing_zones",
        "promotions",
        "blog_posts",
    }
)

# FK-safe delete order (children first).
PURGE_TABLES = [
    "notification_delivery_logs",
    "notification_devices",
    "notification_preferences",
    "notification_user_settings",
    "notification_records",
    "order_events",
    "order_exceptions",
    "analytics_stop_legs",
    "analytics_events",
    "payments",
    "invoices",
    "crm_invoices",
    "bookings",
    "standing_orders",
    "orders",
    "booking_draft_audits",
    "booking_drafts",
    "abandoned_checkouts",
    "quotes",
    "visitor_sessions",
    "leads",
    "domain_events",
    "stripe_webhook_events",
    "clerk_webhook_events",
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
    "vehicles",
    "drivers",
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
    "merchant_users",
    "merchants",
    "claims",
    "support_tickets",
    "crm_tasks",
    "crm_notes",
    "crm_documents",
    "crm_activities",
    "crm_sales_tasks",
    "crm_contracts",
    "crm_quotations",
    "crm_deals",
    "crm_contacts",
    "crm_leads",
    "crm_companies",
    "admin_audit_logs",
    "access_audit_logs",
    "identity_migration_records",
    "identity_migration_runs",
    "identity_links",
    "user_invitations",
    "user_emails",
    "customers",
    "porterchain_users",
]


def _count(db, table: str) -> int:
    try:
        return int(db.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar() or 0)
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
    app_env = (os.getenv("APP_ENV") or os.getenv("ENVIRONMENT") or "").strip().lower()
    init_db()
    db = SessionLocal()
    try:
        all_tables = _list_tables(db)
        missing = [t for t in PURGE_TABLES if t not in all_tables]
        if missing:
            print(f"Note: skip missing tables: {missing}")

        print(f"APP_ENV={app_env or '(unset)'}")
        print("Preserving:")
        for table in sorted(PRESERVE_TABLES):
            if table in all_tables:
                print(f"  {table}: {_count(db, table)} rows")

        # Detach staff from platform users before deleting porterchain_users.
        if not dry_run and "admin_users" in all_tables:
            db.execute(text("UPDATE admin_users SET porterchain_user_id = NULL"))
            print("Cleared admin_users.porterchain_user_id")

        total = 0
        for table in PURGE_TABLES:
            if table not in all_tables:
                continue
            n = _count(db, table)
            if n <= 0:
                continue
            print(f"{'Would purge' if dry_run else 'Purging'} {table}: {n} rows")
            total += n
            if not dry_run:
                db.execute(text(f"DELETE FROM {table}"))

        unlisted = [
            t for t in all_tables if t not in PRESERVE_TABLES and t not in PURGE_TABLES
        ]
        if unlisted:
            print("\nWarning: tables not in preserve/purge lists (unchanged):")
            for t in unlisted:
                print(f"  {t}: {_count(db, t)} rows")

        if dry_run:
            print(f"\nDry run — would purge ~{total} rows")
            db.rollback()
        else:
            db.commit()
            print(f"\nGo-live slate empty. Purged ~{total} rows.")
            print("Remaining:")
            for table in sorted(PRESERVE_TABLES):
                if table in all_tables:
                    print(f"  {table}: {_count(db, table)} rows")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Go-live empty slate (destructive)")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--confirm",
        default="",
        help='Must be exactly "GO_LIVE" to mutate',
    )
    args = parser.parse_args()
    if not args.dry_run and args.confirm != "GO_LIVE":
        print('Refusing: pass --confirm GO_LIVE (or --dry-run)', file=sys.stderr)
        sys.exit(2)
    purge(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
