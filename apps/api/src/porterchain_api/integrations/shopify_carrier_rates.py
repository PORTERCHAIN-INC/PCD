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
from porterchain_api.merchant_engine.service_area import (
    fsa_from_address,
    merchant_coverage_fsas,
    service_area_error,
)
from porterchain_api.merchant_engine.shopify_service import (
    _active_shop,
    _decrypt,
    address_from_saved,
    default_pickup_address,
)
from porterchain_api.merchant_engine.shopify_one_click import ensure_shop_pickup_bound
from porterchain_api.merchant_models import Merchant, ShopifyRateQuote, ShopifyShop
from porterchain_api.pricing_engine import get_pricing_service
from porterchain_api.schemas_merchant import AddressInput
from porterchain_api.services.routing import resolve_route_distance
from porterchain_pricing import GeoPoint, ParcelSpec, PricingRequest

logger = logging.getLogger(__name__)

QUOTE_TTL = timedelta(minutes=30)


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


def _item_dims_in(item: Any) -> tuple[float, float, float] | None:
    """L×W×H (inches) from a line's `length`/`width`/`height` properties, if present."""
    props = item.get("properties") if isinstance(item, dict) else None
    if not isinstance(props, list):
        return None
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
    if len(got) < 2:
        return None
    return (
        float(got.get("length") or 0),
        float(got.get("width") or 0),
        float(got.get("height") or 0),
    )


def _in_to_cm(dims: tuple[float, float, float]) -> dict[str, float]:
    # Shopify furniture props are typically inches; the engine bills in cm.
    return {"length": dims[0] * 2.54, "width": dims[1] * 2.54, "height": dims[2] * 2.54}


def _dimensions_from_items(items: list[Any] | None) -> dict[str, float] | None:
    """Best-effort dims from Shopify line properties (inches → cm for engine)."""
    best: tuple[float, float, float] | None = None
    for item in items or []:
        dims = _item_dims_in(item)
        if dims and (best is None or sum(dims) > sum(best)):
            best = dims
    return _in_to_cm(best) if best else None


#: Line-item property names a store can use for "this item ships in N boxes".
BOX_PROPERTY_NAMES = frozenset({"boxes", "_boxes", "boxes per item", "boxes_per_item", "box count", "box_count"})
MAX_BOXES_PER_ITEM = 20


def item_boxes(item: Any) -> int:
    """Boxes per unit from a line's properties (default 1)."""
    props = item.get("properties") if isinstance(item, dict) else None
    if not isinstance(props, list):
        return 1
    for prop in props:
        if not isinstance(prop, dict):
            continue
        if str(prop.get("name") or "").strip().lower() in BOX_PROPERTY_NAMES:
            try:
                return max(1, min(int(float(prop.get("value"))), MAX_BOXES_PER_ITEM))
            except (TypeError, ValueError):
                return 1
    return 1


def _line_key(item: dict[str, Any], pos: int) -> str:
    raw = item.get("id") or item.get("variant_id") or item.get("sku") or f"line{pos}"
    return str(raw)[:48]


def _shipped_units(items: list[Any] | None):
    """(line position, line, grams per unit, qty, dims in inches, boxes) for shippable lines."""
    for pos, item in enumerate(items or [], start=1):
        if not isinstance(item, dict) or item.get("requires_shipping") is False:
            continue
        try:
            grams = int(item.get("grams") or 0)
            qty = max(int(item.get("quantity") or 1), 1)
        except (TypeError, ValueError):
            continue
        yield pos, item, grams, qty, _item_dims_in(item), item_boxes(item)


