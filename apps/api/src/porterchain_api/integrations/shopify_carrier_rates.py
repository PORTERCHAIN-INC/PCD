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


def _parcel_count_from_items(items: list[Any] | None) -> int:
    if not items:
        return 1
    total = 0
    for item in items:
        if not isinstance(item, dict):
            continue
        try:
            qty = int(item.get("quantity") or 1)
        except (TypeError, ValueError):
            qty = 1
        total += max(1, qty)
    return max(total, 1)


def _dimensions_from_items(items: list[Any] | None) -> dict[str, float] | None:
    """Best-effort dims from Shopify line properties (inches → cm for engine)."""
    if not items:
        return None
    # Use the largest single line's L×W×H when present on properties.
    best: tuple[float, float, float] | None = None
    for item in items:
        if not isinstance(item, dict):
            continue
        props = item.get("properties")
        if not isinstance(props, list):
            continue
        got: dict[str, float] = {}
        for prop in props:
            if not isinstance(prop, dict):
                continue
            name = str(prop.get("name") or "").strip().lower()
            try:
                val = float(prop.get("value"))
            except (TypeError, ValueError):
                continue
            if name in ("length", "width", "height", "l", "w", "h"):
                key = {"l": "length", "w": "width", "h": "height"}.get(name, name)
                got[key] = val
        if len(got) >= 2:
            dims = (
                float(got.get("length") or 0),
                float(got.get("width") or 0),
                float(got.get("height") or 0),
            )
            if best is None or sum(dims) > sum(best):
                best = dims
    if not best:
        return None
    # Shopify furniture props are typically inches; engine SizeTier use cm when unit=cm.
    return {
        "length": best[0] * 2.54,
        "width": best[1] * 2.54,
        "height": best[2] * 2.54,
    }


def resolve_shopify_vehicle(
    merchant: Merchant,
    *,
    dropoff: AddressInput | None = None,
    dimensions: dict[str, float] | None = None,
) -> str:
    """
    cargo_van by default; compact-class when schedule.compact is on, parcel
    fits max_packed_inches, and dest FSA has a compact vehicle row (checked at
    quote time via engine — here we only gate on packed size).
    """
    from porterchain_pricing.policy import policy_from_config

    policy = policy_from_config(getattr(merchant, "pricing_config", None) or {})
    compact = policy.schedule.compact
    if not compact.enabled:
        return "cargo_van"
    # Without dims, stay on van (furniture default for Kaylulu).
    if not dimensions:
        return "cargo_van"
    # dimensions are cm; packed limit is inches.
    sides_in = sorted(
        (
            float(dimensions.get("length") or 0) / 2.54,
            float(dimensions.get("width") or 0) / 2.54,
            float(dimensions.get("height") or 0) / 2.54,
        ),
        reverse=True,
    )
    lim = sorted(
        (float(compact.max_packed_inches[0]), float(compact.max_packed_inches[1])),
        reverse=True,
    )
    if sides_in[0] <= lim[0] + 1e-6 and sides_in[1] <= lim[1] + 1e-6:
        classes = compact.vehicle_classes or ["sedan_suv"]
        return str(classes[0])
    return "cargo_van"


def apply_shopify_book_vehicle(merchant: Merchant, body: Any, payload: dict[str, Any]) -> Any:
    """Align book vehicle_class with carrier quote resolve (Quote≡Book). Never raises."""
    try:
        line_items = (
            payload.get("line_items") if isinstance(payload.get("line_items"), list) else []
        )
        dims = _dimensions_from_items(line_items)
        vehicle = resolve_shopify_vehicle(merchant, dropoff=body.dropoff, dimensions=dims)
        from porterchain_api.domain.customer_goods import persist_vehicle_class

        return body.model_copy(update={"vehicle_class": persist_vehicle_class(vehicle)})
    except Exception:  # noqa: BLE001
        logger.exception(
            "shopify_book_vehicle_resolve_failed merchant=%s",
            getattr(merchant, "id", None),
        )
        return body


