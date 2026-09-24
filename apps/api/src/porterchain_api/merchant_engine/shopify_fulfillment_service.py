"""Shopify fulfillment push + flag-gated FulfillmentService install hooks."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.config import Settings
from porterchain_api.domain.states import OrderSource
from porterchain_api.integrations.shopify_hmac import verify_webhook_hmac
from porterchain_api.booking_models import Order
from porterchain_api.merchant_models import ShopifyShop
from porterchain_api.merchant_engine.shopify_urls import (
    carrier_rates_url,
    fulfillment_service_url,
    normalize_shop_domain,
    webhook_url,
)

logger = logging.getLogger(__name__)


def _helpers():
    from porterchain_api.merchant_engine import shopify_service as shopify

    return shopify


def ingest_fulfillment_order_notification(
    db: Session,
    settings: Settings,
    *,
    raw_body: bytes,
    hmac_header: str | None,
    shop_domain_header: str | None,
) -> dict[str, Any]:
    """FulfillmentService callback URL — HMAC + enqueue; accept→book stays intentional hold."""
    if not settings.shopify_fulfillment_service_enabled:
        return {"ok": True, "ignored": True, "reason": "fo_flag_off"}

    shop_domain = normalize_shop_domain(shop_domain_header or "")
    shop = db.query(ShopifyShop).filter(ShopifyShop.shop_domain == shop_domain).first() if shop_domain else None
    secrets: list[str] = []
    if shop and shop.encrypted_webhook_secret:
        stored = _helpers()._decrypt(shop.encrypted_webhook_secret, settings)
        if stored:
            secrets.append(stored)
    if settings.shopify_api_secret:
        secrets.append(settings.shopify_api_secret)
    if not verify_webhook_hmac(raw_body, hmac_header, secrets):
        raise PermissionError("shopify_hmac_invalid")
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
                "action": "shopify_fo_request",
                "shop_domain": shop.shop_domain,
                "topic": "fulfillment_order_notification",
                "raw_body": raw_body.decode("utf-8"),
            },
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("shopify_fo_notification_enqueue_failed shop=%s", shop_domain)
        raise RuntimeError("shopify_enqueue_failed") from exc
    return {"ok": True, "queued": True, "action": "shopify_fo_request", "stub": True}



def push_fulfillment(db: Session, settings: Settings, order: Order) -> None:
    """Create or update Shopify fulfillment tracking for a PorterChain order.

    First call (no ``fulfillment_id`` yet) creates the fulfillment via FO line
    items. Later lifecycle events (picked up / in transit / delivered) update
    tracking only so the buyer sees mid-flight status — Stripe-like trust.
    """
    if order.order_source != OrderSource.SHOPIFY.value:
        return
    meta = (order.compliance_metadata or {}).get("shopify") or {}
    shop_domain = str(meta.get("shop_domain") or "")
    shopify_order_id = str(meta.get("order_id") or order.purchase_order_number or "")
    if not shop_domain or not shopify_order_id:
        return
    shop = _helpers()._active_shop(db, shop_domain)
    if not shop:
        return
    token = _helpers()._decrypt(shop.encrypted_access_token, settings)
    if not token:
        return
    tracking = order.tracking_number or ""
    tracking_url = (
        f"{settings.website_url.rstrip('/')}/track/{tracking}"
        if tracking
        else f"{settings.website_url.rstrip('/')}/track"
    )
    tracking_info = {
        "number": tracking,
        "url": tracking_url,
        "company": "PorterChain",
    }
    existing_fid = str(meta.get("fulfillment_id") or "").strip()
    if existing_fid:
        resp = _helpers()._admin_post(
            shop.shop_domain,
            token,
            f"/fulfillments/{existing_fid}/update_tracking.json",
            settings,
            {
                "fulfillment": {
                    "notify_customer": True,
                    "tracking_info": tracking_info,
                }
            },
        )
        if isinstance(resp, dict):
            extra = dict(order.compliance_metadata or {})
            shopify_meta = dict(extra.get("shopify") or {})
            shopify_meta["last_tracking_push_at"] = datetime.now(UTC).isoformat()
            shopify_meta["last_tracking_state"] = order.state
            extra["shopify"] = shopify_meta
            order.compliance_metadata = extra
            db.commit()
        return

    fo = _helpers()._admin_get(
        shop.shop_domain, token, f"/orders/{shopify_order_id}/fulfillment_orders.json", settings
    )
    fulfillment_orders = (fo or {}).get("fulfillment_orders") if isinstance(fo, dict) else None
    if not fulfillment_orders:
        logger.info("shopify_no_fulfillment_orders order=%s shopify=%s", order.id, shopify_order_id)
        return
    line_items = [{"fulfillment_order_id": item.get("id")} for item in fulfillment_orders if item.get("id")]
    resp = _helpers()._admin_post(
        shop.shop_domain,
        token,
        "/fulfillments.json",
        settings,
        {
            "fulfillment": {
                "line_items_by_fulfillment_order": line_items,
                "tracking_info": tracking_info,
                "notify_customer": True,
            }
        },
    )
    if isinstance(resp, dict):
        fulfillment = resp.get("fulfillment") if isinstance(resp.get("fulfillment"), dict) else {}
        fid = fulfillment.get("id") if fulfillment else None
        if fid:
            extra = dict(order.compliance_metadata or {})
            shopify_meta = dict(extra.get("shopify") or {})
            shopify_meta["fulfillment_id"] = str(fid)
            shopify_meta["last_tracking_push_at"] = datetime.now(UTC).isoformat()
            shopify_meta["last_tracking_state"] = order.state
            extra["shopify"] = shopify_meta
            order.compliance_metadata = extra
            db.commit()



def _post_install_hooks(shop: ShopifyShop, settings: Settings) -> None:
    try:
        _register_webhooks(shop, settings)
    except Exception:  # noqa: BLE001
        logger.warning(
            "shopify_webhook_register_failed shop=%s", shop.shop_domain, exc_info=True
        )
    try:
        _register_carrier_service(shop, settings)
    except Exception:  # noqa: BLE001
        logger.warning(
            "shopify_carrier_register_failed shop=%s", shop.shop_domain, exc_info=True
        )
    if settings.shopify_fulfillment_service_enabled:
        try:
            _register_fulfillment_service(shop, settings)
        except Exception:  # noqa: BLE001
            logger.warning(
                "shopify_fulfillment_service_register_failed shop=%s",
                shop.shop_domain,
                exc_info=True,
            )



def _register_webhooks(shop: ShopifyShop, settings: Settings) -> None:
    token = _helpers()._decrypt(shop.encrypted_access_token, settings)
    if not token:
        return
    address = webhook_url(settings)
    topics: list[str] = [
        "orders/create",
        "orders/cancelled",
        "app/uninstalled",
        "customers/data_request",
        "customers/redact",
        "shop/redact",
    ]
    if settings.shopify_fulfillment_service_enabled:
        topics.extend(
            [
                "fulfillment_orders/fulfillment_request_submitted",
                "fulfillment_orders/cancellation_request_submitted",
            ]
        )
    for topic in topics:
        _helpers()._admin_post(
            shop.shop_domain,
            token,
            "/webhooks.json",
            settings,
            {"webhook": {"topic": topic, "address": address, "format": "json"}},
        )



def _register_carrier_service(shop: ShopifyShop, settings: Settings) -> None:
    """Register Shopify CarrierService so checkout can call our rate callback."""
    token = _helpers()._decrypt(shop.encrypted_access_token, settings)
    if not token:
        return
    _helpers()._admin_post(
        shop.shop_domain,
        token,
        "/carrier_services.json",
        settings,
        {
            "carrier_service": {
                "name": "PorterChain",
                "callback_url": carrier_rates_url(settings),
                "service_discovery": True,
                "carrier_service_type": "api",
                "format": "json",
            }
        },
    )



def _register_fulfillment_service(shop: ShopifyShop, settings: Settings) -> None:
    """Register Shopify FulfillmentService (flag-gated). Accept→book still held."""
    token = _helpers()._decrypt(shop.encrypted_access_token, settings)
    if not token:
        return
    _helpers()._admin_post(
        shop.shop_domain,
        token,
        "/fulfillment_services.json",
        settings,
        {
            "fulfillment_service": {
                "name": "PorterChain",
                "callback_url": fulfillment_service_url(settings),
                "inventory_management": False,
                "tracking_support": True,
                "requires_shipping_method": False,
                "format": "json",
                "fulfillment_orders_opt_in": True,
            }
        },
    )
