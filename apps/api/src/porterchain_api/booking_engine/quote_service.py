"""Quote service — anonymous public quote per PRODUCT_REQUIREMENTS.md Phase A."""

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.booking_engine import events as E
from porterchain_api.booking_engine._core import emit_event
from porterchain_api.booking_engine.visitor_tracking_service import VisitorTrackingService
from porterchain_api.booking_engine.booking_draft_service import BookingDraftService
from porterchain_api.booking_engine.repositories.quote_repository import QuoteRepository
from porterchain_api.config import Settings
from porterchain_api.domain.states import QuoteState
from porterchain_api.models import Quote
from porterchain_api.pricing_engine import get_pricing_service
from porterchain_api.schemas import CreateQuoteRequest, PricingLineItem, WebsitePricingSnapshot
from porterchain_api.services.pricing import PricingRequest_replace, _request_from_quote_body, expire_quote_if_needed
from porterchain_api.services.routing import resolve_route_distance
from porterchain_pricing import GeoPoint


def _website_breakdown_to_line_items(
    snapshot: WebsitePricingSnapshot,
) -> list[PricingLineItem]:
    breakdown = snapshot.breakdown
    customer_price = snapshot.customer_price_cad
    subtotal = float(breakdown.get("subtotal", 0))
    adjusted_cost = float(breakdown.get("adjustedCost", subtotal))
    traffic_multiplier = float(breakdown.get("trafficMultiplier", 1))
    margin_multiplier = float(breakdown.get("marginMultiplier", 1.18))

    def cents(key_camel: str, key_snake: str, label: str, code: str) -> PricingLineItem | None:
        amount = float(breakdown.get(key_camel, breakdown.get(key_snake, 0)))
        if amount == 0:
            return None
        return PricingLineItem(code=code, label=label, amount_cents=int(round(amount * 100)))

    items: list[PricingLineItem] = []
    for item in (
        cents("baseFee", "base_fee", "Base fee", "base"),
        cents("distanceFee", "distance_fee", "Distance", "distance"),
        cents("timeFee", "time_fee", "Time", "time"),
        cents("weightFee", "weight_fee", "Weight", "weight"),
        cents("fuelFee", "fuel_fee", "Fuel surcharge", "fuel"),
        cents("stopFee", "stop_fee", "Additional stops", "stops"),
        cents("helperFee", "helper_fee", "Helper", "helper"),
    ):
        if item:
            items.append(item)

    traffic_delta = adjusted_cost - subtotal
    if traffic_delta != 0:
        items.append(
            PricingLineItem(
                code="traffic",
                label=f"Traffic adjustment (×{traffic_multiplier:.2f})",
                amount_cents=int(round(traffic_delta * 100)),
            )
        )

    margin_delta = customer_price - adjusted_cost
    if margin_delta != 0:
        items.append(
            PricingLineItem(
                code="margin",
                label=f"Service fee (×{margin_multiplier:.2f})",
                amount_cents=int(round(margin_delta * 100)),
            )
        )

    return items


def _website_pricing_summary(snapshot: WebsitePricingSnapshot) -> dict[str, Any]:
    return {
        "engine": snapshot.quote_engine,
        "customer_price_cad": snapshot.customer_price_cad,
        "driver_payout_cad": snapshot.driver_payout_cad,
        "platform_margin_cad": snapshot.platform_margin_cad,
        "engine_vehicle_id": snapshot.engine_vehicle_id,
        "duration_minutes": snapshot.duration_minutes,
        "breakdown": snapshot.breakdown,
        "traffic": snapshot.traffic,
    }


