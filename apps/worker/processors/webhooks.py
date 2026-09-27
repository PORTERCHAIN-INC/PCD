"""Webhook fan-out queue — merchant callbacks and ingress retries."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def process_webhook(payload: dict[str, Any]) -> None:
    source = payload.get("source")
    action = payload.get("action")
    if action == "lead_ingest":
        from porterchain_api.collaboration_engine.lead_ingest_jobs import (
            process_queued_lead_ingest,
        )

        result = process_queued_lead_ingest(payload)
        logger.info("lead_ingest_queued_done %s", result)
        return
    if action == "merchant_fanout":
        from porterchain_api.merchant_engine.webhook_delivery_service import deliver_merchant_fanout

        deliver_merchant_fanout(payload)
        return
    if action == "shopify_fulfillment":
        _shopify_fulfillment(payload.get("order_id"), payload.get("event_type"))
        return
    if action == "shopify_fulfillment_cancel":
        _shopify_fulfillment_cancel(payload.get("order_id"))
        return
    if isinstance(action, str) and action.startswith("shopify_"):
        _shopify_ingress(payload)
        return
    if source == "fleetbase":
        logger.info("webhook ingress ack: fleetbase order=%s", payload.get("update", {}).get("porterchain_order_id"))
        return
    logger.info("webhook processed: keys=%s", list(payload.keys()))


def _shopify_ingress(payload: dict[str, Any]) -> None:
    from porterchain_api.config import get_settings
    from porterchain_api.db import SessionLocal
    from porterchain_api.merchant_engine.shopify_service import process_queued_webhook

    db = SessionLocal()
    try:
        result = process_queued_webhook(db, get_settings(), payload)
        logger.info("shopify_ingress_done action=%s result=%s", payload.get("action"), result)
    except Exception:
        logger.exception("shopify_ingress_failed action=%s", payload.get("action"))
        db.rollback()
        # Re-raise so WEBHOOKS queue retry/DLQ can fire — silent success drops shipments.
        raise
    finally:
        db.close()


def _shopify_fulfillment(order_id: str | None, event_type: str | None = None) -> None:
    if not order_id:
        logger.warning("shopify_fulfillment missing order_id")
        return
    from porterchain_api.config import get_settings
    from porterchain_api.db import SessionLocal
    from porterchain_api.merchant_engine.shopify_service import push_fulfillment
    from porterchain_api.booking_models import Order

    db = SessionLocal()
    try:
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            logger.warning("shopify_fulfillment: order %s not found", order_id)
            return
        push_fulfillment(db, get_settings(), order, event_type=event_type)
    except Exception:  # noqa: BLE001
        logger.exception("shopify_fulfillment_push_failed order=%s", order_id)
    finally:
        db.close()


def _shopify_fulfillment_cancel(order_id: str | None) -> None:
    if not order_id:
        return
    from porterchain_api.config import get_settings
    from porterchain_api.db import SessionLocal
    from porterchain_api.merchant_engine.shopify_fulfillment_service import cancel_shopify_fulfillment
    from porterchain_api.booking_models import Order

    db = SessionLocal()
    try:
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            return
        cancel_shopify_fulfillment(db, get_settings(), order)
    except Exception:  # noqa: BLE001
        logger.exception("shopify_fulfillment_cancel_failed order=%s", order_id)
    finally:
        db.close()