def parcels_from_items(items: list[Any] | None) -> list[ParcelSpec]:
    """
    One parcel per shipped unit, with that line's grams and dimensions.

    Contract schedules bill per parcel; Shopify sends one line per variant with
    a quantity and per-unit grams, so each unit is treated as its own packed
    parcel. Lines without grams or size properties stay unknown (standard).

    A line whose `boxes` property is N > 1 ships each unit in N boxes: N parcels
    sharing an `item_key` (weight split evenly). Price-book merchants with
    multi-box ON bill them as one item; contracts bill every box.
    """
    out: list[ParcelSpec] = []
    for pos, item, grams, qty, dims, boxes in _shipped_units(items):
        if boxes == 1:
            spec = ParcelSpec(
                stop_index=0,
                weight_kg=grams / 1000.0 if grams > 0 else None,
                dimensions=_in_to_cm(dims) if dims else None,
            )
            out.extend([spec] * qty)
            continue
        each_kg = (grams / 1000.0 / boxes) if grams > 0 else None
        for unit in range(1, qty + 1):
            key = f"{_line_key(item, pos)}:{unit}"
            out.extend(
                ParcelSpec(
                    stop_index=0,
                    weight_kg=each_kg,
                    dimensions=_in_to_cm(dims) if dims else None,
                    item_key=key,
                )
                for _ in range(boxes)
            )
    return out


def packages_from_items(items: list[Any] | None) -> list[dict[str, Any]] | None:
    """
    Booking packages for an order with multi-box lines (same split as
    `parcels_from_items`, so the booked price matches checkout). None when no
    line declares boxes — the order keeps today's single default package.
    """
    units = list(_shipped_units(items))
    if not any(boxes > 1 for *_rest, boxes in units):
        return None
    out: list[dict[str, Any]] = []
    for pos, item, grams, qty, dims, boxes in units:
        title = str(item.get("title") or item.get("name") or "Item").strip()[:120]
        cm = _in_to_cm(dims) if dims else {}
        base = {
            "name": title,
            "sku": str(item.get("sku") or "").strip() or None,
            "length_cm": cm.get("length"),
            "width_cm": cm.get("width"),
            "height_cm": cm.get("height"),
        }
        for unit in range(1, qty + 1):
            key = f"{_line_key(item, pos)}:{unit}"
            for n in range(1, boxes + 1):
                out.append(
                    {
                        **base,
                        "weight_kg": (grams / 1000.0 / boxes) if grams > 0 else None,
                        "item_key": key if boxes > 1 else None,
                        "item_label": title if boxes > 1 else None,
                        "box_index": n if boxes > 1 else None,
                        "box_count": boxes if boxes > 1 else None,
                    }
                )
    return out[:200]


def resolve_shopify_vehicle(
    merchant: Merchant,
    *,
    dropoff: AddressInput | None = None,
    dimensions: dict[str, float] | None = None,
    items: list[Any] | None = None,
) -> str:
    """
    cargo_van by default; compact-class when schedule.compact is on and the
    parcel fits max_packed_inches.

    A merchant on a contract schedule is compact only when every parcel's
    packed size is known and fits AND the destination is in the compact
    territory — otherwise the whole load is van.
    """
    from porterchain_pricing.policy import MODEL_FSA, policy_from_config

    policy = policy_from_config(getattr(merchant, "pricing_config", None) or {})
    if policy.schedule.contract_schedule and getattr(merchant, "pricing_model", None) == MODEL_FSA:
        from porterchain_pricing.contract_schedule import load_contract_schedule

        terms = load_contract_schedule(policy.schedule.contract_schedule)
        if terms is not None:
            return _contract_vehicle(terms, dropoff, items)
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


def _contract_vehicle(terms: Any, dropoff: AddressInput | None, items: list[Any] | None) -> str:
    from porterchain_pricing.components.size_weight import parse_dimensions_cm
    from porterchain_pricing.contract_schedule import fits, footprint_cm

    dest = fsa_from_address(dropoff)[:3] if dropoff else ""
    parcels = parcels_from_items(items)
    if not parcels or not terms.in_compact_territory(dest):
        return "cargo_van"
    for parcel in parcels:
        fp = footprint_cm(parse_dimensions_cm(parcel.dimensions))
        if fp is None or not fits(fp, terms.compact.max_packed_cm):
            return "cargo_van"
    return str(terms.compact.vehicle_classes[0])


