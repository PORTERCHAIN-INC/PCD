"""Shopify install, inbound orders/create, and fulfillment push-back."""

from __future__ import annotations

import json
import logging
import secrets
import time
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlencode

import httpx
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from porterchain_api.config import Settings
from porterchain_api.domain.merchant_states import MerchantRole, MerchantStatus
from porterchain_api.domain.states import OrderSource
from porterchain_api.fleetbase_engine.merchant_sync_service import BookingValidationError
from porterchain_api.integrations.shopify_hmac import verify_oauth_hmac, verify_webhook_hmac
from porterchain_api.integrations.shopify_orders import map_shopify_order, order_ids
from porterchain_api.merchant_engine.activation_service import (
    SIGNUP_SOURCE_SHOPIFY,
    apply_signup_policy,
)
from porterchain_api.merchant_engine.booking_service import MerchantBookingService
from porterchain_api.merchant_engine.import_geocode import geocode_stop
from porterchain_api.merchant_engine.rbac import MerchantContext
from porterchain_api.merchant_engine.secrets import decrypt_signing_secret, encrypt_signing_secret
from porterchain_api.merchant_engine.service_area import assert_ontario_booking
from porterchain_api.merchant_engine.shopify_urls import (
    app_home_url,
    callback_url,
    carrier_rates_url,
    fulfillment_service_url,
    install_url,
    is_shop_domain,
    normalize_shop_domain,
    oauth_configured,
    read_oauth_state,
    sign_oauth_state,
    webhook_url,
)
from porterchain_api.merchant_models import Merchant, MerchantUser, SavedAddress, ShopifyShop
from porterchain_api.booking_models import Order
from porterchain_api.schemas_merchant import AddressInput

from porterchain_api.merchant_engine.shopify_one_click import (  # noqa: F401
    connection_payload,
    go_live,
)
from porterchain_api.merchant_engine.shopify_one_click import (
    handle_gdpr_topic as _handle_gdpr_topic,
)

logger = logging.getLogger(__name__)

_GDPR_TOPICS = frozenset({"shop/redact", "customers/redact", "customers/data_request"})

_booking = MerchantBookingService()


def _encrypt(value: str | None, settings: Settings) -> str | None:
    if not value:
        return None
    return encrypt_signing_secret(value, encryption_key=settings.jwt_secret)


def _decrypt(value: str | None, settings: Settings) -> str | None:
    if not value:
        return None
    return decrypt_signing_secret(value, encryption_key=settings.jwt_secret)


def default_pickup_address(
    db: Session,
    merchant_id: str,
    *,
    shop: ShopifyShop | None = None,
) -> SavedAddress | None:
    if shop and shop.default_pickup_address_id:
        row = (
            db.query(SavedAddress)
            .filter(
                SavedAddress.id == shop.default_pickup_address_id,
                SavedAddress.merchant_id == merchant_id,
            )
            .first()
        )
        if row:
            return row
    return (
        db.query(SavedAddress)
        .filter(SavedAddress.merchant_id == merchant_id)
        .order_by(SavedAddress.is_default.desc(), SavedAddress.created_at.asc())
        .first()
    )


def address_from_saved(row: SavedAddress) -> AddressInput:
    return AddressInput(
        formatted=row.formatted,
        place_id=row.place_id,
        lat=row.lat,
        lng=row.lng,
        postal=row.postal,
    )


def _ensure_coords(addr: AddressInput) -> AddressInput:
    if addr.lat is not None and addr.lng is not None:
        return addr
    geo = geocode_stop(address=addr.formatted, postal=addr.postal, lat=addr.lat, lng=addr.lng)
    if geo.lat is None or geo.lng is None:
        raise ValueError("geocode_failed")
    return addr.model_copy(
        update={
            "lat": geo.lat,
            "lng": geo.lng,
            "formatted": geo.formatted or addr.formatted,
            "postal": addr.postal or None,
        }
    )


