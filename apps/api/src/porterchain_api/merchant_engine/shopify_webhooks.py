"""Shopify webhook ingress: verify, dedupe, route to the WEBHOOKS queue, and run queued jobs."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.config import Settings
from porterchain_api.integrations.shopify_hmac import verify_webhook_hmac
from porterchain_api.merchant_engine import shopify_tokens as tokens
from porterchain_api.merchant_engine.shopify_payload_ops import (
    _book_from_shopify_payload,
    _cancel_from_shopify_payload,
    _return_from_shopify_payload,
    _sync_fulfillment_order,
    _update_from_shopify_payload,
)
from porterchain_api.merchant_engine.shopify_service import _active_shop, _decrypt, _delete_partner_services
from porterchain_api.merchant_engine.shopify_urls import normalize_shop_domain
from porterchain_api.merchant_models import ShopifyShop

logger = logging.getLogger(__name__)

_GDPR_TOPICS = frozenset({"shop/redact", "customers/redact", "customers/data_request"})
_FO_REQUEST_TOPICS = {
    "fulfillment/orders/fulfillment/request/submitted",
    "fulfillment/orders/cancellation/request/submitted",
}
_FO_SYNC_TOPICS = {
    "fulfillment/orders/order/routing/complete",
    "fulfillment/orders/scheduled/fulfillment/order/ready",
    "fulfillment/orders/cancelled",
    "fulfillment/orders/placed/on/hold",
    "fulfillment/orders/hold/released",
    "fulfillment/orders/rescheduled",
    "fulfillment/orders/moved",
    "fulfillment/orders/split",
    "fulfillment/orders/merged",
}
_CREATE_TOPICS = {"orders/create", "orders/paid"}
_UPDATE_TOPICS = {"orders/updated", "orders/update", "orders/edited"}
_CANCEL_TOPICS = {"orders/cancelled", "orders/canceled", "orders/delete", "refunds/create"}


def _webhook_seen(shop: ShopifyShop, webhook_id: str | None) -> bool:
    if not webhook_id:
        return False
    seen = shop.seen_webhook_ids
    return isinstance(seen, list) and webhook_id in seen


def _remember_webhook(shop: ShopifyShop, webhook_id: str | None) -> None:
    if not webhook_id:
        return
    seen = list(shop.seen_webhook_ids) if isinstance(shop.seen_webhook_ids, list) else []
    if webhook_id in seen:
        return
    shop.seen_webhook_ids = [*seen, webhook_id][-200:]


def _action_for_topic(topic_name: str, *, fo_enabled: bool) -> tuple[str | None, dict[str, Any] | None]:
    """Return (action, early_result). early_result is set when we ack without a job."""
    if topic_name in _FO_REQUEST_TOPICS:
        if not fo_enabled:
            return None, {"ok": True, "ignored": topic_name, "reason": "fo_flag_off"}
        action = (
            "shopify_fo_request"
            if "fulfillment/request" in topic_name
            else "shopify_fo_cancel_request"
        )
        return action, None
    if topic_name in _FO_SYNC_TOPICS:
        return "shopify_fo_sync", None
    if topic_name in _CREATE_TOPICS:
        return "shopify_orders_create", None
    if topic_name in _UPDATE_TOPICS:
        return "shopify_orders_updated", None
    if topic_name in _CANCEL_TOPICS:
        return "shopify_orders_cancelled", None
    if topic_name == "returns/approve":
        return "shopify_return_approve", None
    if topic_name == "returns/cancel":
        return "shopify_return_cancel", None
    return None, {"ok": True, "ignored": topic_name}


def ingest_webhook(
    db: Session,
    settings: Settings,
    *,
    raw_body: bytes,
    hmac_header: str | None,
    shop_domain_header: str | None,
    topic: str | None,
    webhook_id: str | None = None,
) -> dict[str, Any]:
    """HMAC on the request path; book/cancel run on WEBHOOKS worker (Phase 4).

    Returns 200-worthy payload only after enqueue succeeds for order topics.
    Raises PermissionError on bad HMAC; RuntimeError('shopify_enqueue_failed') → 503.
    ``X-Shopify-Webhook-Id`` is remembered only after a successful enqueue so a
    failed enqueue can still be retried.
    """
    shop_domain = normalize_shop_domain(shop_domain_header or "")
    shop = db.query(ShopifyShop).filter(ShopifyShop.shop_domain == shop_domain).first() if shop_domain else None
    secrets = []
    if shop and shop.encrypted_webhook_secret:
        stored = _decrypt(shop.encrypted_webhook_secret, settings)
        if stored:
            secrets.append(stored)
    if settings.shopify_api_secret:
        secrets.append(settings.shopify_api_secret)
    if not verify_webhook_hmac(raw_body, hmac_header, secrets):
        raise PermissionError("shopify_hmac_invalid")
    if shop and _webhook_seen(shop, webhook_id):
        return {"ok": True, "duplicate": True}

    topic_name = (topic or "").strip().lower().replace("_", "/")
    if topic_name in _GDPR_TOPICS:
        from porterchain_api.merchant_engine.shopify_privacy import accept_and_enqueue

        def _remember_gdpr() -> None:
            if shop and webhook_id:
                _remember_webhook(shop, webhook_id)
                db.commit()

        return accept_and_enqueue(
            db,
            topic=topic_name,
            shop=shop,
            raw_body=raw_body,
            webhook_id=webhook_id,
            remember=_remember_gdpr,
        )
    if topic_name in {"app/uninstalled"}:
        if shop:
            _delete_partner_services(shop)
            shop.uninstalled_at = datetime.now(UTC)
            tokens.clear_tokens(shop)
            shop.carrier_service_gid = None
            shop.fulfillment_service_gid = None
            shop.location_gid = None
            _remember_webhook(shop, webhook_id)
            db.commit()
        return {"ok": True, "uninstalled": True}

    action, early = _action_for_topic(
        topic_name, fo_enabled=bool(settings.shopify_fulfillment_service_enabled)
    )
    if early is not None:
        if shop and webhook_id:
            _remember_webhook(shop, webhook_id)
            db.commit()
        return early
    if action is None:
        return {"ok": True, "ignored": topic_name}

    if not shop or shop.uninstalled_at is not None:
        raise LookupError("shop_not_connected")

    shop.last_webhook_at = datetime.now(UTC)
    db.commit()

    try:
        from porterchain_shared.queue.names import QueueName
        from porterchain_shared.queue.publisher import get_queue_publisher

        get_queue_publisher().enqueue(
            QueueName.WEBHOOKS,
            {
                "action": action,
                "shop_domain": shop.shop_domain,
                "topic": topic_name,
                "webhook_id": webhook_id,
                "raw_body": raw_body.decode("utf-8"),
            },
        )
    except Exception as exc:  # noqa: BLE001 — Shopify must not get 200 if job was dropped
        logger.exception("shopify_webhook_enqueue_failed shop=%s topic=%s", shop_domain, topic_name)
        raise RuntimeError("shopify_enqueue_failed") from exc
    _remember_webhook(shop, webhook_id)
    db.commit()
    return {"ok": True, "queued": True, "action": action}


def process_queued_webhook(db: Session, settings: Settings, payload: dict[str, Any]) -> dict[str, Any]:
    """Worker entry: create shipment or cancel from a queued Shopify webhook."""
    from porterchain_api.merchant_engine.shopify_ingress_dlq import (
        REASON_INGRESS_PAUSED,
        REASON_PAYLOAD,
        reason_from_exc,
        record_ingress_dlq,
    )

    action = payload.get("action")
    shop_domain = normalize_shop_domain(str(payload.get("shop_domain") or ""))
    topic = str(payload.get("topic") or "") or None
    raw = payload.get("raw_body") or "{}"
    if isinstance(raw, bytes):
        raw_text = raw.decode("utf-8")
    else:
        raw_text = str(raw)
    from_dlq = bool(payload.get("_from_dlq_replay"))

    try:
        body = json.loads(raw_text or "{}")
    except json.JSONDecodeError as exc:
        shop = _active_shop(db, shop_domain) or (
            db.query(ShopifyShop).filter(ShopifyShop.shop_domain == shop_domain).first()
        )
        if shop and not from_dlq:
            record_ingress_dlq(
                db,
                shop=shop,
                shop_domain=shop_domain,
                action=str(action or "unknown"),
                topic=topic,
                raw_body=raw_text,
                reason_code=REASON_PAYLOAD,
                detail=str(exc),
                status="open",
            )
        raise ValueError("payload_invalid") from exc
    if not isinstance(body, dict):
        raise ValueError("payload_invalid")

    shop = _active_shop(db, shop_domain)
    # A paused store holds every new booking it would create (orders and return pickups).
    if action in {"shopify_orders_create", "shopify_return_approve"} and shop and shop.ingress_paused:
        if not from_dlq:
            record_ingress_dlq(
                db,
                shop=shop,
                shop_domain=shop_domain,
                action=str(action),
                topic=topic,
                raw_body=raw_text,
                reason_code=REASON_INGRESS_PAUSED,
                detail="ingress_paused",
                status="held",
                payload=body,
            )
        return {"ok": True, "skipped": "ingress_paused", "held": True}

    try:
        if action == "shopify_orders_create":
            return _book_from_shopify_payload(db, settings, shop_domain=shop_domain, payload=body)
        if action == "shopify_orders_updated":
            return _update_from_shopify_payload(db, settings, shop_domain=shop_domain, payload=body)
        if action == "shopify_orders_cancelled":
            return _cancel_from_shopify_payload(db, settings, shop_domain=shop_domain, payload=body)
        if action in {"shopify_return_approve", "shopify_return_cancel"}:
            return _return_from_shopify_payload(
                db, settings, shop_domain=shop_domain, payload=body, action=str(action)
            )
        if action == "shopify_fo_sync":
            return _sync_fulfillment_order(
                db, settings, shop_domain=shop_domain, topic=topic, payload=body
            )
        if action in {"shopify_fo_request", "shopify_fo_cancel_request"}:
            if not settings.shopify_fulfillment_service_enabled:
                return {"ok": True, "skipped": "fo_flag_off", "action": action}
            from porterchain_api.merchant_engine.shopify_fulfillment_service import act_on_queued_fo

            return act_on_queued_fo(
                db,
                settings,
                shop_domain=shop_domain,
                action=str(action),
                body=body,
            )
        raise ValueError(f"unknown_shopify_action:{action}")
    except Exception as exc:  # noqa: BLE001 — persist DLQ then re-raise for worker visibility
        if action in {
            "shopify_orders_create",
            "shopify_orders_updated",
            "shopify_orders_cancelled",
            "shopify_return_approve",
        } and not from_dlq:
            shop_row = shop or db.query(ShopifyShop).filter(ShopifyShop.shop_domain == shop_domain).first()
            if shop_row:
                reason, detail = reason_from_exc(exc)
                try:
                    record_ingress_dlq(
                        db,
                        shop=shop_row,
                        shop_domain=shop_domain,
                        action=str(action),
                        topic=topic,
                        raw_body=raw_text,
                        reason_code=reason,
                        detail=detail,
                        status="open",
                        payload=body,
                    )
                except Exception:  # noqa: BLE001
                    logger.exception("shopify_dlq_record_failed shop=%s", shop_domain)
        raise