def apply_shopify_book_vehicle(merchant: Merchant, body: Any, payload: dict[str, Any]) -> Any:
    """Align book vehicle_class with carrier quote resolve (Quote≡Book). Never raises."""
    try:
        line_items = (
            payload.get("line_items") if isinstance(payload.get("line_items"), list) else []
        )
        dims = _dimensions_from_items(line_items)
        vehicle = resolve_shopify_vehicle(
            merchant, dropoff=body.dropoff, dimensions=dims, items=line_items
        )
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
        merchant, dropoff=dropoff, dimensions=dims, items=items
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
        parcel_count=max(_parcel_count_from_items(items), len(parcels_from_items(items))),
        parcels=parcels_from_items(items),
    )
    breakdown = get_pricing_service(db).calculate_merchant(request)
    # A refused FSA miss finalizes at 0; caller turns that into empty rates.
    return int(breakdown.final_cents), _breakdown_dict(breakdown)


def _request_hash(
    *,
    shop_id: str,
    merchant_id: str,
    dropoff_postal: str,
    weight_kg: float | None,
) -> str:
    """Match key for checkout ↔ book.

    Shop + destination (+ weight), not ship-from postal. Checkout may price from a
    Shopify origin while book starts from the saved warehouse — those must still
    match. Pickup is stored on the quote snapshot and reused only when the quote
    itself is a trusted match (bound id / hash / dest FSA).
    """
    payload = {
        "shop_id": shop_id,
        "merchant_id": merchant_id,
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
    """Newest non-expired quote for this shop whose destination FSA matches.

    Never falls back to an unrelated destination — that used to hand the wrong
    checkout pickup to multi-location shops (pricing-audit-v2 §1).
    """
    dest = _postal_norm(dropoff_postal)
    if not dest:
        return None
    now = datetime.now(UTC)
    rows = (
        db.query(ShopifyRateQuote)
        .filter(
            ShopifyRateQuote.shop_id == shop_id,
            ShopifyRateQuote.expires_at >= now,
        )
        .order_by(ShopifyRateQuote.created_at.desc())
        .limit(20)
        .all()
    )
    for row in rows:
        if _postal_norm(row.dropoff_postal)[:3] != dest[:3]:
            continue
        if weight_kg is None or row.weight_kg is None:
            return row
        try:
            if abs(float(row.weight_kg) - float(weight_kg)) < 0.05:
                return row
        except (TypeError, ValueError):
            return row
    return None


def quote_usable_for_order(
    quote: Any,
    *,
    shop_id: str,
    dropoff_postal: str | None,
) -> bool:
    """True when a bound / hashed quote still belongs to this shop + destination."""
    if quote is None:
        return False
    if getattr(quote, "shop_id", None) != shop_id:
        return False
    expires = getattr(quote, "expires_at", None)
    if expires is not None:
        exp = expires if expires.tzinfo else expires.replace(tzinfo=UTC)
        if exp < datetime.now(UTC):
            return False
    dest = _postal_norm(dropoff_postal)
    q_dest = _postal_norm(getattr(quote, "dropoff_postal", None))
    if dest and q_dest and q_dest[:3] != dest[:3]:
        return False
    return True


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


#: Engine prices are CAD; Shopify converts to the buyer's market currency.
RATE_CURRENCY = "CAD"


def _checkout_promise(db: Session, dropoff: Any) -> Any:
    """Promise from super-admin cut-off / wave settings; None keeps the fixed window."""
    from porterchain_api.platform.delivery_promise import checkout_promise

    dest = fsa_from_address(dropoff)[:3] if dropoff else ""
    return checkout_promise(db, dest_fsa=dest or None)


def _delivery_window() -> tuple[str, str]:
    from zoneinfo import ZoneInfo

    now = datetime.now(ZoneInfo("America/Toronto"))
    earliest = now + timedelta(hours=2)
    latest = now + timedelta(hours=10)
    fmt = "%Y-%m-%d %H:%M:%S %z"
    return earliest.strftime(fmt), latest.strftime(fmt)


def _country(addr: dict[str, Any] | None) -> str:
    if not isinstance(addr, dict):
        return ""
    return str(addr.get("country") or addr.get("country_code") or "").strip().upper()[:8]


def _empty(shop: Any, reason: str, **ctx: Any) -> dict[str, Any]:
    """Empty rates + one structured line. Context is codes / FSA / status only."""
    extra = "".join(f" {k}={v}" for k, v in ctx.items() if v not in (None, ""))
    logger.info(
        "shopify_carrier_empty shop=%s reason=%s%s",
        getattr(shop, "shop_domain", None) or getattr(shop, "id", None),
        reason,
        extra,
    )
    return {"rates": []}


def _resolve_origin(origin: dict[str, Any] | None) -> tuple[AddressInput | None, str | None]:
    """
    Shopify ship-from, used only when Canadian and inside the GTA ±150 km tile
    (same `service_area_error` gate as destination). Otherwise returns the
    fallback reason; the caller quotes from the merchant's PorterChain pickup.
    """
    from porterchain_api.integrations.shopify_orders import is_canada_country

    if not isinstance(origin, dict):
        return None, "origin_missing"
    if not is_canada_country(_country(origin)):
        return None, "origin_non_canada"
    if not any(origin.get(k) for k in ("postal_code", "zip", "address1", "city")):
        return None, "origin_missing"
    origin_input = _shopify_address_to_input(origin)
    if origin_input is None:
        return None, "origin_missing"
    if service_area_error("origin", origin_input):
        return None, "origin_out_of_area"
    return _ensure_geo(origin_input), None


#: Where a Shopify pickup came from — stored on the rate quote so book can reuse it.
PICKUP_SOURCE_SHOPIFY_ORIGIN = "shopify_origin"
PICKUP_SOURCE_PORTERCHAIN = "porterchain_pickup"


def resolve_shopify_pickup(
    default_pickup: AddressInput,
    origin: dict[str, Any] | None,
) -> tuple[AddressInput, str, str | None]:
    """
    The one pickup rule for Shopify checkout AND order book.

    Shopify ship-from when it is Canadian and inside the GTA ±150 km tile;
    otherwise the merchant's saved PorterChain pickup. Returns
    (pickup, source, fallback_reason). Book passes the checkout quote's stored
    pickup when it has one (see `pickup_from_rate_quote`), else origin=None,
    which resolves to the saved pickup — the same answer checkout gave when
    Shopify's ship-from was unusable.
    """
    origin_pickup, fallback = _resolve_origin(origin)
    if origin_pickup is not None:
        return origin_pickup, PICKUP_SOURCE_SHOPIFY_ORIGIN, None
    return default_pickup, PICKUP_SOURCE_PORTERCHAIN, fallback


def _pickup_snapshot(pickup: AddressInput, source: str) -> dict[str, Any]:
    return {
        "formatted": pickup.formatted,
        "postal": pickup.postal,
        "lat": pickup.lat,
        "lng": pickup.lng,
        "source": source,
    }


def pickup_from_rate_quote(quote: Any) -> tuple[AddressInput, str] | None:
    """Pickup the checkout quote priced from, when still usable for booking."""
    if quote is None:
        return None
    expires = getattr(quote, "expires_at", None)
    if expires is not None:
        exp = expires if expires.tzinfo else expires.replace(tzinfo=UTC)
        if exp < datetime.now(UTC):
            return None
    breakdown = getattr(quote, "breakdown", None)
    snap = breakdown.get("pickup") if isinstance(breakdown, dict) else None
    if not isinstance(snap, dict) or not snap.get("formatted"):
        return None
    try:
        addr = AddressInput(
            formatted=str(snap.get("formatted") or ""),
            postal=snap.get("postal") or None,
            lat=float(snap["lat"]) if snap.get("lat") is not None else None,
            lng=float(snap["lng"]) if snap.get("lng") is not None else None,
        )
    except (TypeError, ValueError):
        return None
    if service_area_error("pickup", addr):
        return None
    return addr, str(snap.get("source") or PICKUP_SOURCE_PORTERCHAIN)


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
    # Signed by our app but the store is uninstalled / unlinked: checkout gets no
    # PorterChain option, never an error (Shopify shows 4xx/5xx as rate failures).
    if not shop or not shop.merchant_id:
        return _empty(shop_domain, "shop_not_connected")
    merchant = db.get(Merchant, shop.merchant_id)
    if not merchant:
        return _empty(shop, "merchant_not_found")
    if merchant.status != MerchantStatus.ACTIVE.value:
        return _empty(shop, "merchant_inactive", status=merchant.status)

    rate_in = payload.get("rate") if isinstance(payload.get("rate"), dict) else payload
    if not isinstance(rate_in, dict):
        rate_in = {}
    # Shopify sends the shop's base currency here, whatever market the buyer is in,
    # and converts a returned rate into the buyer's presentment currency. The engine
    # prices in CAD, so the rate is always labelled CAD (a USD-base shop used to get
    # a CAD amount labelled USD).
    request_currency = str(rate_in.get("currency") or "CAD").upper()[:8]
    currency = RATE_CURRENCY

    from porterchain_api.integrations.shopify_orders import is_canada_country

    destination = rate_in.get("destination") if isinstance(rate_in.get("destination"), dict) else None
    origin = rate_in.get("origin") if isinstance(rate_in.get("origin"), dict) else None
    dest_country = _country(destination)
    if not is_canada_country(dest_country):
        return _empty(shop, "dest_non_canada", dest_country=dest_country)

    pickup_row = default_pickup_address(db, merchant.id, shop=shop)
    if not pickup_row:
        return _empty(shop, "no_pickup")
    shop = ensure_shop_pickup_bound(db, shop, address=pickup_row)
    default_pickup = _ensure_geo(address_from_saved(pickup_row))

    dropoff_raw = _shopify_address_to_input(destination)
    if not dropoff_raw:
        return _empty(shop, "dropoff_missing", dest_country=dest_country)
    if service_area_error("destination", dropoff_raw, merchant_coverage_fsas(db, merchant)):
        return _empty(shop, "dest_out_of_area", dest_fsa=fsa_from_address(dropoff_raw)[:3])
    dropoff = _ensure_geo(dropoff_raw)

    pickup, pickup_source, fallback = resolve_shopify_pickup(default_pickup, origin)
    if pickup_source == PICKUP_SOURCE_PORTERCHAIN:
        # Shopify's ship-from is often a placeholder (US / no address). Quote from
        # the merchant's saved PorterChain pickup; book reuses this quote's pickup.
        pickup_fsa = fsa_from_address(pickup)[:3]
        if service_area_error("pickup", pickup):
            return _empty(shop, "pickup_out_of_area", origin=fallback, pickup_fsa=pickup_fsa)
        logger.info(
            "shopify_carrier_origin_fallback shop=%s reason=%s origin_country=%s pickup_fsa=%s",
            getattr(shop, "shop_domain", None) or shop.id,
            fallback,
            _country(origin) or "-",
            pickup_fsa or "-",
        )

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
        return _empty(shop, "pricing_error")
    finally:
        try:
            from porterchain_api.merchant_engine.commerce_metrics import note_quote_latency

            note_quote_latency((time.perf_counter() - t0) * 1000.0)
        except Exception:
            pass

    if (breakdown.get("metadata") or {}).get("fsa_refused"):
        return _empty(shop, "fsa_refused", dest_fsa=fsa_from_address(dropoff)[:3])
    if cents <= 0:
        return _empty(shop, "zero_price", dest_fsa=fsa_from_address(dropoff)[:3])

    breakdown = {**breakdown, "pickup": _pickup_snapshot(pickup, pickup_source)}
    if request_currency != RATE_CURRENCY:
        breakdown["request_currency"] = request_currency
    promise = _checkout_promise(db, dropoff)
    if promise is not None:
        breakdown["promise"] = promise.as_dict()
    req_hash = _request_hash(
        shop_id=shop.id,
        merchant_id=merchant.id,
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

    if promise is not None:
        fmt = "%Y-%m-%d %H:%M:%S %z"
        service_name, service_code = promise.service_name, promise.service_code
        desc = promise.description
        min_delivery = promise.window_start.strftime(fmt)
        max_delivery = promise.window_end.strftime(fmt)
    else:
        service_name, service_code = "PorterChain Same Day", "porterchain_same_day"
        desc = "Same-day local capacity"
        min_delivery, max_delivery = _delivery_window()
    rate: dict[str, Any] = {
        "service_name": service_name,
        "service_code": service_code,
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
