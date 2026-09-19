"""Shopify Carrier Service (P4.4) — checkout rate shopping via PricingEngine."""

from __future__ import annotations

import hashlib
import json
import logging
import time
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.config import Settings
from porterchain_api.domain.merchant_states import MerchantStatus
from porterchain_api.integrations.shopify_hmac import verify_webhook_hmac
from porterchain_api.merchant_engine.service_area import service_area_error
from porterchain_api.merchant_engine.shopify_service import (
    _active_shop,
    _decrypt,
    address_from_saved,
    default_pickup_address,
)
from porterchain_api.merchant_models import Merchant, ShopifyRateQuote, ShopifyShop
from porterchain_api.pricing_engine import get_pricing_service
from porterchain_api.schemas_merchant import AddressInput
from porterchain_api.services.routing import resolve_route_distance
from porterchain_pricing import GeoPoint, PricingRequest

logger = logging.getLogger(__name__)

QUOTE_TTL = timedelta(minutes=30)
_EMPTY = {"rates": []}


def _carrier_hmac_secrets(db: Session, settings: Settings, shop_domain: str | None) -> list[str]:
    """App secret + optional per-shop webhook secret (same pool as order webhooks)."""
    secrets: list[str] = []
    shop = _active_shop(db, shop_domain) if shop_domain else None
    if shop and shop.encrypted_webhook_secret:
        stored = _decrypt(shop.encrypted_webhook_secret, settings)
        if stored:
            secrets.append(stored)
    app_secret = getattr(settings, "shopify_api_secret", None) or ""
    if app_secret:
        secrets.append(app_secret)
    return secrets


def _postal_norm(raw: str | None) -> str:
    return "".join(c for c in (raw or "").upper() if c.isalnum())


def _shopify_address_to_input(addr: dict[str, Any] | None) -> AddressInput | None:
    if not isinstance(addr, dict):
        return None
    postal = str(addr.get("postal_code") or addr.get("zip") or "").strip()
    parts = [
        addr.get("address1"),
        addr.get("address2"),
        addr.get("city"),
        addr.get("province"),
        postal,
        addr.get("country"),
    ]
    formatted = ", ".join(str(p).strip() for p in parts if p)
    if not formatted and not postal:
        return None
    lat = addr.get("latitude")
    lng = addr.get("longitude")
    try:
        lat_f = float(lat) if lat is not None else None
        lng_f = float(lng) if lng is not None else None
    except (TypeError, ValueError):
        lat_f, lng_f = None, None
    return AddressInput(
        formatted=formatted or postal,
        postal=postal or None,
        lat=lat_f,
        lng=lng_f,
    )


def _ensure_geo(addr: AddressInput) -> AddressInput:
    if addr.lat is not None and addr.lng is not None:
        return addr
    from porterchain_api.merchant_engine.import_geocode import geocode_stop

    geo = geocode_stop(
        address=addr.formatted,
        postal=addr.postal,
        lat=addr.lat,
        lng=addr.lng,
    )
    if geo.lat is None or geo.lng is None:
        return addr
    return addr.model_copy(
        update={
            "lat": geo.lat,
            "lng": geo.lng,
            "formatted": geo.formatted or addr.formatted,
        }
    )


def _to_geo(addr: AddressInput) -> GeoPoint:
    return GeoPoint(
        lat=addr.lat,
        lng=addr.lng,
        formatted=addr.formatted or "",
        postal=addr.postal or "",
    )


def _weight_kg_from_items(items: list[Any] | None) -> float | None:
    if not items:
        return None
    total_g = 0
    for item in items:
        if not isinstance(item, dict):
            continue
        try:
            grams = int(item.get("grams") or 0)
            qty = int(item.get("quantity") or 1)
        except (TypeError, ValueError):
            continue
        total_g += max(0, grams) * max(1, qty)
    if total_g <= 0:
        return None
    return total_g / 1000.0


