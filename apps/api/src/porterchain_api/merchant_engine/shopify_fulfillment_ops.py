"""Shopify fulfillment register, push, and accept. Re-exported by shopify_fulfillment_service."""

from __future__ import annotations

import logging
import re
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.booking_models import Order
from porterchain_api.config import Settings
from porterchain_api.domain.states import OrderSource, OrderState
from porterchain_api.merchant_models import Merchant, ShopifyShop
from porterchain_api.merchant_engine.shopify_tokens import (
    TOKEN_REAUTH_REQUIRED,
    access_token_for,
    is_token_rejection,
    mark_reauth_required,
    no_token_code,
)
from porterchain_api.merchant_engine.shopify_urls import (
    carrier_rates_url,
    fulfillment_callback_prefix,
    webhook_url,
)

logger = logging.getLogger(__name__)


def _helpers():
    from porterchain_api.merchant_engine import shopify_service as shopify

    return shopify


_CREATE_FULFILLMENT_STATES = {
    OrderState.PICKED_UP.value,
    OrderState.IN_TRANSIT.value,
    OrderState.AT_DESTINATION.value,
    OrderState.DELIVERED.value,
    OrderState.POD_COMPLETED.value,
}


def fulfillment_event_status(state: str, event_type: str | None = None) -> str | None:
    """Mirror our order state onto Shopify FulfillmentEventStatus.

    The Shopify fulfillment record is created at PICKED_UP, so CONFIRMED is not
    sent before that shipment exists. DRIVER_EN_ROUTE and AT_PICKUP are still
    pre-pickup and map to CONFIRMED once a fulfillment id is present.
    """
    if event_type in {"order.delayed", "sla.breached"}:
        return "DELAYED"
    if event_type == "exception.opened":
        return "ATTEMPTED_DELIVERY"
    if event_type in {"order.failed", "order.delivery_failed"}:
        return "FAILURE"
    return {
        "BOOKED": "CONFIRMED",
        "DISPATCH_READY": "CONFIRMED",
        "DRIVER_ASSIGNED": "CONFIRMED",
        "DRIVER_ACCEPTED": "CONFIRMED",
        "DRIVER_EN_ROUTE": "CONFIRMED",
        "AT_PICKUP": "CONFIRMED",
        "PICKED_UP": "CARRIER_PICKED_UP",
        # Same-day last mile: once moving to the buyer it is out for delivery.
        "IN_TRANSIT": "OUT_FOR_DELIVERY",
        "AT_DESTINATION": "OUT_FOR_DELIVERY",
        "DELIVERED": "DELIVERED",
        "POD_COMPLETED": "DELIVERED",
        "FAILED": "FAILURE",
    }.get(state)


def push_fulfillment(
    db: Session, settings: Settings, order: Order, *, event_type: str | None = None
) -> None:
    """Create or update Shopify fulfillment tracking for a PorterChain order.

    First call (no ``fulfillment_id`` yet) creates the fulfillment via FO line
    items. Later lifecycle events (picked up / in transit / delivered) update
    tracking only so the buyer sees mid-flight status — Stripe-like trust.
    Silent no-ops persist ``last_fulfillment_error`` so admin can see why.
    """
    if order.order_source != OrderSource.SHOPIFY.value:
        return

    def _record_error(code: str) -> None:
        extra = dict(order.compliance_metadata or {})
        shopify_meta = dict(extra.get("shopify") or {})
        shopify_meta["last_fulfillment_error"] = code
        shopify_meta["last_fulfillment_error_at"] = datetime.now(UTC).isoformat()
        schedule_sync_retry(shopify_meta, code, event_type)
        extra["shopify"] = shopify_meta
        order.compliance_metadata = extra
        db.commit()

    meta = (order.compliance_metadata or {}).get("shopify") or {}
    shop_domain = str(meta.get("shop_domain") or "")
    shopify_order_id = str(meta.get("order_id") or order.purchase_order_number or "")
    if not shop_domain or not shopify_order_id:
        _record_error("missing_shopify_ids")
        return
    shop = _helpers()._active_shop(db, shop_domain)
    if not shop:
        _record_error("shop_not_connected")
        return
    token = access_token_for(shop, settings)
    if not token:
        _record_error("missing_access_token")
        return
    tracking = order.tracking_number or ""
    tracking_url = public_tracking_url(settings, tracking)
    tracking_info = {
        "number": tracking,
        "url": tracking_url,
        "company": "PorterChain",
    }
    existing_fid = str(meta.get("fulfillment_id") or "").strip()
    if not existing_fid and order.state not in _CREATE_FULFILLMENT_STATES:
        return
    if existing_fid:
        if not _push_tracking(
            shop, token, settings, fulfillment_id=existing_fid, tracking_info=tracking_info
        ):
            _record_error("update_tracking_failed")
            return
        _mark_tracking_pushed(db, order, event_type=event_type, shop=shop, token=token, settings=settings)
        _push_reverse_tracking(shop, token, settings, order, tracking_info)
        return

    assigned = str(meta.get("fulfillment_order_id") or "").strip()
    if assigned:
        created = _create_fulfillment_graphql(
            shop, token, settings, fulfillment_order_id=assigned, tracking_info=tracking_info
        )
        if created:
            _store_fulfillment_id(
                db, order, created, event_type=event_type, shop=shop, token=token, settings=settings
            )
            return
    fo = _helpers()._admin_get(
        shop.shop_domain, token, f"/orders/{shopify_order_id}/fulfillment_orders.json", settings
    )
    fulfillment_orders = (fo or {}).get("fulfillment_orders") if isinstance(fo, dict) else None
    if not fulfillment_orders:
        logger.info("shopify_no_fulfillment_orders order=%s shopify=%s", order.id, shopify_order_id)
        _record_error("no_fulfillment_orders")
        return
    if assigned:
        assigned_num = assigned.rsplit("/", 1)[-1]
        line_items = [
            {"fulfillment_order_id": item.get("id")}
            for item in fulfillment_orders
            if item.get("id") and str(item.get("id")).rsplit("/", 1)[-1] == assigned_num
        ]
        if not line_items:
            line_items = [{"fulfillment_order_id": assigned_num}]
    else:
        line_items = [
            {"fulfillment_order_id": item.get("id")} for item in fulfillment_orders if item.get("id")
        ]
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
            shopify_meta.pop("last_fulfillment_error", None)
            shopify_meta.pop("last_fulfillment_error_at", None)
            shopify_meta.pop("sync_retry", None)
            extra["shopify"] = shopify_meta
            order.compliance_metadata = extra
            db.commit()
            _emit_fulfillment_event(db, settings, order, shop, token, event_type=event_type)
            return
        _record_error("fulfillment_create_no_id")
        return
    _record_error("fulfillment_create_failed")


