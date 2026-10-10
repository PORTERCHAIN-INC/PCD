#!/usr/bin/env python3
"""Porterchain async worker — consumes event bus + task queues."""

import argparse
import logging
import os
import signal
import sys
import time
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("porterchain.worker")

_running = True
_last_draft_reconcile_at = 0.0
_last_standing_orders_at = 0.0
_last_interac_inbox_at = 0.0
_last_billing_cycle_at = 0.0
_last_finance_daily_at = 0.0
_last_notification_retry_at = 0.0
_last_webhook_retry_at = 0.0
_last_shopify_sync_retry_at = 0.0
_last_compliance_expiry_at = 0.0
_last_lead_nurture_at = 0.0
_last_lead_sla_at = 0.0
_last_lead_archive_at = 0.0
_last_shopify_retention_at = 0.0
_last_lead_agent_at = 0.0
_last_blog_schedule_at = 0.0
_last_delivery_sla_at = 0.0
DRAFT_RECONCILE_INTERVAL_SECONDS = 300
STANDING_ORDERS_INTERVAL_SECONDS = 300
INTERAC_INBOX_INTERVAL_SECONDS = 300
BILLING_CYCLE_INTERVAL_SECONDS = 3600
FINANCE_DAILY_INTERVAL_SECONDS = 86400
NOTIFICATION_RETRY_INTERVAL_SECONDS = 60
WEBHOOK_RETRY_INTERVAL_SECONDS = 60
COMPLIANCE_EXPIRY_INTERVAL_SECONDS = 900
LEAD_NURTURE_INTERVAL_SECONDS = 300
LEAD_SLA_ESCALATION_INTERVAL_SECONDS = 3600
LEAD_SOFT_ARCHIVE_INTERVAL_SECONDS = 86400
SHOPIFY_RETENTION_INTERVAL_SECONDS = 86400
LEAD_AGENT_INTERVAL_SECONDS = 180
BLOG_SCHEDULE_INTERVAL_SECONDS = 60
DELIVERY_SLA_INTERVAL_SECONDS = 60
EVENT_BUS_BLOCK_MS = 1000
# Catch up Redis stream lag without waiting on empty BRPOP fan-out.
EVENT_BUS_BURST = 50
WORKER_MODES = ("all", "events", "queues", "routing")


def _load_local_api_env() -> None:
    """Load apps/api/.env when the worker is started from apps/worker (local).

    Production compose injects the same keys; existing process env wins.
    """
    env_path = Path(__file__).resolve().parents[1] / "api" / ".env"
    if not env_path.is_file():
        return
    try:
        from dotenv import load_dotenv

        load_dotenv(env_path, override=False)
    except Exception:
        logger.debug("local api env load skipped", exc_info=True)


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


def _consumer_name() -> str:
    return os.environ.get("WORKER_CONSUMER_NAME", "worker-1").strip() or "worker-1"


def parse_worker_mode(argv: list[str] | None = None) -> str:
    parser = argparse.ArgumentParser(prog="porterchain-worker")
    parser.add_argument(
        "--mode",
        choices=WORKER_MODES,
        default=(os.environ.get("WORKER_MODE") or "all").strip() or "all",
        help="events = bus only; queues = Redis queues + sweepers; routing = ROUTING queue only",
    )
    args = parser.parse_args(argv)
    return str(args.mode)


def mode_includes(mode: str, component: str) -> bool:
    if mode == "all":
        return True
    return mode == component


def _drain_event_bus(*, consumer_name: str, block_ms: int = EVENT_BUS_BLOCK_MS) -> int:
    from porterchain_event_bus import get_event_bus

    try:
        return get_event_bus().consume_once(consumer_name=consumer_name, block_ms=block_ms)
    except Exception:
        logger.exception("event bus consume failed — will retry")
        return 0


def _drain_event_bus_burst(*, consumer_name: str) -> int:
    """Block once for new work, then non-blocking burst to burn stream lag."""
    total = _drain_event_bus(consumer_name=consumer_name, block_ms=EVENT_BUS_BLOCK_MS)
    while total < EVENT_BUS_BURST:
        n = _drain_event_bus(consumer_name=consumer_name, block_ms=0)
        if not n:
            break
        total += n
    return total


def _drain_queues(publisher, *, timeout_seconds: int = 0, queues=None) -> int:
    from porterchain_shared.queue.names import QueueName
    from processors import process_queue_message

    processed = 0
    # Always non-blocking in mode=all — blocking per empty queue starved the event bus
    # (~8s+/loop) and left notification.queued / email-push stuck behind 30k lag.
    for queue in queues or list(QueueName):
        while True:
            msg = publisher.dequeue(queue, timeout_seconds=timeout_seconds)
            if not msg:
                break
            try:
                process_queue_message(msg)
                processed += 1
            except Exception:
                logger.exception("failed to process %s message %s", queue.value, msg.message_id)
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