def quote_merchant_rate(
    db: Session,
    merchant: Merchant,
    *,
    pickup: AddressInput,
    dropoff: AddressInput,
    weight_kg: float | None,
    items: list[Any] | None = None,
    vehicle_class: str | None = None,
) -> tuple[int, dict[str, Any]]:
    """Same engine path as MerchantBookingService.create_shipment."""
    pickup_geo = _to_geo(pickup)
    dropoff_geo = _to_geo(dropoff)
    distance, duration_seconds, routing_source = resolve_route_distance(pickup_geo, dropoff_geo)
    dims = _dimensions_from_items(items)
    vehicle = vehicle_class or resolve_shopify_vehicle(
        merchant, dropoff=dropoff, dimensions=dims
    )
    request = PricingRequest(
        pickup=pickup_geo,
        dropoff=dropoff_geo,
        vehicle_class=vehicle,
        package_type="looseParcel",
        service_type="same_day",
        weight_kg=weight_kg,
        dimensions=dims,
        schedule_mode="now",
        is_rush=True,
        distance_meters=distance,
        estimated_duration_minutes=int(duration_seconds / 60) if duration_seconds else None,
        routing_source=routing_source,
        channel="merchant",
        merchant_id=merchant.id,
        parcel_count=_parcel_count_from_items(items),
    )
    breakdown = get_pricing_service(db).calculate_merchant(request)
    meta = dict(getattr(breakdown, "metadata", None) or {})
    if meta.get("fsa_refused"):
        return 0, _breakdown_dict(breakdown)
    return int(breakdown.final_cents), _breakdown_dict(breakdown)


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


def find_quote_by_hash(
    db: Session,
    *,
    shop_id: str,
    request_hash: str,
) -> ShopifyRateQuote | None:
    now = datetime.now(UTC)
    return (
        db.query(ShopifyRateQuote)
        .filter(
            ShopifyRateQuote.shop_id == shop_id,
            ShopifyRateQuote.request_hash == request_hash,
            ShopifyRateQuote.expires_at >= now,
        )
        .order_by(ShopifyRateQuote.created_at.desc())
        .first()
    )


def _delivery_window() -> tuple[str, str]:
    from zoneinfo import ZoneInfo

    now = datetime.now(ZoneInfo("America/Toronto"))
    earliest = now + timedelta(hours=2)
    latest = now + timedelta(hours=10)
    fmt = "%Y-%m-%d %H:%M:%S %z"
    return earliest.strftime(fmt), latest.strftime(fmt)


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

    from porterchain_api.integrations.shopify_orders import is_canada_country

    destination = rate_in.get("destination") if isinstance(rate_in.get("destination"), dict) else None
    origin = rate_in.get("origin") if isinstance(rate_in.get("origin"), dict) else None
    dest_country = None
    if isinstance(destination, dict):
        dest_country = destination.get("country") or destination.get("country_code")
    origin_country = None
    if isinstance(origin, dict):
        origin_country = origin.get("country") or origin.get("country_code")
    if not is_canada_country(dest_country) or not is_canada_country(origin_country):
        return _EMPTY

    pickup_row = default_pickup_address(db, merchant.id, shop=shop)
    if not pickup_row:
        logger.info("shopify_carrier_no_pickup shop=%s", getattr(shop, "shop_domain", shop.id))
        return _EMPTY
    default_pickup = _ensure_geo(address_from_saved(pickup_row))

    dropoff_raw = _shopify_address_to_input(destination)
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

    pickup = default_pickup
    origin_input = _shopify_address_to_input(origin)
    if origin_input is not None and (origin_input.postal or origin_input.formatted):
        origin_err = service_area_error("origin", origin_input)
        if origin_err:
            logger.info(
                "shopify_carrier_origin_out_of_area shop=%s err=%s",
                getattr(shop, "shop_domain", shop.id),
                origin_err,
            )
            return _EMPTY
        pickup = _ensure_geo(origin_input)

    items = rate_in.get("items") if isinstance(rate_in.get("items"), list) else []
    weight_kg = _weight_kg_from_items(items)

    t0 = time.perf_counter()
    try:
        cents, breakdown = quote_merchant_rate(
            db,
            merchant,
            pickup=pickup,
            dropoff=dropoff,
            weight_kg=weight_kg,
            items=items,
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

    if cents <= 0 or (breakdown.get("metadata") or {}).get("fsa_refused"):
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

    desc = "Same-day local capacity"
    min_delivery, max_delivery = _delivery_window()
    rate: dict[str, Any] = {
        "service_name": "PorterChain Same Day",
        "service_code": "porterchain_same_day",
        "total_price": str(cents),
        "currency": currency,
        "description": desc,
        "phone_required": True,
        "min_delivery_date": min_delivery,
        "max_delivery_date": max_delivery,
    }
    if quote_id:
        rate["metafields"] = [
            {
                "namespace": "porterchain",
                "key": "quote_id",
                "value": quote_id,
                "type": "single_line_text_field",
            }
        ]

    try:
        from porterchain_api.merchant_engine.commerce_metrics import note_commerce_event

        note_commerce_event("shopify_quote", "ok")
    except Exception:
        pass

    return {"rates": [rate]}
