"""Quote service — anonymous public quote per PRODUCT_REQUIREMENTS.md Phase A."""

from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from porterchain_api.booking_engine import events as E
from porterchain_api.booking_engine._core import emit_event
from porterchain_api.booking_engine.visitor_tracking_service import VisitorTrackingService
from porterchain_api.config import Settings
from porterchain_api.domain.states import QuoteState
from porterchain_api.models import Quote
from porterchain_api.pricing_engine import get_pricing_service
from porterchain_api.schemas import CreateQuoteRequest, PricingLineItem
from porterchain_api.services.pricing import _request_from_quote_body, expire_quote_if_needed
from porterchain_pricing import GeoPoint, total_route_meters


class QuoteService:
    def __init__(self) -> None:
        self._visitor = VisitorTrackingService()

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
            distance = total_route_meters(request.pickup, request.dropoff, stops)
            request = PricingRequest_replace(request, distance_meters=distance)

        pricing = get_pricing_service(db)
        breakdown = pricing.calculate_retail(request)
        distance_meters = breakdown.metadata.get("distance_meters")
        breakdown_items = [
            PricingLineItem(code=i.code, label=i.label, amount_cents=i.amount_cents) for i in breakdown.items
        ]

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
            amount_cents=breakdown.final_cents,
            pricing_breakdown={
                "items": [i.model_dump() for i in breakdown_items],
                "summary": pricing.to_api_breakdown(breakdown),
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
            payload={"amount_cents": breakdown.final_cents},
        )
        db.commit()
        db.refresh(quote)

        if session_id:
            self._visitor.record_quote(db, session_id, quote.id)

        return quote

    def get_quote(self, db: Session, quote_id: str) -> Quote | None:
        quote = db.query(Quote).filter(Quote.id == quote_id).first()
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