def _drain_interac_inbox() -> int:
    """Read-only pull of Interac e-Transfer emails into the review queue (flagged)."""
    global _last_interac_inbox_at
    now = time.monotonic()
    if now - _last_interac_inbox_at < INTERAC_INBOX_INTERVAL_SECONDS:
        return 0
    _last_interac_inbox_at = now

    from porterchain_api.billing_engine.interac.imap_reader import fetch_and_ingest, imap_configured
    from porterchain_api.config import get_settings
    from porterchain_api.db import SessionLocal

    settings = get_settings()
    if not imap_configured(settings):
        return 0
    try:
        with SessionLocal() as db:
            result = fetch_and_ingest(db, settings)
    except Exception as exc:  # noqa: BLE001 - never log credentials
        logger.warning("interac inbox pull failed: %s", type(exc).__name__)
        return 0
    return int(result.get("queued", 0))


def _drain_billing_cycle() -> int:
    """Create due merchant cycle invoices (flag BILLING_CYCLE_AUTORUN_ENABLED). Idempotent."""
    global _last_billing_cycle_at
    now = time.monotonic()
    if now - _last_billing_cycle_at < BILLING_CYCLE_INTERVAL_SECONDS:
        return 0
    _last_billing_cycle_at = now

    from porterchain_api.config import get_settings

    if not get_settings().billing_cycle_autorun_enabled:
        return 0
    from porterchain_api.admin_engine.merchant_ar_service import MerchantArService
    from porterchain_api.db import SessionLocal

    with SessionLocal() as db:
        result = MerchantArService().run_due_cycles(db)
    if result.get("invoiced") or result.get("failed"):
        logger.info(
            "billing cycle run: processed=%s invoiced=%s failed=%s",
            result.get("processed", 0),
            result.get("invoiced", 0),
            result.get("failed", 0),
        )
    return int(result.get("invoiced", 0))


def _drain_finance_daily() -> int:
    """Daily, no sends: queue overdue reminder *drafts* for admin approval and purge
    Interac records past retention (7 years)."""
    global _last_finance_daily_at
    now = time.monotonic()
    if now - _last_finance_daily_at < FINANCE_DAILY_INTERVAL_SECONDS:
        return 0
    _last_finance_daily_at = now
    from porterchain_api.db import SessionLocal
    from porterchain_api.finance_ops.reminders import queue_drafts
    from porterchain_api.finance_ops.retention import purge_expired_interac

    with SessionLocal() as db:
        drafts = queue_drafts(db)
        purged = purge_expired_interac(db)
    if drafts.get("created") or purged.get("deleted"):
        logger.info("finance daily: drafts=%s purged=%s", drafts, purged)
    return int(drafts.get("created", 0))


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


def _drain_notification_retries() -> int:
    """Re-enqueue failed notifications whose next_retry_at is due."""
    global _last_notification_retry_at
    now = time.monotonic()
    if now - _last_notification_retry_at < NOTIFICATION_RETRY_INTERVAL_SECONDS:
        return 0
    _last_notification_retry_at = now

    from porterchain_api.db import SessionLocal
    from porterchain_api.notification_engine.retry_sweeper import sweep_notification_retries

    with SessionLocal() as db:
        result = sweep_notification_retries(db)
    if result.get("requeued") or result.get("due"):
        logger.info(
            "notification retry sweep: due=%s requeued=%s",
            result.get("due", 0),
            result.get("requeued", 0),
        )
    return int(result.get("requeued", 0))


def _drain_merchant_webhook_retries() -> int:
    """Re-POST failed merchant webhooks whose next_retry_at is due (no sleep)."""
    global _last_webhook_retry_at
    now = time.monotonic()
    if now - _last_webhook_retry_at < WEBHOOK_RETRY_INTERVAL_SECONDS:
        return 0
    _last_webhook_retry_at = now

    from porterchain_api.db import SessionLocal
    from porterchain_api.merchant_engine.webhook_retry_sweeper import sweep_merchant_webhook_retries

    with SessionLocal() as db:
        result = sweep_merchant_webhook_retries(db)
    if result.get("retried") or result.get("due"):
        logger.info(
            "merchant webhook retry sweep: due=%s retried=%s",
            result.get("due", 0),
            result.get("retried", 0),
        )
    return int(result.get("retried", 0))


