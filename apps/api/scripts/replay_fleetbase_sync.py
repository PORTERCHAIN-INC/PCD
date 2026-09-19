#!/usr/bin/env python3
"""Replay Fleetbase dead letters and sync unlinked orders (masterrule D1 G2).

After Phase 2, push_order is enqueue-only — this script enqueues then drains via
process_retry_queue (_http_*). Do not call push_order and expect an immediate link.

Usage:
    cd apps/api && PYTHONPATH=src python scripts/replay_fleetbase_sync.py
    cd apps/api && PYTHONPATH=src python scripts/replay_fleetbase_sync.py --requeue-all
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

API_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(API_ROOT / "src"))

from sqlalchemy import func

from porterchain_api.config import get_settings
from porterchain_api.db import SessionLocal, init_db
from porterchain_api.fleetbase_engine import ErrorQueue
from porterchain_api.fleetbase_engine.booking_sync_service import BookingSyncService
from porterchain_api.fleetbase_engine.retry_queue import RetryQueue
from porterchain_api.booking_models import Order
from porterchain_fleetbase_adapter.circuit_breaker import reset_shared_breaker


def _link_rate(db) -> tuple[int, int, float]:
    total = db.query(func.count(Order.id)).scalar() or 0
    linked = db.query(func.count(Order.id)).filter(Order.fleetbase_order_id.isnot(None)).scalar() or 0
    pct = (linked / total * 100.0) if total else 100.0
    return linked, total, pct


def main() -> int:
    parser = argparse.ArgumentParser(description="Replay Fleetbase sync backlog")
    parser.add_argument("--requeue-all", action="store_true", help="Requeue every dead-letter job")
    parser.add_argument("--target-pct", type=float, default=90.0, help="Stop when link rate reaches this %%")
    parser.add_argument("--max-rounds", type=int, default=10, help="Max process_retry_queue rounds")
    parser.add_argument(
        "--round-sleep",
        type=float,
        default=2.0,
        help="Seconds to sleep between rounds (rate-limit friendly)",
    )
    args = parser.parse_args()

    init_db()
    settings = get_settings()
    if not settings.fleetbase_dispatch_bridge:
        print("ERROR: FLEETBASE_DISPATCH_BRIDGE is false — enable in apps/api/.env")
        return 1
    if not settings.fleetbase_api_key:
        print("ERROR: FLEETBASE_API_KEY missing — create Fleetbase API credential (see RUNBOOK.md)")
        return 1
    if not settings.fleetbase_default_company_uuid:
        print("ERROR: FLEETBASE_DEFAULT_COMPANY_UUID missing")
        return 1

    # Permanent bond: clear circuit left open by a prior rate-limit storm.
    reset_shared_breaker()

    svc = BookingSyncService()
    with SessionLocal() as db:
        if args.requeue_all:
            dead = ErrorQueue.list_dead(db, limit=500)
            for job in dead:
                ErrorQueue.requeue(db, job.id)
            print(f"Requeued {len(dead)} dead-letter job(s)")

        unlinked = (
            db.query(Order)
            .filter(Order.fleetbase_order_id.is_(None))
            .order_by(Order.created_at.asc())
            .all()
        )
        for order in unlinked:
            RetryQueue.enqueue(
                db,
                direction="outbound",
                kind="order",
                order_id=order.id,
                fleetbase_order_id=order.fleetbase_order_id,
                idempotency_key=f"order:{order.id}",
                payload={"order_id": order.id},
            )
        print(f"Enqueued {len(unlinked)} unlinked order(s) for drain")

        for round_num in range(1, args.max_rounds + 1):
            # Ops catch-up may drain more than limit=1; uvicorn /sync/process stays capped.
            result = svc.process_retry_queue(db, settings, limit=10)
            linked, total, pct = _link_rate(db)
            print(
                f"Round {round_num}: queue={result} | linked {linked}/{total} ({pct:.1f}%)"
            )
            if pct >= args.target_pct:
                print(f"Target {args.target_pct}% reached")
                return 0
            if result["processed"] == 0 and result["failed"] == 0:
                break
            # Back off when Fleetbase rate-limits or circuit is recovering.
            sleep_s = args.round_sleep
            if int(result.get("failed") or 0) > int(result.get("processed") or 0):
                sleep_s = max(sleep_s, 5.0)
                reset_shared_breaker()
            if sleep_s > 0:
                time.sleep(sleep_s)

        linked, total, pct = _link_rate(db)
        dead_left = len(ErrorQueue.list_dead(db, limit=500))
        print(f"Final: {linked}/{total} linked ({pct:.1f}%), dead_letters={dead_left}")
        return 0 if pct >= args.target_pct else 1


if __name__ == "__main__":
    raise SystemExit(main())
