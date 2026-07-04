#!/usr/bin/env python3
"""Validate Porterchain PostgreSQL modules — schema + service smoke checks."""

from __future__ import annotations

import sys
from pathlib import Path

API_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(API_ROOT / "src"))

from sqlalchemy import inspect, text

from porterchain_api.admin_engine.crm_sales_service import CrmSalesService
from porterchain_api.db import SessionLocal, engine, init_db

MODULE_TABLES: dict[str, list[str]] = {
    "website_quotes": ["quotes", "customers", "visitor_sessions"],
    "bookings": ["bookings", "booking_drafts", "payments"],
    "orders": ["orders", "order_events", "order_exceptions"],
    "merchants": ["merchants", "merchant_users", "merchant_api_keys"],
    "crm": ["crm_leads", "crm_companies", "crm_deals", "crm_quotations"],
    "finance": ["invoices", "payments", "billing_ledger_entries"],
    "claims": ["claims"],
    "support": ["support_tickets"],
    "notifications": ["notification_records", "notification_devices"],
    "drivers": ["drivers", "driver_shifts", "driver_location_pings"],
    "fleetbase_adapter": ["fleetbase_sync_jobs", "fleetbase_sync_audit"],
    "route_center": ["route_center_plans", "route_center_templates"],
    "auth": ["admin_users", "porterchain_users", "user_invitations"],
}


def main() -> int:
    init_db()
    insp = inspect(engine)
    tables = set(insp.get_table_names())
    failed = False

    print("PostgreSQL module validation")
    print(f"Database: {engine.url.database}")
    print("-" * 48)

    for module, required in MODULE_TABLES.items():
        missing = [t for t in required if t not in tables]
        if missing:
            print(f"FAIL {module}: missing tables {missing}")
            failed = True
            continue
        with SessionLocal() as db:
            for table in required:
                db.execute(text(f"SELECT COUNT(*) FROM {table}"))
        print(f"OK   {module}: {len(required)} tables")

    with SessionLocal() as db:
        CrmSalesService().list_companies(db, province="ON", limit=5)
    print("OK   crm_json_filters: province query")

    with SessionLocal() as db:
        db.execute(text("BEGIN"))
        db.execute(text("SELECT 1"))
        db.rollback()
    print("OK   transactions: rollback")

    print("-" * 48)
    if failed:
        print("RESULT: FAILED")
        return 1
    print("RESULT: PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