def _drain_shopify_fulfillment_retries() -> int:
    """Re-push Shopify fulfillment/tracking whose sync_retry is due (backoff in metadata)."""
    global _last_shopify_sync_retry_at
    now = time.monotonic()
    if now - _last_shopify_sync_retry_at < WEBHOOK_RETRY_INTERVAL_SECONDS:
        return 0
    _last_shopify_sync_retry_at = now

    from porterchain_api.config import get_settings
    from porterchain_api.db import SessionLocal
    from porterchain_api.merchant_engine.shopify_fulfillment_ops import sweep_fulfillment_retries

    with SessionLocal() as db:
        result = sweep_fulfillment_retries(db, get_settings())
    if result.get("due"):
        logger.info(
            "shopify fulfillment retry sweep: due=%s retried=%s",
            result.get("due", 0),
            result.get("retried", 0),
        )
    return int(result.get("retried", 0))


def _drain_lead_nurture() -> int:
    """Send due D+1 nurture emails when marketing consent is present."""
    global _last_lead_nurture_at
    now = time.monotonic()
    if now - _last_lead_nurture_at < LEAD_NURTURE_INTERVAL_SECONDS:
        return 0
    _last_lead_nurture_at = now

    from porterchain_api.collaboration_engine.lead_nurture import process_due_nurture_emails
    from porterchain_api.db import SessionLocal

    with SessionLocal() as db:
        result = process_due_nurture_emails(db, limit=20)
    if result.get("sent") or result.get("due"):
        logger.info(
            "lead nurture sweep: due=%s sent=%s skipped=%s",
            result.get("due", 0),
            result.get("sent", 0),
            result.get("skipped", 0),
        )
    return int(result.get("sent", 0))


def _drain_lead_agent() -> int:
    """Zero-human welcome: enqueue intro email for consented NEW leads."""
    global _last_lead_agent_at
    now = time.monotonic()
    if now - _last_lead_agent_at < LEAD_AGENT_INTERVAL_SECONDS:
        return 0
    _last_lead_agent_at = now

    from porterchain_api.collaboration_engine.lead_agent import process_lead_agent_batch
    from porterchain_api.collaboration_engine.lead_enrich import process_lead_enrich_batch
    from porterchain_api.db import SessionLocal

    sent = 0
    with SessionLocal() as db:
        result = process_lead_agent_batch(db, limit=25)
        enrich = process_lead_enrich_batch(db, limit=15)
    if result.get("sent") or result.get("scanned"):
        logger.info(
            "lead agent sweep: scanned=%s sent=%s skipped=%s",
            result.get("scanned", 0),
            result.get("sent", 0),
            result.get("skipped", 0),
        )
    if enrich.get("found") or enrich.get("scanned"):
        logger.info(
            "lead enrich sweep: scanned=%s found=%s failed=%s skipped=%s",
            enrich.get("scanned", 0),
            enrich.get("found", 0),
            enrich.get("failed", 0),
            enrich.get("skipped", 0),
        )
    return int(result.get("sent", 0)) + int(enrich.get("found", 0))


def _drain_lead_sla_escalation() -> int:
    """Page growth staff for NEW leads past first-response SLA."""
    global _last_lead_sla_at
    now = time.monotonic()
    if now - _last_lead_sla_at < LEAD_SLA_ESCALATION_INTERVAL_SECONDS:
        return 0
    _last_lead_sla_at = now

    from porterchain_api.collaboration_engine.lead_ops import escalate_sla_breached_leads
    from porterchain_api.db import SessionLocal

    with SessionLocal() as db:
        result = escalate_sla_breached_leads(db, limit=25)
    if result.get("notified") or result.get("due"):
        logger.info(
            "lead sla escalation: due=%s notified=%s",
            result.get("due", 0),
            result.get("notified", 0),
        )
    return int(result.get("notified", 0))


def _drain_delivery_sla() -> int:
    """Emit order.delayed and sla.breached once when an open order misses its promise."""
    global _last_delivery_sla_at
    now = time.monotonic()
    if now - _last_delivery_sla_at < DELIVERY_SLA_INTERVAL_SECONDS:
        return 0
    _last_delivery_sla_at = now

    from porterchain_api.booking_engine.order_sla import publish_due_delivery_notices
    from porterchain_api.db import SessionLocal

    with SessionLocal() as db:
        result = publish_due_delivery_notices(db, limit=25)
    sent = int(result.get("delayed", 0)) + int(result.get("breached", 0))
    if sent:
        logger.info(
            "delivery sla notices: delayed=%s breached=%s",
            result.get("delayed", 0),
            result.get("breached", 0),
        )
    return sent


def _drain_lead_soft_archive() -> int:
    """Soft-archive inactive unconverted leads (~24 months)."""
    global _last_lead_archive_at
    now = time.monotonic()
    if now - _last_lead_archive_at < LEAD_SOFT_ARCHIVE_INTERVAL_SECONDS:
        return 0
    _last_lead_archive_at = now

    from porterchain_api.collaboration_engine.lead_retention import soft_archive_stale_leads
    from porterchain_api.db import SessionLocal

    with SessionLocal() as db:
        result = soft_archive_stale_leads(db, limit=100)
    if result.get("archived"):
        logger.info(
            "lead soft-archive: archived=%s skipped=%s scanned=%s",
            result.get("archived", 0),
            result.get("skipped", 0),
            result.get("scanned", 0),
        )
    return int(result.get("archived", 0))