def re_register_shop_hooks(shop: ShopifyShop, settings: Settings) -> dict[str, Any]:
    """Admin heal: re-run webhook + carrier (+ FO if flag) registration."""
    errors: list[str] = []
    carrier_error: str | None = None
    try:
        _register_webhooks(shop, settings)
    except Exception as exc:  # noqa: BLE001
        logger.warning("shopify_webhook_reregister_failed shop=%s", shop.shop_domain, exc_info=True)
        errors.append(f"webhooks:{exc}")
    try:
        _register_carrier_service(shop, settings)
    except Exception as exc:  # noqa: BLE001
        logger.warning("shopify_carrier_reregister_failed shop=%s", shop.shop_domain, exc_info=True)
        errors.append(f"carrier:{exc}")
        carrier_error = carrier_error_code(exc)
    if settings.shopify_fulfillment_service_enabled:
        try:
            _register_fulfillment_service(shop, settings)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "shopify_fulfillment_service_reregister_failed shop=%s",
                shop.shop_domain,
                exc_info=True,
            )
            errors.append(f"fulfillment_service:{exc}")
    return {
        "shop_id": shop.id,
        "shop_domain": shop.shop_domain,
        "ok": not errors,
        "errors": errors,
        "carrier_registered": bool(getattr(shop, "carrier_service_gid", None)),
        "carrier_error": carrier_error,
    }


def _register_webhooks(shop: ShopifyShop, settings: Settings) -> None:
    token = access_token_for(shop, settings)
    if not token:
        raise RuntimeError("webhook_register_failed:no_token")
    address = webhook_url(settings)
    topics: list[str] = [
        "orders/create",
        "orders/updated",
        "orders/edited",
        "orders/paid",
        "orders/cancelled",
        "orders/delete",
        "refunds/create",
        "app/uninstalled",
        "customers/data_request",
        "customers/redact",
        "shop/redact",
        "fulfillment_orders/cancelled",
        "fulfillment_orders/placed_on_hold",
        "fulfillment_orders/hold_released",
        "fulfillment_orders/rescheduled",
        "fulfillment_orders/moved",
        "fulfillment_orders/split",
        "fulfillment_orders/merged",
        "fulfillment_orders/order_routing_complete",
        "fulfillment_orders/scheduled_fulfillment_order_ready",
    ]
    if settings.shopify_fulfillment_service_enabled:
        topics.extend(
            [
                "fulfillment_orders/fulfillment_request_submitted",
                "fulfillment_orders/cancellation_request_submitted",
            ]
        )
    listed = _helpers()._admin_get(shop.shop_domain, token, "/webhooks.json", settings) or {}
    already: set[str] = set()
    for hook in listed.get("webhooks") or []:
        if isinstance(hook, dict) and hook.get("address") == address:
            already.add(str(hook.get("topic") or ""))
    failed: list[str] = []
    for topic in topics:
        if topic in already:
            continue
        result = _helpers()._admin_post(
            shop.shop_domain,
            token,
            "/webhooks.json",
            settings,
            {"webhook": {"topic": topic, "address": address, "format": "json"}},
        )
        if result is None:
            failed.append(topic)
    failed.extend(_register_returns_webhooks(shop, settings, token, address))
    if failed:
        raise RuntimeError("webhook_register_failed:" + ",".join(failed[:5]))


#: Return webhooks exist only in the GraphQL Admin API and need read_returns.
RETURNS_WEBHOOK_TOPICS = ("RETURNS_APPROVE", "RETURNS_CANCEL")


