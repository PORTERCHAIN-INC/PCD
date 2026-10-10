"""Shopify order book, update, cancel, and return. Called from shopify_service."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from porterchain_api.booking_models import Order
from porterchain_api.config import Settings
from porterchain_api.domain.merchant_states import MerchantRole, MerchantStatus
from porterchain_api.domain.states import OrderSource
from porterchain_api.integrations.shopify_orders import (
    customer_slice,
    is_canada_country,
    line_item_slice,
    map_shopify_order,
    order_ids,
    porterchain_shipping_selected,
    quote_id_from_order,
    shipping_address,
    unpaid_non_cod,
)
from porterchain_api.merchant_engine import shopify_service as shopify
from porterchain_api.merchant_engine.rbac import MerchantContext
from porterchain_api.merchant_engine.service_area import (
    assert_ontario_booking,
    merchant_coverage_fsas,
)
from porterchain_api.merchant_models import Merchant, ShopifyShop
from porterchain_api.schemas_merchant import AddressInput

logger = logging.getLogger(__name__)

def _rate_quote_for_order(
    db: Session,
    *,
    shop: ShopifyShop,
    body: Any,
    payload: dict[str, Any],
) -> Any:
    """Trusted checkout rate quote for this order.

    Bound id (when present and still for this shop + dest), then dest-hash
    (shop + destination + weight — no warehouse postal), then dest-FSA match.
    Never returns an unrelated destination quote.
    """
    try:
        from porterchain_api.integrations.shopify_carrier_rates import (
            _request_hash,
            find_quote_by_hash,
            find_quote_for_book,
            quote_usable_for_order,
        )
        from porterchain_api.merchant_models import ShopifyRateQuote

        drop_postal = getattr(body.dropoff, "postal", None) or ""
        bound_id = quote_id_from_order(payload)
        if bound_id:
            row = db.get(ShopifyRateQuote, bound_id)
            if quote_usable_for_order(row, shop_id=shop.id, dropoff_postal=drop_postal):
                return row
        req_hash = _request_hash(
            shop_id=shop.id,
            merchant_id=shop.merchant_id,
            dropoff_postal=drop_postal,
            weight_kg=body.weight_kg,
        )
        row = find_quote_by_hash(db, shop_id=shop.id, request_hash=req_hash)
        if quote_usable_for_order(row, shop_id=shop.id, dropoff_postal=drop_postal):
            return row
        return find_quote_for_book(
            db,
            shop_id=shop.id,
            dropoff_postal=drop_postal,
            weight_kg=body.weight_kg,
        )
    except Exception:
        logger.exception("shopify_book_quote_lookup_failed shop=%s", shop.shop_domain)
        return None


def _order_has_invoice(db: Session, order: Order) -> bool:
    from porterchain_api.booking_models import Invoice

    return db.query(Invoice.id).filter(Invoice.order_id == order.id).first() is not None


def _resolve_book_pickup(
    db: Session,
    *,
    shop: ShopifyShop,
    body: Any,
    payload: dict[str, Any],
) -> tuple[Any, str, Any]:
    """Pickup + source + matched rate quote for Shopify book."""
    from porterchain_api.integrations.shopify_carrier_rates import (
        pickup_from_rate_quote,
        resolve_shopify_pickup,
    )

    rate_quote = _rate_quote_for_order(db, shop=shop, body=body, payload=payload)
    from_quote = pickup_from_rate_quote(rate_quote)
    if from_quote is not None:
        quote_pickup, pickup_source = from_quote
        try:
            quote_pickup = shopify._ensure_coords(quote_pickup)
        except ValueError:
            quote_pickup, pickup_source = body.pickup, "porterchain_pickup"
        return quote_pickup, pickup_source, rate_quote
    quote_pickup, pickup_source, _reason = resolve_shopify_pickup(body.pickup, None)
    return quote_pickup, pickup_source, rate_quote


def _book_from_shopify_payload(
    db: Session,
    settings: Settings,
    *,
    shop_domain: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    shop = shopify._active_shop(db, shop_domain)
    if not shop:
        raise LookupError("shop_not_connected")
    if not porterchain_shipping_selected(payload):
        return {"ok": True, "skipped": "not_porterchain_rate"}
    if unpaid_non_cod(payload):
        return {"ok": True, "skipped": "unpaid"}
    address = shipping_address(payload) or {}
    country = address.get("country") or address.get("country_code") or address.get("countryCode")
    if not is_canada_country(country):
        return {"ok": True, "skipped": "out_of_service_area"}

    pickup_row = shopify.default_pickup_address(db, shop.merchant_id, shop=shop)
    if not pickup_row:
        raise RuntimeError("default_pickup_required")
    from porterchain_api.merchant_engine.shopify_one_click import (
        ensure_shop_pickup_bound,
    )

    shop = ensure_shop_pickup_bound(db, shop, address=pickup_row)
    pickup = shopify._ensure_coords(shopify.address_from_saved(pickup_row))
    body = map_shopify_order(payload, pickup=pickup)
    from porterchain_api.domain.customer_goods import persist_vehicle_class

    vehicle = persist_vehicle_class(getattr(shop, "default_vehicle_class", None))
    package = (getattr(shop, "default_package_type", None) or "").strip() or "looseParcel"
    body = body.model_copy(
        update={
            "pickup": shopify._ensure_coords(body.pickup),
            "dropoff": shopify._ensure_coords(body.dropoff),
            "vehicle_class": vehicle,
            "package_type": package,
        }
    )
    merchant = db.query(Merchant).filter(Merchant.id == shop.merchant_id).first()
    if not merchant or merchant.status != MerchantStatus.ACTIVE.value:
        raise RuntimeError("merchant_not_active")
    from porterchain_api.integrations.shopify_carrier_rates import (
        apply_shopify_book_vehicle,
    )

    body = apply_shopify_book_vehicle(merchant, body, payload)
    quote_pickup, pickup_source, rate_quote = _resolve_book_pickup(
        db, shop=shop, body=body, payload=payload
    )
    body = body.model_copy(update={"pickup": quote_pickup})
    try:
        assert_ontario_booking(body, extra_fsas=merchant_coverage_fsas(db, merchant))
    except shopify.BookingValidationError as exc:
        if exc.code == "out_of_service_area":
            return {"ok": True, "skipped": "out_of_service_area"}
        raise

    order_id, _name = order_ids(payload)
    key = f"shopify:{shop.shop_domain}:{order_id}"
    ctx = MerchantContext(merchant=merchant, user=shopify._actor(db, merchant), role=MerchantRole.OPS)

    existing = shopify._booking.find_by_idempotency_key(db, ctx, key)
    if existing:
        return {"ok": True, "order_id": existing.id, "replayed": True}

    # Shopify marks test checkouts with test=true; never book live capacity for those.
    is_sandbox = bool(payload.get("test")) or bool(payload.get("test_order"))
    auto_dispatch = bool(getattr(shop, "auto_dispatch", False))  # column default; returns used False already
    try:
        order = shopify._booking.create_shipment(
            db,
            settings,
            ctx,
            body,
            order_source=OrderSource.SHOPIFY.value,
            idempotency_key=key,
            sandbox=is_sandbox,
            auto_dispatch=auto_dispatch,
        )
    except IntegrityError:
        db.rollback()
        existing = shopify._booking.find_by_idempotency_key(db, ctx, key, is_sandbox=is_sandbox)
        if not existing:
            raise
        return {"ok": True, "order_id": existing.id, "replayed": True}
    extra = dict(order.compliance_metadata or {})
    lines = payload.get("shipping_lines") if isinstance(payload.get("shipping_lines"), list) else []
    shipping_code = None
    if lines and isinstance(lines[0], dict):
        shipping_code = lines[0].get("code")
    shopify_meta: dict[str, Any] = {
        "shop_domain": shop.shop_domain,
        "order_id": order_id,
        "order_name": _name,
        "held_for_ops": (not is_sandbox) and (not auto_dispatch),
        "auto_dispatch": auto_dispatch,
        "customer": customer_slice(payload, shop_domain=shop.shop_domain),
        "line_items": line_item_slice(payload),
        "shipping_code": shipping_code,
    }
    fo_id = payload.get("fulfillment_order_id")
    if fo_id:
        shopify_meta["fulfillment_order_id"] = str(fo_id)
    shopify_meta["pickup_source"] = pickup_source
    if rate_quote is not None:
        shopify_meta["rate_quote_id"] = rate_quote.id
        shopify_meta["rate_quote_cents"] = rate_quote.total_cents
        shopify_meta["rate_quote_hash"] = rate_quote.request_hash
    extra["shopify"] = shopify_meta
    order.compliance_metadata = extra
    db.commit()
    return {
        "ok": True,
        "order_id": order.id,
        "tracking_number": order.tracking_number,
        "held_for_ops": shopify_meta.get("held_for_ops"),
        "state": order.state,
    }


def _cancel_from_shopify_payload(
    db: Session,
    settings: Settings,
    *,
    shop_domain: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    shop = db.query(ShopifyShop).filter(ShopifyShop.shop_domain == shop_domain).first()
    if not shop:
        raise LookupError("shop_not_connected")
    order_id, _name = order_ids(payload)
    key = f"shopify:{shop.shop_domain}:{order_id}"
    merchant = db.query(Merchant).filter(Merchant.id == shop.merchant_id).first()
    if not merchant:
        raise LookupError("merchant_not_found")
    ctx = MerchantContext(merchant=merchant, user=shopify._actor(db, merchant), role=MerchantRole.OPS)
    order = shopify._booking.find_by_idempotency_key(db, ctx, key)
    if not order:
        # Fallback: compliance_metadata.shopify.order_id
        order = (
            db.query(Order)
            .filter(
                Order.merchant_id == merchant.id,
                Order.order_source == OrderSource.SHOPIFY.value,
                Order.purchase_order_number == str(order_id),
            )
            .first()
        )
    if not order:
        logger.info("shopify_cancel_no_order shop=%s shopify_order=%s", shop_domain, order_id)
        return {"ok": True, "skipped": "order_not_found"}
    if order.state == "CANCELLED":
        return {"ok": True, "order_id": order.id, "already_cancelled": True}
    try:
        shopify._booking.cancel_order(db, ctx, order, settings)
        db.commit()
    except (ValueError, PermissionError) as exc:
        logger.info(
            "shopify_cancel_refused order=%s state=%s err=%s",
            order.id,
            order.state,
            exc,
        )
        return {"ok": True, "order_id": order.id, "skipped": str(exc)}
    _cancel_shopify_fulfillment(db, settings, order)
    return {"ok": True, "order_id": order.id, "cancelled": True}


def _order_for_shopify(
    db: Session,
    *,
    merchant_id: str,
    shop_domain: str,
    shopify_order_id: str,
) -> Order | None:
    key = f"shopify:{shop_domain}:{shopify_order_id}"
    merchant = db.query(Merchant).filter(Merchant.id == merchant_id).first()
    if not merchant:
        return None
    ctx = MerchantContext(merchant=merchant, user=shopify._actor(db, merchant), role=MerchantRole.OPS)
    order = shopify._booking.find_by_idempotency_key(db, ctx, key)
    if order:
        return order
    return (
        db.query(Order)
        .filter(
            Order.merchant_id == merchant.id,
            Order.order_source == OrderSource.SHOPIFY.value,
            Order.purchase_order_number == str(shopify_order_id),
        )
        .first()
    )


def _note_shopify(order: Order, **fields: Any) -> None:
    extra = dict(order.compliance_metadata or {})
    shopify_meta = dict(extra.get("shopify") or {})
    shopify_meta.update(fields)
    extra["shopify"] = shopify_meta
    order.compliance_metadata = extra


def _update_from_shopify_payload(
    db: Session,
    settings: Settings,
    *,
    shop_domain: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Refresh a pre-pickup shipment. After pickup, record drift and leave the stop."""
    shop = shopify._active_shop(db, shop_domain)
    if not shop:
        raise LookupError("shop_not_connected")
    if not porterchain_shipping_selected(payload):
        order_id, _name = order_ids(payload)
        existing = _order_for_shopify(
            db, merchant_id=shop.merchant_id, shop_domain=shop.shop_domain, shopify_order_id=order_id
        )
        if existing and existing.state in shopify._PRE_PICKUP:
            return _cancel_from_shopify_payload(db, settings, shop_domain=shop_domain, payload=payload)
        return {"ok": True, "skipped": "not_porterchain_rate"}
    order_id, _name = order_ids(payload)
    existing = _order_for_shopify(
        db, merchant_id=shop.merchant_id, shop_domain=shop.shop_domain, shopify_order_id=order_id
    )
    if not existing:
        return _book_from_shopify_payload(db, settings, shop_domain=shop_domain, payload=payload)
    if existing.state not in shopify._PRE_PICKUP:
        events = list((existing.compliance_metadata or {}).get("shopify", {}).get("fo_events") or [])
        events.append({"kind": "orders_updated", "at": datetime.now(UTC).isoformat()})
        _note_shopify(
            existing,
            fo_events=events[-20:],
            drift_after_pickup=True,
            price_locked=True,
            amount_cents_unchanged=int(existing.amount_cents or 0),
        )
        logger.info(
            "shopify_update_price_locked order=%s state=%s", existing.id, existing.state
        )
        db.commit()
        return {"ok": True, "order_id": existing.id, "drift": True}
    pickup_row = shopify.default_pickup_address(db, shop.merchant_id, shop=shop)
    if not pickup_row:
        raise RuntimeError("default_pickup_required")
    from porterchain_api.merchant_engine.shopify_one_click import (
        ensure_shop_pickup_bound,
    )

    ensure_shop_pickup_bound(db, shop, address=pickup_row)
    pickup = shopify._ensure_coords(shopify.address_from_saved(pickup_row))
    # Keep the pickup the order was booked with (checkout quote / saved pickup
    # rule already applied at book). Only the buyer side changes on edit.
    booked_pickup = _address_from_stop(existing.pickup) if existing.pickup else pickup
    body = map_shopify_order(payload, pickup=booked_pickup)
    merchant = db.query(Merchant).filter(Merchant.id == shop.merchant_id).first()
    if not merchant or merchant.status != MerchantStatus.ACTIVE.value:
        raise RuntimeError("merchant_not_active")
    from porterchain_api.integrations.shopify_carrier_rates import (
        apply_shopify_book_vehicle,
    )

    body = apply_shopify_book_vehicle(merchant, body, payload)
    try:
        assert_ontario_booking(body, extra_fsas=merchant_coverage_fsas(db, merchant))
    except shopify.BookingValidationError as exc:
        if exc.code == "out_of_service_area":
            return {"ok": True, "skipped": "out_of_service_area", "order_id": existing.id}
        raise

    previous_amount = int(existing.amount_cents or 0)
    existing.dropoff = body.dropoff.model_dump()
    if body.weight_kg is not None:
        existing.weight_kg = body.weight_kg
    note_fields: dict[str, Any] = {
        "customer": customer_slice(payload, shop_domain=shop.shop_domain),
        "line_items": line_item_slice(payload),
        "order_name": _name,
    }

    can_reprice = existing.state in shopify._PRE_PICKUP and not _order_has_invoice(db, existing)
    if can_reprice:
        from porterchain_api.integrations.shopify_carrier_rates import (
            quote_merchant_rate,
        )

        line_items = (
            payload.get("line_items") if isinstance(payload.get("line_items"), list) else []
        )
        try:
            cents, breakdown = quote_merchant_rate(
                db,
                merchant,
                pickup=body.pickup,
                dropoff=body.dropoff,
                weight_kg=body.weight_kg,
                items=line_items,
                vehicle_class=getattr(body, "vehicle_class", None),
            )
        except Exception:
            logger.exception(
                "shopify_update_reprice_failed order=%s shop=%s", existing.id, shop.shop_domain
            )
            _note_shopify(
                existing,
                **note_fields,
                reprice_failed=True,
                amount_cents_unchanged=previous_amount,
            )
            db.commit()
            return {"ok": True, "order_id": existing.id, "updated": True, "reprice": "failed"}
        if (breakdown.get("metadata") or {}).get("fsa_refused"):
            _note_shopify(
                existing,
                **note_fields,
                reprice_skipped="fsa_refused",
                amount_cents_unchanged=previous_amount,
            )
            db.commit()
            return {
                "ok": True,
                "order_id": existing.id,
                "skipped": "fsa_refused",
                "updated": True,
            }
        existing.amount_cents = int(cents)
        note_fields["reprice"] = {
            "from_cents": previous_amount,
            "to_cents": int(cents),
            "at": datetime.now(UTC).isoformat(),
        }
    else:
        events = list((existing.compliance_metadata or {}).get("shopify", {}).get("fo_events") or [])
        events.append(
            {
                "kind": "orders_updated_price_locked",
                "at": datetime.now(UTC).isoformat(),
                "amount_cents": previous_amount,
                "reason": "invoiced",
            }
        )
        note_fields["fo_events"] = events[-20:]
        note_fields["price_locked"] = True
        note_fields["amount_cents_unchanged"] = previous_amount
        logger.info("shopify_update_price_locked order=%s reason=invoiced", existing.id)

    _note_shopify(existing, **note_fields)
    db.commit()
    return {
        "ok": True,
        "order_id": existing.id,
        "updated": True,
        "repriced": can_reprice,
        "amount_cents": existing.amount_cents,
    }