class QuoteService:
    def __init__(self) -> None:
        self._visitor = VisitorTrackingService()
        self._drafts = BookingDraftService()
        self._quotes = QuoteRepository()

    def create_quote(
        self,
        db: Session,
        settings: Settings,
        body: CreateQuoteRequest,
        *,
        ip_address: str | None = None,
    ) -> Quote:
        session_id = body.anonymous_session_id or body.visitor_session_id
        if session_id:
            self._visitor.ensure_session(
                db,
                session_id=session_id,
                ip_address=ip_address,
                browser=body.tracking.browser if body.tracking else None,
                utm_source=body.tracking.utm_source if body.tracking else None,
                utm_medium=body.tracking.utm_medium if body.tracking else None,
                utm_campaign=body.tracking.utm_campaign if body.tracking else None,
                referrer=body.tracking.referrer if body.tracking else None,
                device=body.tracking.device if body.tracking else None,
                location=body.tracking.location if body.tracking else None,
            )

        request = _request_from_quote_body(body)
        if body.additional_stops:
            stops = [GeoPoint(lat=s.lat, lng=s.lng, formatted=s.formatted) for s in body.additional_stops]
            request = PricingRequest_replace(request, additional_stops=stops)
            distance, duration_seconds = resolve_route_distance(request.pickup, request.dropoff, stops)
            request = PricingRequest_replace(
                request,
                distance_meters=distance,
                estimated_duration_minutes=int(duration_seconds / 60) if duration_seconds else None,
            )

        pricing = get_pricing_service(db)
        breakdown = pricing.calculate_retail(request)
        distance_meters = breakdown.metadata.get("distance_meters")
        breakdown_items = [
            PricingLineItem(code=i.code, label=i.label, amount_cents=i.amount_cents) for i in breakdown.items
        ]
        amount_cents = breakdown.final_cents
        pricing_summary = pricing.to_api_breakdown(breakdown)
        pricing_summary["engine"] = "porterchain_pricing"

        if body.website_pricing:
            client_cents = int(round(body.website_pricing.customer_price_cad * 100))
            tolerance = max(
                settings.pricing_client_tolerance_cents,
                int(amount_cents * settings.pricing_client_tolerance_percent),
            )
            pricing_summary["client_estimate_cents"] = client_cents
            pricing_summary["client_engine"] = body.website_pricing.quote_engine
            if abs(client_cents - amount_cents) > tolerance:
                pricing_summary["client_estimate_rejected"] = True
                pricing_summary["client_server_delta_cents"] = client_cents - amount_cents

        expires_at = datetime.now(UTC) + timedelta(minutes=settings.quote_ttl_minutes)
        quote = Quote(
            state=QuoteState.QUOTE.value,
            anonymous_session_id=session_id,
            visitor_session_id=session_id,
            pickup=body.pickup.model_dump(),
            dropoff=body.dropoff.model_dump(),
            vehicle_class=body.vehicle_class,
            package_type=body.package_type,
            weight_kg=body.weight_kg,
            dimensions=body.dimensions,
            declared_value_cents=body.declared_value_cents,
            additional_stops=[s.model_dump() for s in body.additional_stops] if body.additional_stops else None,
            special_instructions=body.special_instructions,
            scheduled_at=body.scheduled_at,
            schedule_mode=body.schedule_mode,
            amount_cents=amount_cents,
            pricing_breakdown={
                "items": [i.model_dump() for i in breakdown_items],
                "summary": pricing_summary,
            },
            distance_meters=distance_meters,
            expires_at=expires_at,
        )
        db.add(quote)
        db.flush()

        emit_event(
            db,
            event_type=E.QUOTE_CREATED,
            aggregate_type="quote",
            aggregate_id=quote.id,
            correlation_id=session_id,
            payload={"amount_cents": amount_cents},
        )
        db.commit()
        db.refresh(quote)

        if session_id:
            self._visitor.record_quote(db, session_id, quote.id)

        self._drafts.attach_quote(db, quote, session_id)

        return quote

    def get_quote(self, db: Session, quote_id: str) -> Quote | None:
        quote = self._quotes.get_by_id(db, quote_id)
        if not quote:
            return None
        return expire_quote_if_needed(db, quote)

    def accept_quote(self, db: Session, quote: Quote) -> Quote:
        emit_event(
            db,
            event_type=E.QUOTE_ACCEPTED,
            aggregate_type="quote",
            aggregate_id=quote.id,
            correlation_id=quote.visitor_session_id,
        )
        db.commit()
        return quote


def PricingRequest_replace(request, **kwargs):
    from porterchain_pricing.types import PricingRequest

    data = {
        "pickup": request.pickup,
        "dropoff": request.dropoff,
        "vehicle_class": request.vehicle_class,
        "package_type": request.package_type,
        "service_type": request.service_type,
        "weight_kg": request.weight_kg,
        "dimensions": request.dimensions,
        "declared_value_cents": request.declared_value_cents,
        "schedule_mode": request.schedule_mode,
        "scheduled_at": request.scheduled_at,
        "is_rush": request.is_rush,
        "additional_stops": request.additional_stops,
        "distance_meters": request.distance_meters,
        "estimated_duration_minutes": request.estimated_duration_minutes,
        "channel": request.channel,
        "merchant_id": request.merchant_id,
        "promo_code": request.promo_code,
        "wallet_credit_cents": request.wallet_credit_cents,
        "referral_credit_cents": request.referral_credit_cents,
        "volume_units": request.volume_units,
    }
    data.update(kwargs)
    return PricingRequest(**data)