def _register_returns_webhooks(
    shop: ShopifyShop, settings: Settings, token: str, address: str
) -> list[str]:
    """Subscribe returns/* when the shop granted read_returns; silent skip otherwise."""
    from porterchain_api.merchant_engine.shopify_urls import has_returns_scope

    if not has_returns_scope(getattr(shop, "scopes", None)):
        return []
    try:
        from porterchain_api.merchant_engine.shopify_admin_graphql import webhook_subscriptions_ensure

        webhook_subscriptions_ensure(
            shop.shop_domain, token, settings, topics=list(RETURNS_WEBHOOK_TOPICS), uri=address
        )
    except Exception:  # noqa: BLE001
        logger.warning("shopify_returns_webhooks_failed shop=%s", shop.shop_domain)
        return ["returns/approve"]
    return []



def _persist_shop(shop: ShopifyShop) -> None:
    from sqlalchemy.orm import object_session

    sess = object_session(shop)
    if sess is not None:
        sess.add(shop)
        sess.commit()


# Why Shopify refused the CarrierService. The portal turns these into merchant copy.
CARRIER_NO_TOKEN = "carrier_no_token"
CARRIER_SCOPE_MISSING = "carrier_scope_missing"
CARRIER_PLAN_UNSUPPORTED = "carrier_plan_unsupported"
CARRIER_REGISTER_FAILED = "carrier_register_failed"
_CARRIER_CODES = (CARRIER_NO_TOKEN, CARRIER_SCOPE_MISSING, CARRIER_PLAN_UNSUPPORTED)


def carrier_error_code(exc: BaseException | str | None) -> str:
    """Map a registration failure to one stable code (never raw Shopify text).

    A refused token (403 "Non-expiring access tokens are no longer accepted", or 401)
    is ``token_reauth_required``, not a missing scope: only a new grant fixes it.
    """
    text = str(exc or "")
    if is_token_rejection(text):
        return TOKEN_REAUTH_REQUIRED
    for code in _CARRIER_CODES:
        if code in text:
            return code
    lowered = text.lower()
    if "access_denied" in lowered or "write_shipping" in lowered or "http_403" in lowered:
        return CARRIER_SCOPE_MISSING
    if (
        "carrier calculated" in lowered
        or "carrier-calculated" in lowered
        or "calculated shipping" in lowered
        or re.search(r"\bplan\b", lowered)
    ):
        return CARRIER_PLAN_UNSUPPORTED
    return CARRIER_REGISTER_FAILED


def _register_carrier_service(shop: ShopifyShop, settings: Settings) -> str:
    """Register (or re-activate) the Shopify CarrierService checkout calls for rates.

    Returns the stored id. Raises ``RuntimeError("carrier_register_failed:<code>")``
    when Shopify refuses, so install and the portal can say rates are not live.
    """
    token = access_token_for(shop, settings)
    if not token:
        raise RuntimeError(f"{CARRIER_REGISTER_FAILED}:{no_token_code(shop, CARRIER_NO_TOKEN)}")
    from porterchain_api.merchant_engine.shopify_admin_graphql import (
        carrier_service_create,
        carrier_service_find,
        carrier_service_update,
    )

    callback = carrier_rates_url(settings)
    existing = shop.carrier_service_gid if isinstance(shop.carrier_service_gid, str) else ""
    reasons: list[str] = []

    def _save(gid: str) -> str:
        shop.carrier_service_gid = gid
        _persist_shop(shop)
        logger.info("shopify_carrier_registered shop=%s", shop.shop_domain)
        return gid

    if existing:
        try:
            return _save(
                carrier_service_update(
                    shop.shop_domain, token, settings, service_id=existing, callback_url=callback
                )
            )
        except Exception as exc:  # noqa: BLE001 — stale id: fall through to create
            reasons.append(f"update:{exc}")
    try:
        return _save(carrier_service_create(shop.shop_domain, token, settings, callback_url=callback))
    except Exception as exc:  # noqa: BLE001
        reasons.append(f"create:{exc}")
    # A service from an earlier install can still be on the store ("already configured").
    try:
        found = carrier_service_find(shop.shop_domain, token, settings, callback_url=callback)
        if found:
            return _save(
                carrier_service_update(
                    shop.shop_domain, token, settings, service_id=found, callback_url=callback
                )
            )
    except Exception as exc:  # noqa: BLE001
        reasons.append(f"find:{exc}")
    resp = _helpers()._admin_post(
        shop.shop_domain,
        token,
        "/carrier_services.json",
        settings,
        {
            "carrier_service": {
                "name": "PorterChain",
                "callback_url": callback,
                "service_discovery": True,
                "carrier_service_type": "api",
                "format": "json",
                "active": True,
            }
        },
    )
    service = resp.get("carrier_service") if isinstance(resp, dict) else None
    if isinstance(service, dict) and service.get("id"):
        return _save(str(service["id"]))
    code = carrier_error_code(" | ".join(reasons))
    granted = str(getattr(shop, "scopes", "") or "")
    if code == CARRIER_REGISTER_FAILED and granted and "write_shipping" not in granted:
        code = CARRIER_SCOPE_MISSING
    if existing and code != TOKEN_REAUTH_REQUIRED:
        # The old id did not update and nothing replaced it: do not report rates as live.
        shop.carrier_service_gid = None
        _persist_shop(shop)
    if code == TOKEN_REAUTH_REQUIRED:
        mark_reauth_required(shop, "carrier_token_refused")
    logger.warning(
        "shopify_carrier_register_failed shop=%s code=%s reasons=%s",
        shop.shop_domain,
        code,
        " | ".join(reasons)[:500],
    )
    raise RuntimeError(f"{CARRIER_REGISTER_FAILED}:{code}")