def _drain_shopify_buyer_retention() -> int:
    """Wipe Shopify buyer contact 24 months after delivery."""
    global _last_shopify_retention_at
    now = time.monotonic()
    if now - _last_shopify_retention_at < SHOPIFY_RETENTION_INTERVAL_SECONDS:
        return 0
    _last_shopify_retention_at = now

    from porterchain_api.config import get_settings
    from porterchain_api.db import SessionLocal
    from porterchain_api.merchant_engine.shopify_privacy import run_retention

    with SessionLocal() as db:
        result = run_retention(db, get_settings())
    if result.get("wiped"):
        logger.info("shopify buyer retention: wiped=%s", result.get("wiped", 0))
    return int(result.get("wiped", 0))


def _drain_blog_scheduled_publish() -> int:
    """Publish drafts whose scheduled_publish_at has elapsed."""
    global _last_blog_schedule_at
    now = time.monotonic()
    if now - _last_blog_schedule_at < BLOG_SCHEDULE_INTERVAL_SECONDS:
        return 0
    _last_blog_schedule_at = now

    from porterchain_api.config import get_settings
    from porterchain_api.content_engine.blog_revalidate import notify_blog_revalidate
    from porterchain_api.content_engine.blog_service import BlogService
    from porterchain_api.db import SessionLocal

    settings = get_settings()
    with SessionLocal() as db:
        published = BlogService().publish_due_posts(db, limit=20)
    for record in published:
        notify_blog_revalidate(settings, locale=record.locale, slug=record.slug)
    if published:
        logger.info("blog scheduled publish: count=%s", len(published))
    return len(published)


def _drain_driver_compliance_expiry() -> int:
    """Revoke insurance/registration/license flags when document expiry lapses."""
    global _last_compliance_expiry_at
    now = time.monotonic()
    if now - _last_compliance_expiry_at < COMPLIANCE_EXPIRY_INTERVAL_SECONDS:
        return 0
    _last_compliance_expiry_at = now

    from porterchain_api.config import get_settings
    from porterchain_api.db import SessionLocal
    from porterchain_api.driver_engine.compliance_expiry_service import DriverComplianceExpiryService

    settings = get_settings()
    if not settings.driver_compliance_expiry_sweep_enabled:
        return 0

    with SessionLocal() as db:
        result = DriverComplianceExpiryService().sweep(db)
    if result.get("updated"):
        logger.info(
            "driver compliance expiry: scanned=%s updated=%s",
            result.get("scanned", 0),
            result.get("updated", 0),
        )
    return int(result.get("updated", 0))


def main(argv: list[str] | None = None) -> None:
    _load_local_api_env()
    from porterchain_api.platform.bus import ensure_handlers_registered
    from porterchain_shared.queue.names import QueueName
    from porterchain_shared.queue.publisher import get_queue_publisher
    from porterchain_shared.redis_health import require_redis_for_production

    require_redis_for_production()
    ensure_handlers_registered()

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    mode = parse_worker_mode(argv)
    publisher = get_queue_publisher()
    consumer_name = _consumer_name()
    logger.info(
        "worker started mode=%s — event bus consumer=%s; queues: %s",
        mode,
        consumer_name,
        ", ".join(q.value for q in QueueName),
    )

    while _running:
        try:
            processed = 0
            if mode_includes(mode, "events"):
                processed += _drain_event_bus_burst(consumer_name=consumer_name)
            if mode == "routing":
                from porterchain_shared.queue.names import QueueName as _QN

                processed += _drain_queues(
                    publisher,
                    timeout_seconds=0,
                    queues=[_QN.ROUTING],
                )
            elif mode_includes(mode, "queues"):
                processed += _drain_queues(publisher, timeout_seconds=0)
                processed += _drain_draft_reconciliation()
                processed += _drain_standing_orders()
                processed += _drain_interac_inbox()
                processed += _drain_billing_cycle()
                processed += _drain_finance_daily()
                processed += _drain_notification_retries()
                processed += _drain_merchant_webhook_retries()
                processed += _drain_shopify_fulfillment_retries()
                processed += _drain_driver_compliance_expiry()
                processed += _drain_lead_nurture()
                processed += _drain_lead_agent()
                processed += _drain_lead_sla_escalation()
                processed += _drain_delivery_sla()
                processed += _drain_lead_soft_archive()
                processed += _drain_shopify_buyer_retention()
                processed += _drain_blog_scheduled_publish()
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