def _actor(db: Session, merchant: Merchant) -> MerchantUser:
    user = (
        db.query(MerchantUser)
        .filter(MerchantUser.merchant_id == merchant.id, MerchantUser.is_active.is_(True))
        .order_by(MerchantUser.created_at.asc())
        .first()
    )
    if user:
        return user
    email = (merchant.email or "").strip().lower()
    # Real shop emails get a pending:{email} seat so Clerk sign-in can claim the merchant.
    if email and not email.endswith("@merchants.porterchain.invalid"):
        from porterchain_api.merchant_engine.team_service import ensure_merchant_seat

        return ensure_merchant_seat(
            db,
            merchant_id=merchant.id,
            email=email,
            role=MerchantRole.OWNER.value,
            audit_action="shopify.owner_seat",
            commit=False,
        )
    user = MerchantUser(
        merchant_id=merchant.id,
        clerk_user_id=f"shopify:{merchant.id}",
        email=merchant.email,
        role=MerchantRole.OWNER.value,
        is_active=True,
    )
    db.add(user)
    db.flush()
    return user


def _active_shop(db: Session, shop_domain: str) -> ShopifyShop | None:
    return (
        db.query(ShopifyShop)
        .filter(ShopifyShop.shop_domain == shop_domain, ShopifyShop.uninstalled_at.is_(None))
        .first()
    )


def connect_custom_app(
    db: Session,
    ctx: MerchantContext,
    settings: Settings,
    *,
    shop_domain: str,
    admin_access_token: str,
    webhook_secret: str | None = None,
    default_pickup_address_id: str | None = None,
) -> ShopifyShop:
    shop = normalize_shop_domain(shop_domain)
    if not is_shop_domain(shop):
        raise ValueError("shop_domain_invalid")
    token = (admin_access_token or "").strip()
    if not token:
        raise ValueError("admin_access_token_required")
    pickup_id = (default_pickup_address_id or "").strip() or None
    if not pickup_id:
        raise ValueError("pickup_address_required")
    if pickup_id:
        addr = (
            db.query(SavedAddress)
            .filter(SavedAddress.id == pickup_id, SavedAddress.merchant_id == ctx.merchant.id)
            .first()
        )
        if not addr:
            raise LookupError("pickup_address_not_found")
    row = db.query(ShopifyShop).filter(ShopifyShop.shop_domain == shop).first()
    if row and row.merchant_id != ctx.merchant.id:
        raise ValueError("shop_already_connected")
    if row is None:
        row = ShopifyShop(merchant_id=ctx.merchant.id, shop_domain=shop, auto_dispatch=False)
        db.add(row)
    row.merchant_id = ctx.merchant.id
    row.encrypted_access_token = _encrypt(token, settings)
    if webhook_secret:
        row.encrypted_webhook_secret = _encrypt(webhook_secret.strip(), settings)
    if pickup_id:
        row.default_pickup_address_id = pickup_id
    row.uninstalled_at = None
    row.installed_at = datetime.now(UTC)
    apply_signup_policy(db, ctx.merchant, source=SIGNUP_SOURCE_SHOPIFY)
    db.commit()
    db.refresh(row)
    _post_install_hooks(row, settings)
    return row


def set_default_pickup(
    db: Session,
    ctx: MerchantContext,
    shop_id: str,
    address_id: str,
) -> ShopifyShop:
    shop = (
        db.query(ShopifyShop)
        .filter(ShopifyShop.id == shop_id, ShopifyShop.merchant_id == ctx.merchant.id)
        .first()
    )
    if not shop:
        raise LookupError("shop_not_found")
    addr = (
        db.query(SavedAddress)
        .filter(SavedAddress.id == address_id, SavedAddress.merchant_id == ctx.merchant.id)
        .first()
    )
    if not addr:
        raise LookupError("pickup_address_not_found")
    shop.default_pickup_address_id = addr.id
    db.commit()
    db.refresh(shop)
    return shop


def disconnect_shop(db: Session, ctx: MerchantContext, shop_id: str) -> None:
    shop = (
        db.query(ShopifyShop)
        .filter(ShopifyShop.id == shop_id, ShopifyShop.merchant_id == ctx.merchant.id)
        .first()
    )
    if not shop:
        raise LookupError("shop_not_found")
    shop.uninstalled_at = datetime.now(UTC)
    shop.encrypted_access_token = None
    db.commit()