def _register_fulfillment_service(shop: ShopifyShop, settings: Settings) -> None:
    """Register FulfillmentService. Callback prefix lets Shopify append the notification path."""
    token = access_token_for(shop, settings)
    if not token:
        return
    callback = fulfillment_callback_prefix(settings)
    existing = shop.fulfillment_service_gid if isinstance(shop.fulfillment_service_gid, str) else ""
    try:
        from porterchain_api.merchant_engine.shopify_admin_graphql import (
            ShopifyAdminError,
            fulfillment_service_create,
            fulfillment_service_update,
        )

        if existing:
            shop.fulfillment_service_gid = fulfillment_service_update(
                shop.shop_domain,
                token,
                settings,
                service_id=existing,
                callback_url=callback,
            )
            _persist_shop(shop)
            return
        service_id, location_id = fulfillment_service_create(
            shop.shop_domain, token, settings, callback_url=callback
        )
        shop.fulfillment_service_gid = service_id
        if location_id:
            shop.location_gid = location_id
        _persist_shop(shop)
        _edit_location(shop, settings, token)
        return
    except ShopifyAdminError:
        logger.info("shopify_fs_graphql_fallback shop=%s", shop.shop_domain)
    except Exception:  # noqa: BLE001
        logger.info("shopify_fs_graphql_fallback shop=%s", shop.shop_domain, exc_info=True)
    resp = _helpers()._admin_post(
        shop.shop_domain,
        token,
        "/fulfillment_services.json",
        settings,
        {
            "fulfillment_service": {
                "name": "PorterChain",
                "callback_url": callback,
                "inventory_management": False,
                "tracking_support": True,
                "requires_shipping_method": False,
                "format": "json",
                "fulfillment_orders_opt_in": True,
            }
        },
    )
    service = resp.get("fulfillment_service") if isinstance(resp, dict) else None
    if isinstance(service, dict) and service.get("id"):
        shop.fulfillment_service_gid = str(service["id"])
        if service.get("location_id"):
            shop.location_gid = str(service["location_id"])
        _persist_shop(shop)
        return
    listed = _helpers()._admin_get(shop.shop_domain, token, "/fulfillment_services.json", settings) or {}
    for row in listed.get("fulfillment_services") or []:
        if not isinstance(row, dict) or str(row.get("name") or "") != "PorterChain" or not row.get("id"):
            continue
        shop.fulfillment_service_gid = str(row["id"])
        if row.get("location_id"):
            shop.location_gid = str(row["location_id"])
        _persist_shop(shop)
        _edit_location(shop, settings, token)
        return
    raise RuntimeError("fulfillment_service_register_failed")


def _edit_location(shop: ShopifyShop, settings: Settings, token: str) -> None:
    location_id = str(shop.location_gid or "").strip()
    if not location_id:
        return
    from sqlalchemy.orm import object_session

    sess = object_session(shop)
    if sess is None:
        return
    from porterchain_api.merchant_engine.shopify_service import default_pickup_address

    addr = default_pickup_address(sess, shop.merchant_id, shop=shop)
    if addr is None:
        return
    try:
        from porterchain_api.merchant_engine.shopify_admin_graphql import location_edit

        location_edit(
            shop.shop_domain,
            token,
            settings,
            location_id=location_id,
            address={
                "address1": str(getattr(addr, "line1", None) or addr.formatted or "")[:255],
                "city": str(getattr(addr, "city", None) or ""),
                "provinceCode": str(getattr(addr, "province", None) or "ON"),
                "zip": str(getattr(addr, "postal", None) or ""),
                "countryCode": "CA",
            },
        )
    except Exception:  # noqa: BLE001
        logger.info("shopify_location_edit_skipped shop=%s", shop.shop_domain)


