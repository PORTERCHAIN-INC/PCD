"""4-click Shopify onboarding (behind SHOPIFY_FOUR_CLICK_ONBOARDING_ENABLED).

Click 1 Install, click 2 Approve (both Shopify). Click 3: merchant confirms the
pickup address we prefill from the store's own address (/shop.json — no new
scope). Click 4 "Go live": save pickup, bind it to the shop, generate the FSA
rate card, register the carrier, and return the exact Markets step + deep link.
The account already exists from install (shop owner email); Go live reserves an
owner seat for that email, so the owner just signs in to the portal — no signup, no mail.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from porterchain_api.config import Settings
from porterchain_api.merchant_models import Merchant, SavedAddress
from sqlalchemy.orm import Session

SHIPPING_DEEP_LINK = "shopify://admin/settings/shipping"
MARKETS_STEPS = [
    "Settings → Shipping and delivery → your Canada shipping zone (or market) → Add rate",
    "Choose 'Use carrier or app to calculate rates' → PorterChain → Save",
]


def _shop_row(db: Session, shop_domain: str):
    from porterchain_api.merchant_engine.shopify_session import _active_row

    row = _active_row(db, shop_domain)
    if row is None:
        raise LookupError("shop_not_found")
    return row


def _shop_address(payload: dict[str, Any]) -> dict[str, Any]:
    parts = [
        payload.get("address1"),
        payload.get("address2"),
        payload.get("city"),
        payload.get("province_code") or payload.get("province"),
        payload.get("zip"),
    ]
    return {
        "formatted": ", ".join(str(p).strip() for p in parts if p and str(p).strip()),
        "postal": (payload.get("zip") or "").strip() or None,
        "country": payload.get("country_code"),
        "lat": payload.get("latitude"),
        "lng": payload.get("longitude"),
    }


def prefill(db: Session, settings: Settings, shop_domain: str) -> dict[str, Any]:
    """Click 3 screen data: the store's address, or the saved pickup if one exists."""
    from porterchain_api.merchant_engine import shopify_service as shopify
    from porterchain_api.merchant_engine.shopify_tokens import access_token_for

    row = _shop_row(db, shop_domain)
    saved = shopify.default_pickup_address(db, row.merchant_id, shop=row)
    if saved is not None:
        return {
            "source": "saved",
            "address": {
                "formatted": saved.formatted,
                "postal": saved.postal,
                "lat": saved.lat,
                "lng": saved.lng,
            },
        }
    token = access_token_for(row, settings)
    payload = (
        (shopify._admin_get(shop_domain, token, "/shop.json", settings) or {}).get(
            "shop"
        )
        if token
        else None
    )
    return {"source": "shopify_store", "address": _shop_address(payload or {})}


def go_live(
    db: Session,
    settings: Settings,
    shop_domain: str,
    address: dict[str, Any],
    generate_card: Callable[[Session, str], list] | None = None,
) -> dict[str, Any]:
    """Click 4. Idempotent: re-running reuses the pickup and refreshes the card."""
    from porterchain_api.merchant_engine import shopify_service as shopify
    from porterchain_api.merchant_engine.shopify_session import ensure_carrier_rates
    from porterchain_api.schemas_merchant import AddressInput

    row = _shop_row(db, shop_domain)
    formatted = str(address.get("formatted") or "").strip()
    if not formatted:
        raise ValueError("pickup_address_required")
    addr = shopify._ensure_coords(
        AddressInput(
            formatted=formatted,
            postal=address.get("postal"),
            lat=address.get("lat"),
            lng=address.get("lng"),
        )
    )
    saved = shopify.default_pickup_address(db, row.merchant_id, shop=row)
    if saved is None or saved.formatted != addr.formatted:
        saved = SavedAddress(
            merchant_id=row.merchant_id,
            label="Shopify pickup",
            address_type="pickup",
            formatted=addr.formatted,
            lat=addr.lat,
            lng=addr.lng,
            postal=addr.postal,
            is_default=True,
        )
        db.add(saved)
        db.flush()
    row.default_pickup_address_id = saved.id
    merchant = db.get(Merchant, row.merchant_id)
    owner_email = (merchant.email or "") if merchant else ""
    if merchant is not None and owner_email and not owner_email.endswith(".invalid"):
        # Owner seat reserved by the shop owner's email: signing in to the portal with it
        # claims the account. No email is sent here (no bulk mail, ever).
        from porterchain_api.domain.merchant_states import MerchantRole
        from porterchain_api.merchant_engine.team_service import ensure_merchant_seat

        ensure_merchant_seat(
            db,
            merchant_id=merchant.id,
            email=owner_email,
            role=MerchantRole.OWNER.value,
            audit_action="shopify.owner_seat_reserved",
            commit=False,
        )
    db.commit()
    try:
        card_rows = generate_card(db, row.merchant_id) if generate_card else []
        db.commit()
    except RuntimeError:  # routing down: card regenerates on the next open; carrier still prices by distance
        db.rollback()
        card_rows = []
    rates = ensure_carrier_rates(db, settings, shop_domain)
    return {
        "live": rates == "ready",
        "rates": rates,
        "pickup": {"id": saved.id, "formatted": saved.formatted},
        "rate_card_fsas": len(card_rows),
        "rate_card": "ready" if card_rows else "pending",
        "next_step": {"steps": MARKETS_STEPS, "deep_link": SHIPPING_DEEP_LINK},
        "account": {
            "email": owner_email or None,
            "portal_access": "sign_in_with_shop_email",
        },
    }


def merchant_for_shop(db: Session, shop_domain: str):
    """Linked merchant for an installed shop, or None."""
    from porterchain_api.merchant_models import Merchant

    try:
        row = _shop_row(db, shop_domain)
    except LookupError:
        return None
    return db.get(Merchant, row.merchant_id) if row.merchant_id else None
