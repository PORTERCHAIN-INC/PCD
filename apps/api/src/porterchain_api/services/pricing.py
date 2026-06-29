"""Porterchain pricing bridge — delegates to porterchain_pricing engine."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from porterchain_api.config import Settings
from porterchain_api.domain.states import QuoteState
from porterchain_api.models import DomainEvent, Quote
from porterchain_api.pricing_engine import get_pricing_service
from porterchain_api.schemas import AddressInput, CreateQuoteRequest, PricingLineItem
from porterchain_pricing import GeoPoint, PricingRequest, haversine_meters, total_route_meters


def _geo(addr: AddressInput) -> GeoPoint:
    return GeoPoint(lat=addr.lat, lng=addr.lng, formatted=addr.formatted)


def _request_from_quote_body(body: CreateQuoteRequest, *, channel: str = "retail", merchant_id: str | None = None) -> PricingRequest:
    stops = [_geo(s) for s in (body.additional_stops or [])]
    pickup = _geo(body.pickup)
    dropoff = _geo(body.dropoff)
    distance = total_route_meters(pickup, dropoff, stops)
    service_type = body.service_type or ("scheduled" if body.schedule_mode == "later" else "same_day")
    return PricingRequest(
        pickup=pickup,
        dropoff=dropoff,
        vehicle_class=body.vehicle_class,
        package_type=body.package_type,
        service_type=service_type,
        weight_kg=body.weight_kg,
        dimensions=body.dimensions,
        declared_value_cents=body.declared_value_cents,
        schedule_mode=body.schedule_mode,
        scheduled_at=body.scheduled_at,
        is_rush=body.schedule_mode == "now",
        additional_stops=stops,
        distance_meters=distance,
        channel=channel,  # type: ignore[arg-type]
        merchant_id=merchant_id,
        promo_code=body.promo_code,
    )


def calculate_pricing(
    db: Session,
    *,
    vehicle_class: str,
    package_type: str,
    distance_meters: int | None,
    weight_kg: float | None,
    schedule_mode: str,
    declared_value_cents: int | None = None,
    additional_stops_count: int = 0,
    pickup: AddressInput | None = None,
    dropoff: AddressInput | None = None,
    merchant_id: str | None = None,
    service_type: str | None = None,
    dimensions: str | None = None,
    scheduled_at: datetime | None = None,
    promo_code: str | None = None,
) -> tuple[int, list[PricingLineItem]]:
    """Calculate price using Porterchain Pricing Engine."""
    pickup_geo = _geo(pickup) if pickup else GeoPoint()
    dropoff_geo = _geo(dropoff) if dropoff else GeoPoint()
    channel = "merchant" if merchant_id else "retail"
    request = PricingRequest(
        pickup=pickup_geo,
        dropoff=dropoff_geo,
        vehicle_class=vehicle_class,
        package_type=package_type,
        service_type=service_type or ("scheduled" if schedule_mode == "later" else "same_day"),
        weight_kg=weight_kg,
        dimensions=dimensions,
        declared_value_cents=declared_value_cents,
        schedule_mode=schedule_mode,
        scheduled_at=scheduled_at,
        is_rush=schedule_mode == "now",
        distance_meters=distance_meters,
        channel=channel,  # type: ignore[arg-type]
        merchant_id=merchant_id,
        promo_code=promo_code,
    )
    if additional_stops_count > 0 and not pickup and not dropoff:
        pass  # legacy callers without addresses — distance_meters already set

    service = get_pricing_service(db)
    breakdown = service.calculate_merchant(request) if merchant_id else service.calculate_retail(request)
    items = [PricingLineItem(code=i.code, label=i.label, amount_cents=i.amount_cents) for i in breakdown.items]
    if breakdown.tax_cents and not any(i.code == "tax" for i in items):
        items.append(PricingLineItem(code="tax", label="HST", amount_cents=breakdown.tax_cents))
    return breakdown.final_cents, items


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


def create_quote(db: Session, settings: Settings, body: CreateQuoteRequest) -> Quote:
    request = _request_from_quote_body(body)
    service = get_pricing_service(db)
    breakdown = service.calculate_retail(request)
    distance_meters = breakdown.metadata.get("distance_meters")
    items = [PricingLineItem(code=i.code, label=i.label, amount_cents=i.amount_cents) for i in breakdown.items]

    expires_at = datetime.now(UTC) + timedelta(minutes=settings.quote_ttl_minutes)
    quote = Quote(
        state=QuoteState.QUOTE.value,
        anonymous_session_id=body.anonymous_session_id,
        pickup=body.pickup.model_dump(),
        dropoff=body.dropoff.model_dump(),
        vehicle_class=body.vehicle_class,
        package_type=body.package_type,
        weight_kg=body.weight_kg,
        dimensions=body.dimensions,
        scheduled_at=body.scheduled_at,
        schedule_mode=body.schedule_mode,
        amount_cents=breakdown.final_cents,
        pricing_breakdown={"items": [i.model_dump() for i in items], "summary": service.to_api_breakdown(breakdown)},
        distance_meters=distance_meters,
        expires_at=expires_at,
    )
    db.add(quote)
    db.flush()
    db.add(
        DomainEvent(
            event_type="quote.created",
            aggregate_type="quote",
            aggregate_id=quote.id,
            correlation_id=quote.id,
            payload={"amount_cents": breakdown.final_cents},
        )
    )
    db.commit()
    db.refresh(quote)
    return quote