def _coord(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _push_tracking(
    shop: ShopifyShop,
    token: str,
    settings: Settings,
    *,
    fulfillment_id: str,
    tracking_info: dict[str, str],
) -> bool:
    try:
        from porterchain_api.merchant_engine.shopify_admin_graphql import (
            ShopifyAdminError,
            fulfillment_tracking_update,
        )

        fulfillment_tracking_update(
            shop.shop_domain,
            token,
            settings,
            fulfillment_id=fulfillment_id,
            tracking=tracking_info,
            notify_customer=True,
        )
        return True
    except ShopifyAdminError:
        logger.info("shopify_tracking_graphql_fallback shop=%s", shop.shop_domain)
    except Exception:  # noqa: BLE001
        logger.info("shopify_tracking_graphql_fallback shop=%s", shop.shop_domain, exc_info=True)
    resp = _helpers()._admin_post(
        shop.shop_domain,
        token,
        f"/fulfillments/{fulfillment_id.rsplit('/', 1)[-1]}/update_tracking.json",
        settings,
        {"fulfillment": {"notify_customer": True, "tracking_info": tracking_info}},
    )
    return isinstance(resp, dict)


def _create_fulfillment_graphql(
    shop: ShopifyShop,
    token: str,
    settings: Settings,
    *,
    fulfillment_order_id: str,
    tracking_info: dict[str, str],
) -> str | None:
    try:
        from porterchain_api.merchant_engine.shopify_admin_graphql import fulfillment_create

        return fulfillment_create(
            shop.shop_domain,
            token,
            settings,
            fulfillment_order_id=fulfillment_order_id,
            tracking=tracking_info,
            notify_customer=True,
        )
    except Exception:  # noqa: BLE001
        logger.info("shopify_fulfillment_graphql_fallback shop=%s", shop.shop_domain)
        return None


def _mark_tracking_pushed(
    db: Session,
    order: Order,
    *,
    event_type: str | None,
    shop: ShopifyShop,
    token: str,
    settings: Settings,
) -> None:
    extra = dict(order.compliance_metadata or {})
    shopify_meta = dict(extra.get("shopify") or {})
    shopify_meta["last_tracking_push_at"] = datetime.now(UTC).isoformat()
    shopify_meta["last_tracking_state"] = order.state
    shopify_meta.pop("last_fulfillment_error", None)
    shopify_meta.pop("last_fulfillment_error_at", None)
    shopify_meta.pop("sync_retry", None)
    extra["shopify"] = shopify_meta
    order.compliance_metadata = extra
    db.commit()
    _emit_fulfillment_event(db, settings, order, shop, token, event_type=event_type)


def _store_fulfillment_id(
    db: Session,
    order: Order,
    fulfillment_id: str,
    *,
    event_type: str | None,
    shop: ShopifyShop,
    token: str,
    settings: Settings,
) -> None:
    extra = dict(order.compliance_metadata or {})
    shopify_meta = dict(extra.get("shopify") or {})
    shopify_meta["fulfillment_id"] = fulfillment_id
    extra["shopify"] = shopify_meta
    order.compliance_metadata = extra
    db.commit()
    _mark_tracking_pushed(
        db, order, event_type=event_type, shop=shop, token=token, settings=settings
    )


def _push_reverse_tracking(
    shop: ShopifyShop,
    token: str,
    settings: Settings,
    order: Order,
    tracking_info: dict[str, str],
) -> None:
    meta = (order.compliance_metadata or {}).get("shopify") or {}
    reverse_id = str(meta.get("reverse_delivery_id") or "").strip()
    if not reverse_id:
        return
    try:
        from porterchain_api.merchant_engine.shopify_admin_graphql import reverse_delivery_shipping_update

        reverse_delivery_shipping_update(
            shop.shop_domain,
            token,
            settings,
            reverse_delivery_id=reverse_id,
            tracking=tracking_info,
        )
    except Exception:  # noqa: BLE001
        logger.info("shopify_reverse_tracking_skipped order=%s", order.id)


def _emit_fulfillment_event(
    db: Session,
    settings: Settings,
    order: Order,
    shop: ShopifyShop,
    token: str,
    *,
    event_type: str | None,
) -> None:
    del db
    meta = (order.compliance_metadata or {}).get("shopify") or {}
    fulfillment_id = str(meta.get("fulfillment_id") or "").strip()
    status = fulfillment_event_status(order.state, event_type)
    if not fulfillment_id or not status:
        return
    pushed = [str(x) for x in (meta.get("pushed_event_statuses") or []) if x]
    if status in pushed and status not in _REPEATABLE_EVENT_STATUSES:
        # Idempotent: a replayed lifecycle event must not stack duplicate buyer updates.
        return
    try:
        from porterchain_api.merchant_engine.shopify_admin_graphql import fulfillment_event_create

        dropoff = order.dropoff if isinstance(order.dropoff, dict) else {}
        lat = _coord(dropoff.get("lat"))
        lng = _coord(dropoff.get("lng"))
        fulfillment_event_create(
            shop.shop_domain,
            token,
            settings,
            fulfillment_id=fulfillment_id,
            status=status,
            happened_at=datetime.now(UTC).isoformat(),
            message=status.replace("_", " ").title(),
            latitude=lat,
            longitude=lng,
        )
        extra = dict(order.compliance_metadata or {})
        shopify_meta = dict(extra.get("shopify") or {})
        shopify_meta["last_event_status"] = status
        shopify_meta["last_event_at"] = datetime.now(UTC).isoformat()
        shopify_meta["pushed_event_statuses"] = [*pushed, status][-20:]
        shopify_meta.pop("sync_retry", None)
        extra["shopify"] = shopify_meta
        order.compliance_metadata = extra
        from sqlalchemy.orm import object_session

        sess = object_session(order)
        if sess is not None:
            sess.commit()
    except Exception:  # noqa: BLE001
        logger.warning("shopify_fulfillment_event_failed order=%s status=%s", order.id, status)
        _record_event_failure(order, event_type)


def _record_event_failure(order: Order, event_type: str | None) -> None:
    from sqlalchemy.orm import object_session

    extra = dict(order.compliance_metadata or {})
    shopify_meta = dict(extra.get("shopify") or {})
    shopify_meta["last_fulfillment_error"] = "event_push_failed"
    shopify_meta["last_fulfillment_error_at"] = datetime.now(UTC).isoformat()
    schedule_sync_retry(shopify_meta, "event_push_failed", event_type)
    extra["shopify"] = shopify_meta
    order.compliance_metadata = extra
    sess = object_session(order)
    if sess is not None:
        try:
            sess.commit()
        except Exception:  # noqa: BLE001
            sess.rollback()


# ------------------------------------------------------------------ #
# Reliable sync: retry with backoff, swept by the worker every minute.
# ------------------------------------------------------------------ #

#: Buyer-visible statuses that may legitimately repeat (a second failed attempt, a new delay).
_REPEATABLE_EVENT_STATUSES = frozenset({"ATTEMPTED_DELIVERY", "DELAYED"})
#: Transient errors worth retrying. Missing ids / disconnected shop are not.
RETRYABLE_SYNC_ERRORS = frozenset(
    {
        "update_tracking_failed",
        "fulfillment_create_failed",
        "fulfillment_create_no_id",
        "no_fulfillment_orders",
        "missing_access_token",
        "event_push_failed",
    }
)
SYNC_RETRY_BACKOFF_SECONDS = (60, 300, 900, 3600, 10800, 21600)


def public_tracking_url(settings: Settings, tracking: str) -> str:
    """Buyer-facing PorterChain tracking page (website /track/{number})."""
    base = settings.website_url.rstrip("/")
    return f"{base}/track/{tracking}" if tracking else f"{base}/track"


def schedule_sync_retry(
    shopify_meta: dict[str, Any],
    code: str,
    event_type: str | None,
    *,
    now: datetime | None = None,
) -> None:
    """Set or clear ``sync_retry`` on a Shopify meta dict (mutates in place)."""
    now = now or datetime.now(UTC)
    if code not in RETRYABLE_SYNC_ERRORS:
        shopify_meta.pop("sync_retry", None)
        return
    prev = shopify_meta.get("sync_retry") if isinstance(shopify_meta.get("sync_retry"), dict) else {}
    attempts = int(prev.get("attempts") or 0) + 1
    if attempts > len(SYNC_RETRY_BACKOFF_SECONDS):
        shopify_meta.pop("sync_retry", None)
        shopify_meta["sync_gave_up_at"] = now.isoformat()
        return
    delay = SYNC_RETRY_BACKOFF_SECONDS[attempts - 1]
    shopify_meta["sync_retry"] = {
        "attempts": attempts,
        "due_at": (now + timedelta(seconds=delay)).isoformat(),
        "event_type": event_type or prev.get("event_type"),
        "code": code,
    }


def _retry_due(retry: Any, now: datetime) -> bool:
    if not isinstance(retry, dict):
        return False
    try:
        due = datetime.fromisoformat(str(retry.get("due_at") or ""))
    except ValueError:
        return True
    if due.tzinfo is None:
        due = due.replace(tzinfo=UTC)
    return due <= now


def _clear_sync_retry(db: Session, order: Order) -> None:
    extra = dict(order.compliance_metadata or {})
    shopify_meta = dict(extra.get("shopify") or {})
    shopify_meta.pop("sync_retry", None)
    extra["shopify"] = shopify_meta
    order.compliance_metadata = extra
    db.commit()


def sweep_fulfillment_retries(
    db: Session, settings: Settings, *, now: datetime | None = None, limit: int = 50
) -> dict[str, int]:
    """Re-push Shopify fulfillment/tracking for orders whose retry is due."""
    now = now or datetime.now(UTC)
    candidates = (
        db.query(Order)
        .filter(Order.order_source == OrderSource.SHOPIFY.value)
        .filter(Order.compliance_metadata["shopify"]["sync_retry"].isnot(None))
        .limit(500)
        .all()
    )
    due = [
        o
        for o in candidates
        if _retry_due(((o.compliance_metadata or {}).get("shopify") or {}).get("sync_retry"), now)
    ][:limit]
    retried = 0
    for order in due:
        retry = ((order.compliance_metadata or {}).get("shopify") or {}).get("sync_retry") or {}
        try:
            push_fulfillment(db, settings, order, event_type=retry.get("event_type"))
            retried += 1
            after = ((order.compliance_metadata or {}).get("shopify") or {}).get("sync_retry")
            if after == retry:
                # Nothing to push any more (e.g. cancelled before a fulfillment existed).
                _clear_sync_retry(db, order)
        except Exception:  # noqa: BLE001
            db.rollback()
            logger.warning("shopify_fulfillment_retry_failed order=%s", order.id, exc_info=True)
    return {"due": len(due), "retried": retried}


def cancel_shopify_fulfillment(db: Session, settings: Settings, order: Order) -> None:
    meta = (order.compliance_metadata or {}).get("shopify") or {}
    fulfillment_id = str(meta.get("fulfillment_id") or "").strip()
    if not fulfillment_id:
        return
    shop_domain = str(meta.get("shop_domain") or "")
    shop = _helpers()._active_shop(db, shop_domain) if shop_domain else None
    if not shop:
        return
    token = access_token_for(shop, settings)
    if not token:
        return
    from porterchain_api.merchant_engine.shopify_admin_graphql import fulfillment_cancel

    fulfillment_cancel(shop.shop_domain, token, settings, fulfillment_id=fulfillment_id)


def delete_partner_services(shop: ShopifyShop, settings: Settings) -> None:
    token = access_token_for(shop, settings)
    if not token:
        return
    from porterchain_api.merchant_engine.shopify_admin_graphql import (
        ShopifyAdminError,
        carrier_service_delete,
        fulfillment_service_delete,
    )

    if shop.carrier_service_gid:
        try:
            carrier_service_delete(
                shop.shop_domain, token, settings, service_id=str(shop.carrier_service_gid)
            )
        except ShopifyAdminError:
            logger.info("shopify_carrier_delete_skipped shop=%s", shop.shop_domain)
        except Exception:  # noqa: BLE001
            logger.info("shopify_carrier_delete_skipped shop=%s", shop.shop_domain, exc_info=True)
    if shop.fulfillment_service_gid:
        try:
            fulfillment_service_delete(
                shop.shop_domain,
                token,
                settings,
                service_id=str(shop.fulfillment_service_gid),
            )
        except ShopifyAdminError:
            logger.info("shopify_fs_delete_skipped shop=%s", shop.shop_domain)
        except Exception:  # noqa: BLE001
            logger.info("shopify_fs_delete_skipped shop=%s", shop.shop_domain, exc_info=True)


def act_on_queued_fo(
    db: Session,
    settings: Settings,
    *,
    shop_domain: str,
    action: str,
    body: dict[str, Any],
) -> dict[str, Any]:
    """Accept or reject the fulfillment orders Shopify assigned to us, then book."""
    shop = _helpers()._active_shop(db, shop_domain)
    if not isinstance(shop, ShopifyShop):
        return {"ok": True, "skipped": "shop_not_connected", "action": action}
    if action == "shopify_fo_request" and shop.ingress_paused:
        return {"ok": True, "skipped": "ingress_paused", "action": action}
    token = access_token_for(shop, settings)
    if not token:
        return {"ok": True, "skipped": "missing_access_token", "action": action}
    kind = str(body.get("kind") or "")
    if action == "shopify_fo_cancel_request" or "CANCEL" in kind.upper():
        return _act_on_cancellations(db, settings, shop, token)
    return _act_on_fulfillment_requests(db, settings, shop, token)


def _act_on_fulfillment_requests(
    db: Session, settings: Settings, shop: ShopifyShop, token: str
) -> dict[str, Any]:
    from porterchain_api.merchant_engine.shopify_admin_graphql import (
        ShopifyAdminError,
        accept_fulfillment_request,
        assigned_fulfillment_orders,
        fulfillment_order_close,
        reject_fulfillment_request,
    )
    from porterchain_api.merchant_engine.shopify_payload_ops import _book_from_shopify_payload

    try:
        nodes = assigned_fulfillment_orders(
            shop.shop_domain, token, settings, assignment_status="FULFILLMENT_REQUESTED"
        )
    except ShopifyAdminError as exc:
        raise RuntimeError("shopify_graphql_failed") from exc
    accepted = 0
    rejected = 0
    window = (datetime.now(UTC) + timedelta(hours=8)).isoformat()
    from porterchain_api.merchant_engine.service_area import merchant_coverage_fsas

    coverage = merchant_coverage_fsas(db, db.get(Merchant, shop.merchant_id))
    for node in nodes:
        method = ""
        delivery = node.get("deliveryMethod")
        if isinstance(delivery, dict):
            method = str(delivery.get("methodType") or "")
        payload = _order_payload_from_fo(node)
        reason = _reject_reason(payload, method, coverage)
        fo_id = str(node.get("id") or "")
        if not fo_id:
            continue
        if reason:
            try:
                reject_fulfillment_request(
                    shop.shop_domain, token, settings, fulfillment_order_id=fo_id, message=reason
                )
            except ShopifyAdminError:
                logger.info("shopify_fo_reject_failed shop=%s", shop.shop_domain)
            rejected += 1
            continue
        try:
            accept_fulfillment_request(
                shop.shop_domain,
                token,
                settings,
                fulfillment_order_id=fo_id,
                message="PorterChain will deliver this shipment.",
                estimated_shipped_at=window,
            )
        except ShopifyAdminError:
            logger.info("shopify_fo_accept_failed shop=%s", shop.shop_domain)
            continue
        result = _book_from_shopify_payload(
            db, settings, shop_domain=shop.shop_domain, payload=payload
        )
        if result.get("skipped") == "out_of_service_area":
            try:
                fulfillment_order_close(
                    shop.shop_domain,
                    token,
                    settings,
                    fulfillment_order_id=fo_id,
                    message="Outside the priced delivery tile.",
                )
            except ShopifyAdminError:
                logger.info("shopify_fo_close_failed shop=%s", shop.shop_domain)
            rejected += 1
            continue
        accepted += 1
    return {"ok": True, "accepted": accepted, "rejected": rejected}


def _act_on_cancellations(
    db: Session, settings: Settings, shop: ShopifyShop, token: str
) -> dict[str, Any]:
    from porterchain_api.merchant_engine.shopify_admin_graphql import (
        ShopifyAdminError,
        accept_cancellation_request,
        assigned_fulfillment_orders,
        reject_cancellation_request,
    )
    from porterchain_api.merchant_engine.shopify_payload_ops import (
        _cancel_from_shopify_payload,
        _order_for_shopify,
    )
    from porterchain_api.merchant_engine.shopify_service import _PRE_PICKUP

    try:
        nodes = assigned_fulfillment_orders(
            shop.shop_domain, token, settings, assignment_status="CANCELLATION_REQUESTED"
        )
    except ShopifyAdminError as exc:
        raise RuntimeError("shopify_graphql_failed") from exc
    accepted = 0
    rejected = 0
    for node in nodes:
        fo_id = str(node.get("id") or "")
        payload = _order_payload_from_fo(node)
        order_id = str(payload.get("id") or "")
        order = (
            _order_for_shopify(
                db,
                merchant_id=shop.merchant_id,
                shop_domain=shop.shop_domain,
                shopify_order_id=order_id,
            )
            if order_id
            else None
        )
        pre_pickup = order is None or order.state in _PRE_PICKUP
        try:
            if pre_pickup:
                accept_cancellation_request(
                    shop.shop_domain,
                    token,
                    settings,
                    fulfillment_order_id=fo_id,
                    message="Cancellation accepted.",
                )
                if order_id:
                    _cancel_from_shopify_payload(
                        db, settings, shop_domain=shop.shop_domain, payload=payload
                    )
                accepted += 1
            else:
                reject_cancellation_request(
                    shop.shop_domain,
                    token,
                    settings,
                    fulfillment_order_id=fo_id,
                    message="Already picked up.",
                )
                rejected += 1
        except ShopifyAdminError:
            logger.info("shopify_fo_cancel_reply_failed shop=%s", shop.shop_domain)
    return {"ok": True, "accepted": accepted, "rejected": rejected}


def _reject_reason(
    payload: dict[str, Any], method: str, extra_fsas: frozenset[str] = frozenset()
) -> str | None:
    from porterchain_api.integrations.shopify_orders import is_canada_country
    from porterchain_api.merchant_engine.service_area import service_area_error
    from porterchain_api.schemas_merchant import AddressInput

    if method in {"PICK_UP", "PICKUP_POINT", "NONE"}:
        return "PorterChain delivers shipping orders only."
    if method == "LOCAL":
        from porterchain_api.integrations.shopify_orders import porterchain_shipping_selected

        lines = payload.get("shipping_lines")
        if not isinstance(lines, list) or not lines or not porterchain_shipping_selected(payload):
            return "Local delivery is not a PorterChain rate."
    address = payload.get("shipping_address") if isinstance(payload.get("shipping_address"), dict) else {}
    country = address.get("country") or address.get("countryCode")
    if not is_canada_country(country):
        return "PorterChain delivers in Canada only."
    postal = str(address.get("zip") or "")
    err = service_area_error(
        "destination", AddressInput(formatted=postal or "Canada", postal=postal or None), extra_fsas
    )
    if err:
        return "Outside the priced delivery tile."
    return None


def _shipping_lines_from_order(order: dict[str, Any]) -> list[dict[str, Any]]:
    conn = order.get("shippingLines") if isinstance(order.get("shippingLines"), dict) else {}
    edges = conn.get("edges") if isinstance(conn, dict) else None
    lines: list[dict[str, Any]] = []
    if isinstance(edges, list):
        for edge in edges:
            line = edge.get("node") if isinstance(edge, dict) else None
            if isinstance(line, dict):
                lines.append({"code": line.get("code"), "title": line.get("title")})
    return lines


def _order_payload_from_fo(node: dict[str, Any]) -> dict[str, Any]:
    dest = node.get("destination") if isinstance(node.get("destination"), dict) else {}
    order = node.get("order") if isinstance(node.get("order"), dict) else {}
    legacy = str(order.get("legacyResourceId") or "")
    if not legacy:
        legacy = str(order.get("id") or "").rsplit("/", 1)[-1]
    items: list[dict[str, Any]] = []
    edges = (node.get("lineItems") or {}).get("edges") if isinstance(node.get("lineItems"), dict) else []
    if isinstance(edges, list):
        for edge in edges:
            line = edge.get("node") if isinstance(edge, dict) else None
            if not isinstance(line, dict):
                continue
            product = line.get("lineItem") if isinstance(line.get("lineItem"), dict) else {}
            items.append(
                {
                    "title": product.get("title"),
                    "sku": line.get("sku") or product.get("sku"),
                    "quantity": line.get("remainingQuantity") or 1,
                    "grams": 0,
                }
            )
    first = str(dest.get("firstName") or "")
    last = str(dest.get("lastName") or "")
    method = ""
    delivery = node.get("deliveryMethod")
    if isinstance(delivery, dict):
        method = str(delivery.get("methodType") or "")
    shipping_lines = _shipping_lines_from_order(order)
    if not shipping_lines and method != "LOCAL":
        shipping_lines = [{"code": "porterchain_same_day", "title": "PorterChain Same Day"}]
    return {
        "id": legacy,
        "name": order.get("name") or "",
        "financial_status": "paid",
        "shipping_lines": shipping_lines,
        "shipping_address": {
            "address1": dest.get("address1"),
            "address2": dest.get("address2"),
            "city": dest.get("city"),
            "province": dest.get("province"),
            "zip": dest.get("zip"),
            "country": dest.get("countryCode") or "CA",
            "phone": dest.get("phone"),
            "name": " ".join(p for p in (first, last) if p),
        },
        "line_items": items,
        "fulfillment_order_id": node.get("id"),
    }
