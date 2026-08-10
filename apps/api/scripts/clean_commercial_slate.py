"""Dev-only commercial slate wipe for clean E2E validation.

Keeps: Fleetbase company/user/api_credentials/order_configs,
       Clerk/Stripe env, founder admin identity when possible.

Clears: PC orders + related commercial rows; Fleetbase orders/payloads/places.

Usage:
    cd apps/api && PYTHONPATH=src python scripts/clean_commercial_slate.py
"""

from __future__ import annotations

import sys
from pathlib import Path

API_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(API_ROOT / "src"))

from sqlalchemy import text

from porterchain_api.db import SessionLocal, init_db


# Order matters for FK-ish deletes where ORM cascades are incomplete.
PC_DELETE_SQL = [
    "DELETE FROM fleetbase_sync_jobs",
    "DELETE FROM fleetbase_sync_audit",
    "DELETE FROM analytics_stop_legs",
    "DELETE FROM analytics_events",
    "DELETE FROM order_exceptions",
    "DELETE FROM order_events",
    "DELETE FROM claims",
    "DELETE FROM domain_events WHERE aggregate_type IN ('order','payment','booking','quote','claim')",
    "DELETE FROM payments",
    "DELETE FROM invoices",
    "DELETE FROM crm_invoices",
    "DELETE FROM standing_orders",
    "DELETE FROM bookings",  # FK → orders
    "DELETE FROM orders",
    "DELETE FROM booking_draft_audits",
    "DELETE FROM booking_drafts",
    "DELETE FROM quotes",
    "DELETE FROM abandoned_checkouts",
]


def wipe_porterchain() -> dict[str, int]:
    init_db()
    db = SessionLocal()
    counts: dict[str, int] = {}
    try:
        for sql in PC_DELETE_SQL:
            table = sql.split(" FROM ", 1)[1].split(" ", 1)[0]
            try:
                result = db.execute(text(sql))
                counts[table] = result.rowcount or 0
                db.commit()
            except Exception as exc:  # noqa: BLE001 — best-effort per table
                db.rollback()
                counts[table] = -1
                print(f"  skip {table}: {exc}")
        try:
            r = db.execute(
                text(
                    "UPDATE drivers SET fleetbase_driver_id = NULL "
                    "WHERE fleetbase_driver_id IS NOT NULL "
                    "AND fleetbase_driver_id NOT LIKE 'driver_%'"
                )
            )
            counts["drivers_fb_cleared"] = r.rowcount or 0
            db.commit()
        except Exception as exc:  # noqa: BLE001
            db.rollback()
            print(f"  skip drivers clear: {exc}")
    finally:
        db.close()
    return counts


def wipe_fleetbase() -> dict[str, int]:
    """Truncate execution tables via mysql CLI inside docker."""
    import subprocess

    sql = """
SET FOREIGN_KEY_CHECKS=0;
TRUNCATE TABLE tracking_statuses;
TRUNCATE TABLE tracking_numbers;
TRUNCATE TABLE proofs;
TRUNCATE TABLE positions;
TRUNCATE TABLE waypoints;
TRUNCATE TABLE payloads;
TRUNCATE TABLE places;
TRUNCATE TABLE orders;
TRUNCATE TABLE manifest_stops;
TRUNCATE TABLE manifests;
TRUNCATE TABLE work_orders;
TRUNCATE TABLE porterchain_proof_of_delivery;
TRUNCATE TABLE porterchain_tracked_unit_events;
TRUNCATE TABLE porterchain_tracked_units;
TRUNCATE TABLE porterchain_tracking_sequences;
SET FOREIGN_KEY_CHECKS=1;
SELECT 'orders' t, COUNT(*) c FROM orders
UNION ALL SELECT 'places', COUNT(*) FROM places
UNION ALL SELECT 'api_credentials', COUNT(*) FROM api_credentials
UNION ALL SELECT 'order_configs', COUNT(*) FROM order_configs
UNION ALL SELECT 'companies', COUNT(*) FROM companies
UNION ALL SELECT 'drivers', COUNT(*) FROM drivers;
"""
    cmd = [
        "docker",
        "exec",
        "-i",
        "porterchain-mysql",
        "mysql",
        "-ufleetbase",
        "-pchange-me-fleetbase",
        "fleetbase",
    ]
    proc = subprocess.run(cmd, input=sql, capture_output=True, text=True, check=False)
    print(proc.stdout)
    if proc.returncode != 0:
        print(proc.stderr)
        # Some tables may not exist — try minimal wipe
        minimal = """
SET FOREIGN_KEY_CHECKS=0;
TRUNCATE TABLE orders;
TRUNCATE TABLE payloads;
TRUNCATE TABLE places;
SET FOREIGN_KEY_CHECKS=1;
SELECT COUNT(*) AS orders FROM orders;
"""
        proc2 = subprocess.run(cmd, input=minimal, capture_output=True, text=True, check=False)
        print(proc2.stdout)
        print(proc2.stderr)
        return {"ok": proc2.returncode == 0}
    return {"ok": 1}


def main() -> None:
    print("=== Phase 0 · Clean commercial slate ===")
    print("Wiping PorterChain commercial rows…")
    pc = wipe_porterchain()
    for k, v in pc.items():
        print(f"  {k}: {v}")
    print("Wiping Fleetbase orders/payloads/places…")
    fb = wipe_fleetbase()
    print(f"  fleetbase wipe: {fb}")
    print("Done. Company/user/api key/order_config preserved.")


if __name__ == "__main__":
    main()
