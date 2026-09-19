"""Purge unlinked local seed orders. Keep Fleetbase-linked rows.

Jeff Dean: do not backfill thousands of dummy orders into Fleetbase.
User decision 2026-09-14: delete unlinked seed, keep real/linked bookings.

    cd apps/api && PYTHONPATH=src python scripts/purge_unlinked_seed_orders.py --dry-run
    cd apps/api && PYTHONPATH=src python scripts/purge_unlinked_seed_orders.py --execute
"""

from __future__ import annotations

import argparse

from sqlalchemy import text

from porterchain_api.db import SessionLocal, init_db

# Soft refs that may lack a real FK. Column verified at runtime.
_SOFT_REFS: tuple[tuple[str, str], ...] = (
    ("order_events", "order_id"),
    ("order_exceptions", "order_id"),
    ("packages", "order_id"),
    ("payments", "order_id"),
    ("invoices", "order_id"),
    ("bookings", "order_id"),
    ("claims", "order_id"),
    ("support_tickets", "order_id"),
    ("driver_incidents", "order_id"),
    ("driver_stop_meta", "order_id"),
    ("billing_ledger_entries", "order_id"),
    ("fleetbase_sync_audit", "order_id"),
    ("booking_drafts", "order_id"),
)


def _children(db) -> list[tuple[str, str]]:
    """(table, column) that reference orders — FK discovery + verified soft refs."""
    rows = db.execute(
        text(
            """
            SELECT tc.table_name, kcu.column_name
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
              ON tc.constraint_name = kcu.constraint_name
             AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage AS ccu
              ON ccu.constraint_name = tc.constraint_name
             AND ccu.table_schema = tc.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY'
              AND ccu.table_name = 'orders'
              AND ccu.column_name = 'id'
              AND tc.table_name <> 'orders'
            ORDER BY tc.table_name
            """
        )
    ).fetchall()
    discovered = [(str(t), str(c)) for t, c in rows]
    seen = {t for t, _ in discovered}
    for table, column in _SOFT_REFS:
        if table in seen:
            continue
        exists = db.execute(
            text(
                """
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = :table
                  AND column_name = :column
                """
            ),
            {"table": table, "column": column},
        ).scalar()
        if exists:
            discovered.append((table, column))
    return discovered


def _count(db, sql: str, **params) -> int:
    return int(db.execute(text(sql), params).scalar() or 0)


def purge(*, execute: bool) -> None:
    init_db()
    db = SessionLocal()
    try:
        linked = _count(db, "SELECT COUNT(*) FROM orders WHERE fleetbase_order_id IS NOT NULL")
        unlinked = _count(db, "SELECT COUNT(*) FROM orders WHERE fleetbase_order_id IS NULL")
        pending_jobs = _count(
            db,
            """
            SELECT COUNT(*) FROM fleetbase_sync_jobs j
            JOIN orders o ON o.id = j.order_id
            WHERE o.fleetbase_order_id IS NULL
              AND j.status IN ('pending', 'retrying')
            """,
        )
        print(f"Linked keep:              {linked}")
        print(f"Unlinked seed delete:     {unlinked}")
        print(f"Unlinked pending jobs:    {pending_jobs}")
        if not execute:
            print("Dry run — pass --execute to apply")
            db.rollback()
            return

        # Drop all sync jobs for unlinked orders (pending + history).
        deleted_jobs = db.execute(
            text(
                """
                DELETE FROM fleetbase_sync_jobs j
                WHERE j.order_id IN (
                  SELECT o.id FROM orders o WHERE o.fleetbase_order_id IS NULL
                )
                """
            )
        ).rowcount
        print(f"Deleted sync jobs:        {deleted_jobs}")

        # booking_draft_audits → booking_drafts → orders
        db.execute(
            text(
                """
                DELETE FROM booking_draft_audits
                WHERE booking_draft_id IN (
                  SELECT d.id FROM booking_drafts d
                  WHERE d.order_id IN (
                    SELECT o.id FROM orders o WHERE o.fleetbase_order_id IS NULL
                  )
                )
                """
            )
        )

        # payments before invoices (grandchild FK)
        db.execute(
            text(
                """
                DELETE FROM payments
                WHERE order_id IN (
                  SELECT o.id FROM orders o WHERE o.fleetbase_order_id IS NULL
                )
                OR invoice_id IN (
                  SELECT i.id FROM invoices i
                  WHERE i.order_id IN (
                    SELECT o.id FROM orders o WHERE o.fleetbase_order_id IS NULL
                  )
                )
                """
            )
        )

        for table, column in _children(db):
            if table in ("payments", "fleetbase_sync_jobs"):
                continue
            db.execute(
                text(
                    f"""
                    DELETE FROM {table}
                    WHERE {column} IN (
                      SELECT o.id FROM orders o WHERE o.fleetbase_order_id IS NULL
                    )
                    """
                )
            )

        deleted_orders = db.execute(
            text("DELETE FROM orders WHERE fleetbase_order_id IS NULL")
        ).rowcount
        db.commit()
        print(f"Deleted orders:           {deleted_orders}")
        print("Committed.")
        print(
            "Remaining orders:",
            _count(db, "SELECT COUNT(*) FROM orders"),
            "linked",
            _count(db, "SELECT COUNT(*) FROM orders WHERE fleetbase_order_id IS NOT NULL"),
        )
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    purge(execute=bool(args.execute) and not args.dry_run)


if __name__ == "__main__":
    main()