def _sync_fulfillment_order(
    db: Session,
    settings: Settings,
    *,
    shop_domain: str,
    topic: str | None,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Hold, move, split, merge, and reschedule update the same order before pickup."""
    del settings
    shop = shopify._active_shop(db, shop_domain)
    if not shop:
        return {"ok": True, "skipped": "shop_not_connected"}
    fo = payload.get("fulfillment_order") if isinstance(payload.get("fulfillment_order"), dict) else payload
    shopify_order_id = str(fo.get("order_id") or payload.get("order_id") or "")
    if not shopify_order_id:
        return {"ok": True, "skipped": "order_id_missing"}
    order = _order_for_shopify(
        db,
        merchant_id=shop.merchant_id,
        shop_domain=shop.shop_domain,
        shopify_order_id=shopify_order_id,
    )
    if not order:
        return {"ok": True, "skipped": "order_not_found"}
    topic_name = topic or ""
    held = "placed/on/hold" in topic_name
    released = "hold/released" in topic_name
    if order.state not in shopify._PRE_PICKUP:
        events = list((order.compliance_metadata or {}).get("shopify", {}).get("fo_events") or [])
        events.append({"kind": topic_name or "fo_sync", "at": datetime.now(UTC).isoformat()})
        _note_shopify(order, fo_events=events[-20:], drift_after_pickup=True)
        db.commit()
        return {"ok": True, "order_id": order.id, "drift": True}
    if held:
        _note_shopify(order, held_by_shopify=True)
    elif released:
        _note_shopify(order, held_by_shopify=False)
    else:
        events = list((order.compliance_metadata or {}).get("shopify", {}).get("fo_events") or [])
        events.append({"kind": topic_name or "fo_sync", "at": datetime.now(UTC).isoformat()})
        _note_shopify(order, fo_events=events[-20:])
    db.commit()
    return {"ok": True, "order_id": order.id, "synced": True}


def _address_from_stop(stop: Any) -> AddressInput:
    data = stop if isinstance(stop, dict) else {}
    return AddressInput(
        formatted=str(data.get("formatted") or ""),
        postal=data.get("postal"),
        lat=data.get("lat"),
        lng=data.get("lng"),
    )


def _return_from_shopify_payload(
    db: Session,
    settings: Settings,
    *,
    shop_domain: str,
    payload: dict[str, Any],
    action: str,
) -> dict[str, Any]:
    """In-tile return pickup. Money stays in Shopify."""
    shop = shopify._active_shop(db, shop_domain)
    if not shop:
        raise LookupError("shop_not_connected")
    return_id = str(payload.get("id") or "")
    shopify_order_id = str(payload.get("order_id") or "")
    if action == "shopify_return_cancel":
        if not return_id:
            return {"ok": True, "skipped": "return_id_missing"}
        merchant = db.query(Merchant).filter(Merchant.id == shop.merchant_id).first()
        if not merchant:
            raise LookupError("merchant_not_found")
        ctx = MerchantContext(merchant=merchant, user=shopify._actor(db, merchant), role=MerchantRole.OPS)
        key = f"shopify-return:{shop.shop_domain}:{return_id}"
        order = shopify._booking.find_by_idempotency_key(db, ctx, key)
        if not order or order.state not in shopify._PRE_PICKUP:
            return {"ok": True, "skipped": "return_not_cancellable"}
        try:
            shopify._booking.cancel_order(db, ctx, order, settings)
            db.commit()
        except (ValueError, PermissionError) as exc:
            return {"ok": True, "order_id": order.id, "skipped": str(exc)}
        return {"ok": True, "order_id": order.id, "cancelled": True}
    if not return_id or not shopify_order_id:
        return {"ok": True, "skipped": "return_ids_missing"}
    original = _order_for_shopify(
        db,
        merchant_id=shop.merchant_id,
        shop_domain=shop.shop_domain,
        shopify_order_id=shopify_order_id,
    )
    if not original:
        return {"ok": True, "skipped": "order_not_found"}
    merchant = db.query(Merchant).filter(Merchant.id == shop.merchant_id).first()
    if not merchant or merchant.status != MerchantStatus.ACTIVE.value:
        raise RuntimeError("merchant_not_active")
    ctx = MerchantContext(merchant=merchant, user=shopify._actor(db, merchant), role=MerchantRole.OPS)
    key = f"shopify-return:{shop.shop_domain}:{return_id}"
    existing = shopify._booking.find_by_idempotency_key(db, ctx, key)
    if existing:
        return {"ok": True, "order_id": existing.id, "replayed": True}
    from porterchain_api.merchant_engine.return_service import (
        SOURCE_SHOPIFY,
        create_return_order,
    )

    try:
        order = create_return_order(
            db,
            settings,
            ctx,
            original,
            source=SOURCE_SHOPIFY,
            idempotency_key=key,
            booking=shopify._booking,
            reference=f"return-{return_id}",
            purchase_order=shopify_order_id,
            order_source=OrderSource.SHOPIFY.value,
            auto_dispatch=bool(getattr(shop, "auto_dispatch", False)),
            extra={"shopify_return_id": return_id},
        )
    except shopify.BookingValidationError as exc:
        if exc.code == "out_of_service_area":
            return {"ok": True, "skipped": "out_of_service_area"}
        raise
    _note_shopify(
        order,
        shop_domain=shop.shop_domain,
        order_id=shopify_order_id,
        return_id=return_id,
        return_of=original.id,
        customer=(original.compliance_metadata or {}).get("shopify", {}).get("customer"),
    )
    db.commit()
    _push_reverse_delivery(db, settings, shop, order, payload)
    return {"ok": True, "order_id": order.id, "return": True}


def _push_reverse_delivery(
    db: Session,
    settings: Settings,
    shop: ShopifyShop,
    order: Order,
    payload: dict[str, Any],
) -> None:
    reverse_id = str(
        payload.get("reverse_fulfillment_order_id")
        or payload.get("admin_graphql_api_id")
        or ""
    )
    if not reverse_id.startswith("gid://shopify/ReverseFulfillmentOrder/"):
        return
    from porterchain_api.merchant_engine.shopify_tokens import access_token_for

    token = access_token_for(shop, settings)
    if not token or not order.tracking_number:
        return
    try:
        from porterchain_api.merchant_engine.shopify_admin_graphql import (
            reverse_delivery_create,
        )

        delivery_id = reverse_delivery_create(
            shop.shop_domain,
            token,
            settings,
            reverse_fulfillment_order_id=reverse_id,
            tracking={
                "number": order.tracking_number,
                "url": f"{settings.website_url.rstrip('/')}/track/{order.tracking_number}",
            },
        )
        if delivery_id:
            _note_shopify(order, reverse_delivery_id=delivery_id)
            db.commit()
    except Exception:
        logger.warning("shopify_reverse_delivery_failed order=%s", order.id, exc_info=True)


def _cancel_shopify_fulfillment(db: Session, settings: Settings, order: Order) -> None:
    try:
        from porterchain_api.merchant_engine.shopify_fulfillment_service import (
            cancel_shopify_fulfillment,
        )

        cancel_shopify_fulfillment(db, settings, order)
    except Exception:
        logger.warning("shopify_fulfillment_cancel_failed order=%s", order.id, exc_info=True)

