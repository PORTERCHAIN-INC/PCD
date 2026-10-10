"""Porterchain pricing bridge — retail quote helpers for the booking engine."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from porterchain_api.booking_models import DomainEvent, Quote
from porterchain_api.domain.customer_goods import persist_vehicle_class
from porterchain_api.domain.states import QuoteState
from porterchain_api.pricing_engine import get_pricing_service
from porterchain_api.schemas import AddressInput, CreateQuoteRequest, PricingLineItem
from porterchain_api.services.routing import resolve_route_distance
from porterchain_pricing import GeoPoint, PricingRequest


def _geo(addr: AddressInput) -> GeoPoint:
    return GeoPoint(
        lat=addr.lat,
        lng=addr.lng,
        formatted=addr.formatted,
        postal=getattr(addr, "postal", None) or "",
    )


def _request_from_quote_body(
    body: CreateQuoteRequest,
    *,
    channel: str = "retail",
    merchant_id: str | None = None,
    weight_kg: float | None = None,
    volume_cm3: float | None = None,
    dimensions: str | None = None,
    package_type: str | None = None,
    use_overrides: bool = False,
    parcel_count: int | None = None,
) -> PricingRequest:
    stops = [_geo(s) for s in (body.additional_stops or [])]
    pickup = _geo(body.pickup)
    dropoff = _geo(body.dropoff)
    distance, duration_seconds, routing_source = resolve_route_distance(pickup, dropoff, stops)
    service_type = body.service_type or ("scheduled" if body.schedule_mode == "later" else "same_day")
    return PricingRequest(
        pickup=pickup,
        dropoff=dropoff,
        vehicle_class=persist_vehicle_class(body.vehicle_class),
        package_type=package_type or body.package_type,
        service_type=service_type,
        weight_kg=weight_kg if use_overrides else body.weight_kg,
        dimensions=dimensions if use_overrides else body.dimensions,
        volume_cm3=volume_cm3 if use_overrides else None,
        declared_value_cents=body.declared_value_cents,
        schedule_mode=body.schedule_mode,
        scheduled_at=body.scheduled_at,
        is_rush=body.schedule_mode == "now",
        additional_stops=stops,
        distance_meters=distance,
        estimated_duration_minutes=int(duration_seconds / 60) if duration_seconds else None,
        routing_source=routing_source,
        channel=channel,  # type: ignore[arg-type]
        merchant_id=merchant_id,
        promo_code=body.promo_code,
        booking_mode="vehicle" if getattr(body, "booking_mode", None) == "vehicle" else "parcels",
        parcel_count=max(int(parcel_count or 1), 1),
    )


def _address_from_dict(data: dict) -> AddressInput:
    return AddressInput(
        formatted=data.get("formatted", ""),
        place_id=data.get("place_id"),
        lat=data.get("lat"),
        lng=data.get("lng"),
        postal=data.get("postal"),
    )


def _promo_code_from_quote(quote: Quote) -> str | None:
    """Promo is not a Quote column — recover it from parcels or the last breakdown."""
    payload = quote.parcels if isinstance(quote.parcels, dict) else {}
    raw = payload.get("promo_code")
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    breakdown = quote.pricing_breakdown if isinstance(quote.pricing_breakdown, dict) else {}
    summary = breakdown.get("summary") if isinstance(breakdown.get("summary"), dict) else {}
    from_summary = summary.get("promo_code")
    if isinstance(from_summary, str) and from_summary.strip():
        return from_summary.strip()
    return None


def _request_from_quote(quote: Quote) -> PricingRequest:
    payload = quote.parcels if isinstance(quote.parcels, dict) else {}
    mode = payload.get("booking_mode")
    volume = None
    weight = None if mode == "vehicle" else quote.weight_kg
    dimensions = None if mode == "vehicle" else quote.dimensions
    if mode != "vehicle":
        cubes = 0.0
        for item in payload.get("items") or []:
            if not isinstance(item, dict):
                continue
            if item.get("length_cm") and item.get("width_cm") and item.get("height_cm"):
                cubes += float(item["length_cm"]) * float(item["width_cm"]) * float(item["height_cm"])
        volume = cubes or None
    body = CreateQuoteRequest(
        pickup=_address_from_dict(quote.pickup or {}),
        dropoff=_address_from_dict(quote.dropoff or {}),
        vehicle_class=quote.vehicle_class,
        package_type=quote.package_type,
        weight_kg=weight,
        dimensions=dimensions,
        declared_value_cents=quote.declared_value_cents,
        additional_stops=[_address_from_dict(s) for s in (quote.additional_stops or [])],
        scheduled_at=quote.scheduled_at,
        schedule_mode=quote.schedule_mode,
        booking_mode="vehicle" if mode == "vehicle" else "parcels",
        promo_code=_promo_code_from_quote(quote),
    )
    return _request_from_quote_body(
        body,
        weight_kg=weight,
        volume_cm3=volume,
        dimensions=dimensions,
        package_type=quote.package_type,
        use_overrides=True,
        parcel_count=len([i for i in payload.get("items") or [] if isinstance(i, dict)]) or 1,
    )


def expire_quote_if_needed(db: Session, quote: Quote, now: datetime | None = None) -> Quote:
    now = now or datetime.now(UTC)
    exp = quote.expires_at
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=UTC)
    if quote.state == QuoteState.QUOTE.value and exp <= now:
        quote.state = QuoteState.QUOTE_EXPIRED.value
        db.add(
            DomainEvent(
                event_type="quote.expired",
                aggregate_type="quote",
                aggregate_id=quote.id,
                correlation_id=quote.id,
                payload={},
            )
        )
        db.commit()
        db.refresh(quote)
    return quote


def revalidate_retail_quote(db: Session, quote: Quote) -> Quote:
    """Recalculate authoritative retail price from stored quote fields (masterrule §11).

    If the recomputed amount differs from the quoted amount, persist the new
    figure and raise `quote_price_changed:N` so the customer confirms before
    Stripe charges. Coverage is checked by the caller
    (booking_engine.quote_service.revalidate_quote_for_payment).
    """
    quote = expire_quote_if_needed(db, quote)
    if quote.state == QuoteState.QUOTE_EXPIRED.value:
        raise ValueError("quote_expired")

    service = get_pricing_service(db)
    request = _request_from_quote(quote)
    from porterchain_api.config import get_settings
    from porterchain_shared.redis_health import is_local_env

    if request.routing_source == "haversine" and not is_local_env(get_settings().app_env):
        raise ValueError("route_unavailable")
    breakdown = service.calculate_retail(request)
    items = [PricingLineItem(code=i.code, label=i.label, amount_cents=i.amount_cents) for i in breakdown.items]
    summary = service.to_api_breakdown(breakdown)
    if quote.pricing_breakdown and quote.pricing_breakdown.get("summary", {}).get("client_estimate_cents"):
        summary["client_estimate_cents"] = quote.pricing_breakdown["summary"]["client_estimate_cents"]

    quoted = int(quote.amount_cents or 0)
    new_cents = int(breakdown.final_cents)
    quote.pricing_breakdown = {"items": [i.model_dump() for i in items], "summary": summary}
    quote.distance_meters = breakdown.metadata.get("distance_meters") or quote.distance_meters
    if new_cents != quoted:
        quote.amount_cents = new_cents
        db.commit()
        db.refresh(quote)
        raise ValueError(f"quote_price_changed:{new_cents}")
    db.commit()
    db.refresh(quote)
    return quote