def complete_oauth(
    db: Session,
    settings: Settings,
    *,
    shop_domain: str,
    code: str,
    state: str | None,
    query_string: str,
) -> ShopifyShop:
    if not oauth_configured(settings):
        raise ValueError("shopify_oauth_not_configured")
    if not verify_oauth_hmac(query_string, settings.shopify_api_secret):
        raise ValueError("oauth_hmac_invalid")
    shop = normalize_shop_domain(shop_domain)
    if not is_shop_domain(shop):
        raise ValueError("shop_domain_invalid")
    oauth_state = read_oauth_state(state, settings)
    merchant_id = oauth_state.merchant_id
    token_body = _exchange_token(shop, code, settings)
    access_token = str(token_body.get("access_token") or "")
    if not access_token:
        raise ValueError("oauth_token_missing")
    shop_info = _admin_get(shop, access_token, "/shop.json", settings) or {}
    shop_payload = shop_info.get("shop") if isinstance(shop_info.get("shop"), dict) else shop_info
    merchant = _merchant_for_install(db, merchant_id, shop, shop_payload)
    row = db.query(ShopifyShop).filter(ShopifyShop.shop_domain == shop).first()
    if row and row.merchant_id != merchant.id:
        raise ValueError("shop_already_connected")
    if row is None:
        row = ShopifyShop(merchant_id=merchant.id, shop_domain=shop, auto_dispatch=False)
        db.add(row)
    row.merchant_id = merchant.id
    row.encrypted_access_token = _encrypt(access_token, settings)
    row.scopes = str(token_body.get("scope") or settings.shopify_api_scopes)
    gid = shop_payload.get("id") if isinstance(shop_payload, dict) else None
    row.shopify_shop_gid = str(gid) if gid else row.shopify_shop_gid
    row.uninstalled_at = None
    row.installed_at = datetime.now(UTC)
    # One-click: bind pickup from signed state, else merchant default warehouse.
    preferred_pickup = oauth_state.pickup_address_id
    if preferred_pickup:
        addr = (
            db.query(SavedAddress)
            .filter(
                SavedAddress.id == preferred_pickup,
                SavedAddress.merchant_id == merchant.id,
            )
            .first()
        )
        if addr:
            row.default_pickup_address_id = addr.id
    elif not row.default_pickup_address_id:
        fallback = default_pickup_address(db, merchant.id)
        if fallback:
            row.default_pickup_address_id = fallback.id
    apply_signup_policy(db, merchant, source=SIGNUP_SOURCE_SHOPIFY)
    db.commit()
    db.refresh(row)
    _post_install_hooks(row, settings)
    return row


