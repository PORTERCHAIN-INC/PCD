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
from porterchain_api.booking_models import Quote
from porterchain_api.pricing_engine import get_pricing_service
from porterchain_api.schemas import CreateQuoteRequest, PricingLineItem
from porterchain_api.pricing_engine.quote_bridge import (
    _request_from_quote_body,
    expire_quote_if_needed,
    revalidate_retail_quote,
)


def _assert_in_coverage(db: Session, ends: tuple[tuple[str, Any, Any], ...]) -> None:
    """Raise `{label}_outside_service_area` unless every end is in the GTA ±150 km area."""
    from porterchain_api.admin_engine.platform_settings import address_in_coverage

    for label, formatted, postal in ends:
        if not address_in_coverage(
            db,
            formatted=formatted if isinstance(formatted, str) else None,
            postal=postal if isinstance(postal, str) else None,
        ):
            raise ValueError(f"{label}_outside_service_area")


def revalidate_quote_for_payment(db: Session, quote: Quote) -> Quote:
    """Before Stripe: quote still valid, both ends still in area, price unchanged."""
    quote = expire_quote_if_needed(db, quote)
    if quote.state == QuoteState.QUOTE_EXPIRED.value:
        raise ValueError("quote_expired")
    ends = []
    for label, blob in (("pickup", quote.pickup), ("dropoff", quote.dropoff)):
        data = blob if isinstance(blob, dict) else {}
        ends.append((label, data.get("formatted"), data.get("postal")))
    _assert_in_coverage(db, tuple(ends))
    return revalidate_retail_quote(db, quote)


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
                signals=self._visitor.signals_from_tracking(body.tracking),
            )

        priced = self._price_body(db, settings, body)
        load = priced["load"]
        matrix_id = priced["matrix_id"]
        amount_cents = priced["amount_cents"]
        breakdown_items = priced["items"]
        pricing_summary = priced["summary"]
        distance_meters = priced["distance_meters"]
        parcels = dict(priced["parcels"] or {})
        # Persist promo on the quote so payment revalidation does not drop it
        # (Quote has no promo_code column; Stripe uses revalidate_retail_quote).
        if body.promo_code and str(body.promo_code).strip():
            parcels["promo_code"] = str(body.promo_code).strip()

        expires_at = datetime.now(UTC) + timedelta(minutes=settings.quote_ttl_minutes)
        quote = Quote(
            state=QuoteState.QUOTE.value,
            anonymous_session_id=session_id,
            visitor_session_id=session_id,
            pickup=body.pickup.model_dump(),
            dropoff=body.dropoff.model_dump(),
            vehicle_class=matrix_id,
            package_type=load.package_type,
            weight_kg=load.weight_kg,
            dimensions=load.dimensions,
            parcels=parcels,
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

    def preview_quote(self, db: Session, settings: Settings, body: CreateQuoteRequest) -> dict[str, Any]:
        """Same fare as a saved quote, without inserting a quotes row."""
        priced = self._price_body(db, settings, body)
        cents = int(priced["amount_cents"])
        meters = priced.get("distance_meters")
        return {
            "amount_cents": cents,
            "amount_display": f"${cents / 100:.2f} CAD",
            "distance_km": round(meters / 1000, 1) if meters else None,
            "pricing_breakdown": [i.model_dump() for i in priced["items"]],
            "vehicle_class": priced["matrix_id"],
            "included_km": priced["included_km"],
            "booking_mode": priced["load"].booking_mode,
            "parcel_count": len(priced["load"].items),
        }

    def _price_body(self, db: Session, settings: Settings, body: CreateQuoteRequest) -> dict[str, Any]:
        from porterchain_api.admin_engine.settings_service import AdminSettingsService
        from porterchain_api.domain.customer_goods import parcels_payload, presets_from_card, resolve_load
        from porterchain_api.domain.retail_vehicles import enabled_retail_vehicle_ids
        from porterchain_pricing.gta_rate import customer_gta_from_dict, normalize_vehicle_type

        settings_svc = AdminSettingsService()
        catalog = settings_svc.get_config_value(db, "vehicle_types")
        customer_card = settings_svc.get_config_value(db, "pricing_customer_distance")
        if not isinstance(catalog, list):
            catalog = []
        if not isinstance(customer_card, dict):
            customer_card = {}
        customer_rates = customer_gta_from_dict(customer_card)
        enabled = enabled_retail_vehicle_ids(db)
        try:
            matrix_id = normalize_vehicle_type(body.vehicle_class, known=customer_rates.vehicles)
        except ValueError as exc:
            raise ValueError("vehicle_class_not_available") from exc
        if enabled and matrix_id not in enabled:
            raise ValueError("vehicle_class_not_available")
        if matrix_id not in customer_rates.vehicles:
            raise ValueError("vehicle_rate_missing")

        load = resolve_load(
            booking_mode=body.booking_mode,
            parcels=body.parcels,
            vehicle_id=matrix_id,
            catalog=catalog,
            presets=presets_from_card(customer_card),
            fallback_weight_kg=body.weight_kg,
            fallback_dimensions=body.dimensions,
        )
        # Same GTA ±150 km tile gate on both ends as merchant / Shopify booking.
        _assert_in_coverage(
            db,
            (
                ("pickup", getattr(body.pickup, "formatted", None), getattr(body.pickup, "postal", None)),
                ("dropoff", getattr(body.dropoff, "formatted", None), getattr(body.dropoff, "postal", None)),
            ),
        )

        request = _request_from_quote_body(
            body,
            weight_kg=load.weight_kg,
            volume_cm3=load.volume_cm3,
            dimensions=load.dimensions,
            package_type=load.package_type,
            use_overrides=True,
            parcel_count=len(load.items) or 1,
        )
        # Production quotes need Valhalla/OSRM. Local/CI may fall back to haversine
        # when those services are not running (never Google).
        from porterchain_shared.redis_health import is_local_env

        if request.routing_source == "haversine" and not is_local_env(settings.app_env):
            raise ValueError("route_unavailable")

        pricing = get_pricing_service(db)
        breakdown = pricing.calculate_retail(request)
        items = [PricingLineItem(code=i.code, label=i.label, amount_cents=i.amount_cents) for i in breakdown.items]
        summary = pricing.to_api_breakdown(breakdown)
        summary["engine"] = "porterchain_pricing"
        if body.website_pricing:
            client_cents = int(round(body.website_pricing.customer_price_cad * 100))
            tolerance = max(
                settings.pricing_client_tolerance_cents,
                int(breakdown.final_cents * settings.pricing_client_tolerance_percent),
            )
            summary["client_estimate_cents"] = client_cents
            summary["client_engine"] = body.website_pricing.quote_engine
            if abs(client_cents - breakdown.final_cents) > tolerance:
                summary["client_estimate_rejected"] = True
                summary["client_server_delta_cents"] = client_cents - breakdown.final_cents
        return {
            "matrix_id": matrix_id,
            "load": load,
            "amount_cents": breakdown.final_cents,
            "items": items,
            "summary": summary,
            "distance_meters": breakdown.metadata.get("distance_meters"),
            "included_km": customer_rates.base_km_limit,
            "parcels": parcels_payload(load, body.declared_value_cents),
        }

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
