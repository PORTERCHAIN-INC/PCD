"""Shopify fulfillment adapter.

Shopify definitions, kept as Shopify wrote them:

- Fulfillment: a shipment of one or more items, including the line items, tracking, and location.
- FulfillmentOrder: items fulfilled from the same location. deliveryMethod says shipping, pickup, or other.
- FulfillmentService: a third-party service that prepares and ships for the store. Creating one creates a Location.

PorterChain already has one order. Accept books that order. PICKED_UP creates the Shopify fulfillment.
Later states only add fulfillmentEventCreate. There is no second fulfillment root.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.config import Settings
from porterchain_api.domain.states import OrderSource, OrderState
from porterchain_api.integrations.shopify_hmac import verify_webhook_hmac
from porterchain_api.booking_models import Order
from porterchain_api.merchant_models import ShopifyShop
from porterchain_api.merchant_engine.shopify_urls import (
    carrier_rates_url,
    fulfillment_callback_prefix,
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
    """FulfillmentService callback. Shopify posts only kind; we enqueue accept or cancel."""
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

        kind = ""
        try:
            parsed = json.loads(raw_body.decode("utf-8") or "{}")
            if isinstance(parsed, dict):
                kind = str(parsed.get("kind") or "")
        except (UnicodeDecodeError, json.JSONDecodeError):
            kind = ""
        action = (
            "shopify_fo_cancel_request" if "CANCEL" in kind.upper() else "shopify_fo_request"
        )
        get_queue_publisher().enqueue(
            QueueName.WEBHOOKS,
            {
                "action": action,
                "shop_domain": shop.shop_domain,
                "topic": "fulfillment_order_notification",
                "raw_body": raw_body.decode("utf-8"),
            },
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("shopify_fo_notification_enqueue_failed shop=%s", shop_domain)
        raise RuntimeError("shopify_enqueue_failed") from exc
    return {"ok": True, "queued": True, "action": action}




from porterchain_api.merchant_engine.shopify_fulfillment_ops import (  # noqa: E402
    _order_payload_from_fo,
    _register_carrier_service,
    _register_fulfillment_service,
    _register_webhooks,
    _reject_reason,
    act_on_queued_fo,
    cancel_shopify_fulfillment,
    delete_partner_services,
    fulfillment_event_status,
    push_fulfillment,
    re_register_shop_hooks,
)


def _post_install_hooks(shop: ShopifyShop, settings: Settings) -> None:
    try:
        _register_webhooks(shop, settings)
    except Exception:  # noqa: BLE001
        logger.warning("shopify_webhook_register_failed shop=%s", shop.shop_domain, exc_info=True)
    try:
        _register_carrier_service(shop, settings)
    except Exception:  # noqa: BLE001
        logger.warning("shopify_carrier_register_failed shop=%s", shop.shop_domain, exc_info=True)
    if settings.shopify_fulfillment_service_enabled:
        try:
            _register_fulfillment_service(shop, settings)
        except Exception:  # noqa: BLE001
            logger.warning(
                "shopify_fulfillment_service_register_failed shop=%s",
                shop.shop_domain,
                exc_info=True,
            )
