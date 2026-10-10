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
from porterchain_api.domain.states import OrderSource, OrderState
from porterchain_api.merchant_engine.booking_validation import BookingValidationError
from porterchain_api.integrations.shopify_hmac import verify_webhook_hmac
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
from porterchain_api.merchant_engine.activation_service import (
    SIGNUP_SOURCE_SHOPIFY,
    apply_signup_policy,
)
from porterchain_api.merchant_engine.booking_service import MerchantBookingService
from porterchain_api.merchant_engine.import_geocode import geocode_stop
from porterchain_api.merchant_engine.rbac import MerchantContext
from porterchain_api.merchant_engine.secrets import decrypt_signing_secret, encrypt_signing_secret
from porterchain_api.merchant_engine.service_area import assert_ontario_booking
from porterchain_api.merchant_engine import shopify_tokens as tokens
from porterchain_api.merchant_engine.shopify_urls import (
    carrier_rates_url,
    fulfillment_service_url,
    is_shop_domain,
    normalize_shop_domain,
    webhook_url,
)
from porterchain_api.merchant_models import Merchant, MerchantUser, SavedAddress, ShopifyShop
from porterchain_api.booking_models import Order
from porterchain_api.schemas_merchant import AddressInput

from porterchain_api.merchant_engine.shopify_one_click import (  # noqa: F401
    connection_payload,
    go_live,
)
from porterchain_api.merchant_engine.shopify_session import can_rebind_shop, rates_status  # noqa: F401

logger = logging.getLogger(__name__)


_booking = MerchantBookingService()


def _encrypt(value: str | None, settings: Settings) -> str | None:
    if not value:
        return None
    return encrypt_signing_secret(value, encryption_key=settings.jwt_secret)


def _decrypt(value: str | None, settings: Settings) -> str | None:
    if not value:
        return None
    return decrypt_signing_secret(value, encryption_key=settings.jwt_secret)


_PICKUP_ADDRESS_TYPES = ("pickup", "warehouse")


def default_pickup_address(
    db: Session,
    merchant_id: str,
    *,
    shop: ShopifyShop | None = None,
) -> SavedAddress | None:
    if shop and getattr(shop, "default_pickup_address_id", None):
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
        .filter(
            SavedAddress.merchant_id == merchant_id,
            SavedAddress.address_type.in_(_PICKUP_ADDRESS_TYPES),
        )
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
    tokens.store_custom_app_token(row, token, settings)
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


def disconnect_shop(db: Session, ctx: MerchantContext, shop_id: str, *, audit: bool = True) -> None:
    shop = (
        db.query(ShopifyShop)
        .filter(ShopifyShop.id == shop_id, ShopifyShop.merchant_id == ctx.merchant.id)
        .first()
    )
    if not shop:
        raise LookupError("shop_not_found")
    _delete_partner_services(shop)
    shop.uninstalled_at = datetime.now(UTC)
    tokens.clear_tokens(shop)
    shop.carrier_service_gid = None
    shop.fulfillment_service_gid = None
    shop.location_gid = None
    if audit:  # merchant self-disconnect was invisible to staff; admin path writes its own row
        from porterchain_api.merchant_engine.shopify_one_click import audit_disconnect

        audit_disconnect(db, ctx, shop)
    db.commit()


def _delete_partner_services(shop: ShopifyShop) -> None:
    """Drop CarrierService and FulfillmentService while the token is still valid."""
    try:
        from porterchain_api.config import get_settings
        from porterchain_api.merchant_engine.shopify_fulfillment_service import delete_partner_services

        delete_partner_services(shop, get_settings())
    except Exception:  # noqa: BLE001
        logger.warning("shopify_partner_delete_failed shop=%s", shop.shop_domain, exc_info=True)


_PRE_PICKUP = {
    OrderState.BOOKED.value,
    OrderState.DISPATCH_READY.value,
    OrderState.DRIVER_ASSIGNED.value,
    OrderState.DRIVER_ACCEPTED.value,
    OrderState.DRIVER_REJECTED.value,
    OrderState.DRIVER_EN_ROUTE.value,
    OrderState.AT_PICKUP.value,
}


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
    token = tokens.access_token_for(shop, settings)
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
    shop_domain: str,
    shop_payload: dict[str, Any],
) -> Merchant:
    """Company for a managed install — never steal another merchant's shop.

    A store already linked keeps its company. Otherwise the shop email may attach
    to a company with no other active Shopify store (blocks email hijack onto an
    established account), else a new onboarding company is created. A portal seat
    later claims it with the embedded app's link token.
    """
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


def _post_install_hooks(shop: ShopifyShop, settings: Settings) -> dict[str, Any]:
    shop.install_hooks = _fo._post_install_hooks(shop, settings)  # request-scoped, not a column
    return shop.install_hooks

# Re-exports kept for existing importers (integration).
from porterchain_api.merchant_engine.shopify_fulfillment_service import push_fulfillment  # noqa: E402, F401
from porterchain_api.merchant_engine.booking_validation import BookingValidationError  # noqa: E402, F401
from porterchain_api.integrations.shopify_orders import order_ids  # noqa: E402, F401
from porterchain_api.integrations.shopify_orders import shipping_address  # noqa: E402, F401
from porterchain_api.merchant_engine.service_area import assert_ontario_booking  # noqa: E402, F401
from porterchain_api.integrations.shopify_orders import customer_slice  # noqa: E402, F401
from porterchain_api.integrations.shopify_orders import is_canada_country  # noqa: E402, F401
from porterchain_api.integrations.shopify_orders import line_item_slice  # noqa: E402, F401
from porterchain_api.integrations.shopify_orders import map_shopify_order  # noqa: E402, F401
from porterchain_api.integrations.shopify_orders import porterchain_shipping_selected  # noqa: E402, F401
from porterchain_api.integrations.shopify_orders import quote_id_from_order  # noqa: E402, F401
from porterchain_api.integrations.shopify_orders import unpaid_non_cod  # noqa: E402, F401
from porterchain_api.merchant_engine.shopify_urls import carrier_rates_url  # noqa: E402, F401
from porterchain_api.merchant_engine.shopify_urls import fulfillment_service_url  # noqa: E402, F401
from porterchain_api.merchant_engine.shopify_urls import webhook_url  # noqa: E402, F401
from porterchain_api.merchant_engine.shopify_payload_ops import _cancel_shopify_fulfillment  # noqa: E402, F401
from porterchain_api.merchant_engine.shopify_fulfillment_service import ingest_fulfillment_order_notification  # noqa: E402, F401