def ingest_webhook(
    db: Session,
    settings: Settings,
    *,
    raw_body: bytes,
    hmac_header: str | None,
    shop_domain_header: str | None,
    topic: str | None,
) -> dict[str, Any]:
    """HMAC on the request path; book/cancel run on WEBHOOKS worker (Phase 4).

    Returns 200-worthy payload only after enqueue succeeds for order topics.
    Raises PermissionError on bad HMAC; RuntimeError('shopify_enqueue_failed') → 503.
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

    topic_name = (topic or "").strip().lower().replace("_", "/")
    if topic_name in _GDPR_TOPICS:
        return _handle_gdpr_topic(
            db, settings, topic=topic_name, shop=shop, raw_body=raw_body
        )
    if topic_name in {"app/uninstalled"}:
        if shop:
            shop.uninstalled_at = datetime.now(UTC)
            shop.encrypted_access_token = None
            db.commit()
        return {"ok": True, "uninstalled": True}

    create_topics = {"orders/create"}
    cancel_topics = {"orders/cancelled", "orders/canceled"}
    # Topics after ingest normalize: lower + "_" → "/".
    # Shopify header example: fulfillment_orders/fulfillment_request_submitted
    # → fulfillment/orders/fulfillment/request/submitted
    fo_topics = {
        "fulfillment/orders/fulfillment/request/submitted",
        "fulfillment/orders/cancellation/request/submitted",
    }
    if topic_name in fo_topics:
        if not settings.shopify_fulfillment_service_enabled:
            return {"ok": True, "ignored": topic_name, "reason": "fo_flag_off"}
        action = (
            "shopify_fo_request"
            if "fulfillment_request" in topic_name
            else "shopify_fo_cancel_request"
        )
    elif topic_name in create_topics:
        action = "shopify_orders_create"
    elif topic_name in cancel_topics:
        action = "shopify_orders_cancelled"
    else:
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
                "raw_body": raw_body.decode("utf-8"),
            },
        )
    except Exception as exc:  # noqa: BLE001 — Shopify must not get 200 if job was dropped
        logger.exception("shopify_webhook_enqueue_failed shop=%s topic=%s", shop_domain, topic_name)
        raise RuntimeError("shopify_enqueue_failed") from exc
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
    if action == "shopify_orders_create" and shop and shop.ingress_paused:
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
        if action == "shopify_orders_cancelled":
            return _cancel_from_shopify_payload(db, settings, shop_domain=shop_domain, payload=body)
        if action in {"shopify_fo_request", "shopify_fo_cancel_request"}:
            # Foundation: enqueue + ack only. Accept→book is intentional hold (PCD_INTENTIONAL_SKIPS).
            if not settings.shopify_fulfillment_service_enabled:
                return {"ok": True, "skipped": "fo_flag_off", "action": action}
            logger.info(
                "shopify_fo_stub action=%s shop=%s keys=%s",
                action,
                shop_domain,
                list(body.keys())[:12],
            )
            return {"ok": True, "stub": True, "action": action, "detail": "fo_accept_book_held"}
        raise ValueError(f"unknown_shopify_action:{action}")
    except Exception as exc:  # noqa: BLE001 — persist DLQ then re-raise for worker visibility
        if action in {"shopify_orders_create", "shopify_orders_cancelled"} and not from_dlq:
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


def _book_from_shopify_payload(
    db: Session,
    settings: Settings,
    *,
    shop_domain: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    shop = _active_shop(db, shop_domain)
    if not shop:
        raise LookupError("shop_not_connected")

    pickup_row = default_pickup_address(db, shop.merchant_id, shop=shop)
    if not pickup_row:
        raise RuntimeError("default_pickup_required")
    pickup = _ensure_coords(address_from_saved(pickup_row))
    body = map_shopify_order(payload, pickup=pickup)
    from porterchain_api.domain.customer_goods import persist_vehicle_class

    vehicle = persist_vehicle_class(getattr(shop, "default_vehicle_class", None))
    package = (getattr(shop, "default_package_type", None) or "").strip() or "looseParcel"
    body = body.model_copy(
        update={
            "pickup": _ensure_coords(body.pickup),
            "dropoff": _ensure_coords(body.dropoff),
            "vehicle_class": vehicle,
            "package_type": package,
        }
    )
    assert_ontario_booking(body)

    order_id, _name = order_ids(payload)
    key = f"shopify:{shop.shop_domain}:{order_id}"
    merchant = db.query(Merchant).filter(Merchant.id == shop.merchant_id).first()
    if not merchant or merchant.status != MerchantStatus.ACTIVE.value:
        raise RuntimeError("merchant_not_active")
    ctx = MerchantContext(merchant=merchant, user=_actor(db, merchant), role=MerchantRole.OPS)

    existing = _booking.find_by_idempotency_key(db, ctx, key)
    if existing:
        return {"ok": True, "order_id": existing.id, "replayed": True}

    # Shopify marks test checkouts with test=true; never book live capacity for those.
    is_sandbox = bool(payload.get("test")) or bool(payload.get("test_order"))
    auto_dispatch = bool(getattr(shop, "auto_dispatch", True))
    try:
        order = _booking.create_shipment(
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
        existing = _booking.find_by_idempotency_key(db, ctx, key, is_sandbox=is_sandbox)
        if not existing:
            raise
        return {"ok": True, "order_id": existing.id, "replayed": True}
    extra = dict(order.compliance_metadata or {})
    shopify_meta: dict[str, Any] = {
        "shop_domain": shop.shop_domain,
        "order_id": order_id,
        "order_name": _name,
        "held_for_ops": (not is_sandbox) and (not auto_dispatch),
        "auto_dispatch": auto_dispatch,
    }
    try:
        from porterchain_api.integrations.shopify_carrier_rates import find_quote_for_book

        drop_postal = getattr(body.dropoff, "postal", None) or ""
        quote = find_quote_for_book(db, shop_id=shop.id, dropoff_postal=drop_postal)
        if quote:
            shopify_meta["rate_quote_id"] = quote.id
            shopify_meta["rate_quote_cents"] = quote.total_cents
            shopify_meta["rate_quote_hash"] = quote.request_hash
    except Exception:  # noqa: BLE001 — booking must not fail on quote lookup
        logger.exception("shopify_book_quote_attach_failed shop=%s", shop.shop_domain)
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
    ctx = MerchantContext(merchant=merchant, user=_actor(db, merchant), role=MerchantRole.OPS)
    order = _booking.find_by_idempotency_key(db, ctx, key)
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
        _booking.cancel_order(db, ctx, order, settings)
        db.commit()
    except (ValueError, PermissionError) as exc:
        logger.info(
            "shopify_cancel_refused order=%s state=%s err=%s",
            order.id,
            order.state,
            exc,
        )
        return {"ok": True, "order_id": order.id, "skipped": str(exc)}
    return {"ok": True, "order_id": order.id, "cancelled": True}


def capture_cod_transaction(db: Session, settings: Settings, order: Order) -> None:
    """Mark Shopify order paid after COD Stripe capture (manual payment method)."""
    if order.order_source != OrderSource.SHOPIFY.value:
        return
    meta = (order.compliance_metadata or {}).get("shopify") or {}
    shop_domain = str(meta.get("shop_domain") or "")
    shopify_order_id = str(meta.get("order_id") or order.purchase_order_number or "")
    if not shop_domain or not shopify_order_id:
        return
    shop = _active_shop(db, shop_domain)
    if not shop:
        return
    token = _decrypt(shop.encrypted_access_token, settings)
    if not token:
        return
    amount = (order.cod_amount_cents or 0) / 100.0
    currency = (order.currency or "CAD").upper()
    resp = _admin_post(
        shop.shop_domain,
        token,
        f"/orders/{shopify_order_id}/transactions.json",
        settings,
        {
            "transaction": {
                "kind": "capture",
                "status": "success",
                "amount": f"{amount:.2f}",
                "currency": currency,
                "source": "external",
            }
        },
    )
    if isinstance(resp, dict):
        extra = dict(order.compliance_metadata or {})
        shopify_meta = dict(extra.get("shopify") or {})
        tx = resp.get("transaction") if isinstance(resp.get("transaction"), dict) else {}
        if tx.get("id"):
            shopify_meta["cod_transaction_id"] = str(tx["id"])
        shopify_meta["cod_captured"] = True
        extra["shopify"] = shopify_meta
        order.compliance_metadata = extra
        db.add(order)
        db.commit()
        logger.info("shopify_cod_captured order=%s shopify=%s", order.id, shopify_order_id)


def _merchant_for_install(
    db: Session,
    merchant_id: str | None,
    shop_domain: str,
    shop_payload: dict[str, Any],
) -> Merchant:
    """Resolve merchant for OAuth install — never steal another merchant's shop.

    Portal install always passes signed ``merchant_id`` in state. Public install
    may omit it: rebind only an already-linked shop domain, else create a new
    onboarding merchant. Email match is allowed only when that merchant has no
    other active Shopify shop (blocks email-hijack onto an established account).
    """
    if merchant_id:
        merchant = db.query(Merchant).filter(Merchant.id == merchant_id).first()
        if not merchant:
            raise ValueError("merchant_not_found")
        # Signed state merchant wins — never fall through to email attach.
        other = (
            db.query(ShopifyShop)
            .filter(
                ShopifyShop.shop_domain == shop_domain,
                ShopifyShop.merchant_id != merchant.id,
                ShopifyShop.uninstalled_at.is_(None),
            )
            .first()
        )
        if other:
            raise ValueError("shop_already_connected")
        return merchant

    existing_shop = db.query(ShopifyShop).filter(ShopifyShop.shop_domain == shop_domain).first()
    if existing_shop:
        merchant = db.query(Merchant).filter(Merchant.id == existing_shop.merchant_id).first()
        if merchant:
            return merchant

    email = str(shop_payload.get("email") or "").strip().lower()
    if email:
        by_email = db.query(Merchant).filter(Merchant.email == email).first()
        if by_email:
            # Refuse attach when that merchant already has a different live shop.
            other_shop = (
                db.query(ShopifyShop)
                .filter(
                    ShopifyShop.merchant_id == by_email.id,
                    ShopifyShop.shop_domain != shop_domain,
                    ShopifyShop.uninstalled_at.is_(None),
                    ShopifyShop.encrypted_access_token.isnot(None),
                )
                .first()
            )
            if other_shop:
                raise ValueError("shopify_email_already_bound")
            return by_email

    if not email:
        local = shop_domain.split(".", 1)[0]
        email = f"{local}@merchants.porterchain.invalid"
    name = str(shop_payload.get("name") or shop_domain)
    merchant = Merchant(
        status=MerchantStatus.ONBOARDING.value,
        company_name=name,
        email=email,
        payment_terms="NET_30",
        profile={"source": SIGNUP_SOURCE_SHOPIFY, "shopify_shop_domain": shop_domain},
    )
    db.add(merchant)
    db.flush()
    apply_signup_policy(db, merchant, source=SIGNUP_SOURCE_SHOPIFY)
    _actor(db, merchant)
    return merchant


def _admin_headers(token: str) -> dict[str, str]:
    return {"X-Shopify-Access-Token": token, "Content-Type": "application/json"}


def _admin_url(shop: str, path: str, settings: Settings) -> str:
    return f"https://{shop}/admin/api/{settings.shopify_api_version}{path}"


def _exchange_token(shop: str, code: str, settings: Settings) -> dict[str, Any]:
    url = f"https://{shop}/admin/oauth/access_token"
    with httpx.Client(timeout=15.0) as client:
        response = client.post(
            url,
            json={
                "client_id": settings.shopify_api_key,
                "client_secret": settings.shopify_api_secret,
                "code": code,
            },
        )
        response.raise_for_status()
        body = response.json()
    return body if isinstance(body, dict) else {}


def _admin_get(shop: str, token: str, path: str, settings: Settings) -> dict[str, Any] | None:
    with httpx.Client(timeout=15.0) as client:
        response = client.get(_admin_url(shop, path, settings), headers=_admin_headers(token))
        if response.status_code >= 400:
            logger.warning("shopify_admin_get_failed path=%s status=%s", path, response.status_code)
            return None
        body = response.json()
    return body if isinstance(body, dict) else None


def _admin_post(
    shop: str, token: str, path: str, settings: Settings, json_body: dict[str, Any]
) -> dict[str, Any] | None:
    with httpx.Client(timeout=15.0) as client:
        response = client.post(
            _admin_url(shop, path, settings), headers=_admin_headers(token), json=json_body
        )
        if response.status_code >= 400:
            logger.warning(
                "shopify_admin_post_failed path=%s status=%s body=%s",
                path,
                response.status_code,
                response.text[:300],
            )
            return None
        if not response.content:
            return {}
        body = response.json()
    return body if isinstance(body, dict) else None




# Re-exports — fulfillment / FO live in shopify_fulfillment_service (ENG-G2 LOC).
from porterchain_api.merchant_engine.shopify_fulfillment_service import (  # noqa: E402
    ingest_fulfillment_order_notification,
    push_fulfillment,
)
from porterchain_api.merchant_engine import shopify_fulfillment_service as _fo  # noqa: E402


def _post_install_hooks(shop: ShopifyShop, settings: Settings) -> None:
    _fo._post_install_hooks(shop, settings)
