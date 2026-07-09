#!/usr/bin/env python3
"""Porterchain async worker — consumes event bus + task queues."""

import logging
import signal
import sys
import time

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("porterchain.worker")

_running = True
_last_fleetbase_retry_at = 0.0
_last_draft_reconcile_at = 0.0
_last_standing_orders_at = 0.0
FLEETBASE_RETRY_INTERVAL_SECONDS = 60
DRAFT_RECONCILE_INTERVAL_SECONDS = 300
STANDING_ORDERS_INTERVAL_SECONDS = 300


def _touch_heartbeat() -> None:
    try:
        from porterchain_shared.redis_client import get_redis_client

        get_redis_client().setex("porterchain:worker:heartbeat", 120, str(time.time()))
    except Exception:
        logger.debug("worker heartbeat write failed", exc_info=True)


def _shutdown(_signum, _frame) -> None:
    global _running
    _running = False
    logger.info("shutdown signal received")


def _drain_queues(publisher, *, timeout_seconds: int = 1) -> int:
    from porterchain_shared.queue.names import QueueName
    from processors import process_queue_message

    processed = 0
    for queue in QueueName:
        while True:
            msg = publisher.dequeue(queue, timeout_seconds=0 if processed else timeout_seconds)
            if not msg:
                break
            try:
                process_queue_message(msg)
                processed += 1
            except Exception:
                logger.exception("failed to process %s message %s", queue.value, msg.message_id)
    return processed


def _drain_fleetbase_retry_queue() -> int:
    """Periodically process due Fleetbase sync retry jobs."""
    global _last_fleetbase_retry_at
    now = time.monotonic()
    if now - _last_fleetbase_retry_at < FLEETBASE_RETRY_INTERVAL_SECONDS:
        return 0
    _last_fleetbase_retry_at = now

    from porterchain_api.config import get_settings
    from porterchain_api.db import SessionLocal
    from porterchain_api.fleetbase_engine.booking_sync_service import BookingSyncService

    settings = get_settings()
    if not settings.fleetbase_dispatch_bridge:
        return 0

    with SessionLocal() as db:
        result = BookingSyncService().process_retry_queue(db, settings)
    processed = int(result.get("processed", 0))
    if processed or result.get("failed") or result.get("skipped"):
        logger.info(
            "fleetbase retry drain: processed=%s failed=%s skipped=%s",
            result.get("processed", 0),
            result.get("failed", 0),
            result.get("skipped", 0),
        )
    return processed


def _drain_draft_reconciliation() -> int:
    """Expire stale booking drafts and repair draft/order mismatches."""
    global _last_draft_reconcile_at
    now = time.monotonic()
    if now - _last_draft_reconcile_at < DRAFT_RECONCILE_INTERVAL_SECONDS:
        return 0
    _last_draft_reconcile_at = now

    from porterchain_api.booking_engine.draft_reconciliation_service import (
        BookingDraftReconciliationService,
    )
    from porterchain_api.config import get_settings
    from porterchain_api.db import SessionLocal

    settings = get_settings()
    with SessionLocal() as db:
        result = BookingDraftReconciliationService().run_cycle(db, settings)
    if result.get("expired") or result.get("repaired"):
        logger.info("draft reconciliation: %s", result)
    return int(result.get("expired", 0)) + int(result.get("repaired", 0))


def _drain_standing_orders() -> int:
    """Materialize due recurring merchant standing orders (§8.1.11)."""
    global _last_standing_orders_at
    now = time.monotonic()
    if now - _last_standing_orders_at < STANDING_ORDERS_INTERVAL_SECONDS:
        return 0
    _last_standing_orders_at = now

    from porterchain_api.config import get_settings
    from porterchain_api.db import SessionLocal
    from porterchain_api.merchant_engine.standing_order_service import MerchantStandingOrderService

    settings = get_settings()
    with SessionLocal() as db:
        result = MerchantStandingOrderService().run_due_orders(db, settings)
    if result.get("created") or result.get("failed"):
        logger.info(
            "standing orders drain: processed=%s created=%s failed=%s skipped=%s",
            result.get("processed", 0),
            result.get("created", 0),
            result.get("failed", 0),
            result.get("skipped", 0),
        )
    return int(result.get("created", 0))


def main() -> None:
    from porterchain_shared.queue.names import QueueName
    from porterchain_shared.queue.publisher import get_queue_publisher
    from porterchain_shared.redis_health import require_redis_for_production

    require_redis_for_production()

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    publisher = get_queue_publisher()
    logger.info("worker started — queues only: %s", ", ".join(q.value for q in QueueName))

    while _running:
        try:
            processed = _drain_queues(publisher, timeout_seconds=1)
            processed += _drain_fleetbase_retry_queue()
            processed += _drain_draft_reconciliation()
            processed += _drain_standing_orders()
            _touch_heartbeat()
        except Exception:
            logger.exception("worker loop error — backing off before retry")
            time.sleep(2)
            continue
        if processed == 0:
            time.sleep(0.5)

    logger.info("worker stopped")
    sys.exit(0)


if __name__ == "__main__":
    main()