def _request_hash(
    *,
    shop_id: str,
    merchant_id: str,
    pickup_postal: str,
    dropoff_postal: str,
    weight_kg: float | None,
) -> str:
    payload = {
        "shop_id": shop_id,
        "merchant_id": merchant_id,
        "pickup": _postal_norm(pickup_postal),
        "dropoff": _postal_norm(dropoff_postal),
        "weight_kg": round(weight_kg, 3) if weight_kg is not None else None,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()


def _breakdown_dict(breakdown: Any) -> dict[str, Any]:
    items = getattr(breakdown, "items", None) or []
    return {
        "final_cents": int(getattr(breakdown, "final_cents", 0) or 0),
        "subtotal_cents": int(getattr(breakdown, "subtotal_cents", 0) or 0),
        "tax_cents": int(getattr(breakdown, "tax_cents", 0) or 0),
        "contract_id": getattr(breakdown, "contract_id", None),
        "items": [
            {
                "code": getattr(i, "code", ""),
                "label": getattr(i, "label", ""),
                "amount_cents": int(getattr(i, "amount_cents", 0) or 0),
            }
            for i in items
        ],
        "metadata": dict(getattr(breakdown, "metadata", None) or {}),
    }


def persist_rate_quote(
    db: Session,
    *,
    shop: ShopifyShop,
    merchant_id: str,
    request_hash: str,
    total_cents: int,
    currency: str,
    breakdown: dict[str, Any],
    pickup_postal: str | None,
    dropoff_postal: str | None,
    weight_kg: float | None,
) -> ShopifyRateQuote:
    row = ShopifyRateQuote(
        shop_id=shop.id,
        merchant_id=merchant_id,
        request_hash=request_hash,
        total_cents=int(total_cents),
        currency=(currency or "CAD").upper()[:8],
        breakdown=breakdown,
        pickup_postal=pickup_postal,
        dropoff_postal=dropoff_postal,
        weight_kg=str(weight_kg) if weight_kg is not None else None,
        expires_at=datetime.now(UTC) + QUOTE_TTL,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def find_quote_for_book(
    db: Session,
    *,
    shop_id: str,
    dropoff_postal: str | None,
    weight_kg: float | None = None,
) -> ShopifyRateQuote | None:
    """Best-effort match for webhook book — newest non-expired quote for dest FSA."""
    now = datetime.now(UTC)
    q = (
        db.query(ShopifyRateQuote)
        .filter(
            ShopifyRateQuote.shop_id == shop_id,
            ShopifyRateQuote.expires_at >= now,
        )
        .order_by(ShopifyRateQuote.created_at.desc())
    )
    dest = _postal_norm(dropoff_postal)
    rows = q.limit(20).all()
    if not rows:
        return None
    if dest:
        for row in rows:
            if _postal_norm(row.dropoff_postal)[:3] == dest[:3]:
                if weight_kg is None or row.weight_kg is None:
                    return row
                try:
                    if abs(float(row.weight_kg) - float(weight_kg)) < 0.05:
                        return row
                except (TypeError, ValueError):
                    return row
    return rows[0]


def quote_merchant_rate(
    db: Session,
    merchant: Merchant,
    *,
    pickup: AddressInput,
    dropoff: AddressInput,
    weight_kg: float | None,
) -> tuple[int, dict[str, Any]]:
    """Same engine path as MerchantBookingService.create_shipment."""
    pickup_geo = _to_geo(pickup)
    dropoff_geo = _to_geo(dropoff)
    distance, duration_seconds, routing_source = resolve_route_distance(pickup_geo, dropoff_geo)
    request = PricingRequest(
        pickup=pickup_geo,
        dropoff=dropoff_geo,
        vehicle_class="cargo_van",
        package_type="looseParcel",
        service_type="same_day",
        weight_kg=weight_kg,
        schedule_mode="now",
        is_rush=True,
        distance_meters=distance,
        estimated_duration_minutes=int(duration_seconds / 60) if duration_seconds else None,
        routing_source=routing_source,
        channel="merchant",
        merchant_id=merchant.id,
    )
    breakdown = get_pricing_service(db).calculate_merchant(request)
    return int(breakdown.final_cents), _breakdown_dict(breakdown)


def carrier_service_rates(
    db: Session,
    settings: Settings,
    *,
    raw_body: bytes,
    hmac_header: str | None,
    shop_domain: str | None,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """
    Shopify CarrierService callback.

    Handshake: Shop-Domain → ShopifyShop → merchant.
    Price: PricingEngine.calculate_merchant (FSA|distance + contract) — Quote≡Book.
    """
    secrets = _carrier_hmac_secrets(db, settings, shop_domain)
    if not secrets:
        raise PermissionError("hmac_not_configured")
    if not verify_webhook_hmac(raw_body, hmac_header, secrets):
        raise PermissionError("invalid_hmac")

    shop = _active_shop(db, shop_domain) if shop_domain else None
    if not shop or not shop.merchant_id:
        raise LookupError("shop_not_connected")
    merchant = db.get(Merchant, shop.merchant_id)
    if not merchant:
        raise LookupError("merchant_not_found")
    if merchant.status != MerchantStatus.ACTIVE.value:
        return _EMPTY

    rate_in = payload.get("rate") if isinstance(payload.get("rate"), dict) else payload
    if not isinstance(rate_in, dict):
        rate_in = {}
    currency = str(rate_in.get("currency") or "CAD").upper()

    pickup_row = default_pickup_address(db, merchant.id, shop=shop)
    if not pickup_row:
        logger.info("shopify_carrier_no_pickup shop=%s", getattr(shop, "shop_domain", shop.id))
        return _EMPTY
    pickup = _ensure_geo(address_from_saved(pickup_row))

    dropoff_raw = _shopify_address_to_input(
        rate_in.get("destination") if isinstance(rate_in.get("destination"), dict) else None
    )
    if not dropoff_raw:
        return _EMPTY
    area_err = service_area_error("destination", dropoff_raw)
    if area_err:
        logger.info(
            "shopify_carrier_out_of_area shop=%s err=%s",
            getattr(shop, "shop_domain", shop.id),
            area_err,
        )
        return _EMPTY
    dropoff = _ensure_geo(dropoff_raw)

    items = rate_in.get("items") if isinstance(rate_in.get("items"), list) else []
    weight_kg = _weight_kg_from_items(items)

    t0 = time.perf_counter()
    try:
        cents, breakdown = quote_merchant_rate(
            db, merchant, pickup=pickup, dropoff=dropoff, weight_kg=weight_kg
        )
    except Exception:  # noqa: BLE001 — checkout must not 500; omit rates
        logger.exception(
            "shopify_carrier_pricing_failed shop=%s", getattr(shop, "shop_domain", shop.id)
        )
        try:
            from porterchain_api.merchant_engine.commerce_metrics import note_commerce_event

            note_commerce_event("shopify_quote", "error")
        except Exception:
            pass
        return _EMPTY
    finally:
        try:
            from porterchain_api.merchant_engine.commerce_metrics import note_quote_latency

            note_quote_latency((time.perf_counter() - t0) * 1000.0)
        except Exception:
            pass

    if cents <= 0:
        return _EMPTY

    req_hash = _request_hash(
        shop_id=shop.id,
        merchant_id=merchant.id,
        pickup_postal=pickup.postal or "",
        dropoff_postal=dropoff.postal or "",
        weight_kg=weight_kg,
    )
    try:
        quote = persist_rate_quote(
            db,
            shop=shop,
            merchant_id=merchant.id,
            request_hash=req_hash,
            total_cents=cents,
            currency=currency,
            breakdown=breakdown,
            pickup_postal=pickup.postal,
            dropoff_postal=dropoff.postal,
            weight_kg=weight_kg,
        )
        quote_id = quote.id
    except Exception:  # noqa: BLE001
        logger.exception(
            "shopify_carrier_quote_persist_failed shop=%s",
            getattr(shop, "shop_domain", shop.id),
        )
        quote_id = None

    desc = "Same-day local capacity — PorterChain"
    if quote_id:
        desc = f"{desc} (quote {quote_id[:8]})"

    try:
        from porterchain_api.merchant_engine.commerce_metrics import note_commerce_event

        note_commerce_event("shopify_quote", "ok")
    except Exception:
        pass

    return {
        "rates": [
            {
                "service_name": "PorterChain Same Day",
                "service_code": "porterchain_same_day",
                "total_price": str(cents),
                "currency": currency,
                "description": desc,
            }
        ]
    }
