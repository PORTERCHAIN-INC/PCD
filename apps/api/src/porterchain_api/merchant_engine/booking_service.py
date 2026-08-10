"""Merchant booking — Net terms flow per BUSINESS_WORKFLOW.md §2.3."""

from sqlalchemy.orm import Session

from porterchain_api.booking_engine.compliance_metadata import build_compliance_metadata
from porterchain_api.booking_engine.site_access import enrich_dropoff
from porterchain_api.booking_engine._core import emit_event
from porterchain_api.booking_engine.numbers import generate_order_number, generate_tracking_number
from porterchain_api.booking_engine.order_transitions import transition_order_state, transition_to_dispatch_ready
from porterchain_api.config import Settings
from porterchain_api.fleetbase_engine import BookingSyncService, MerchantSyncService
from porterchain_api.domain.states import OrderState, OrderSource
from porterchain_api.merchant_engine import events as E
from porterchain_api.merchant_engine.rbac import MerchantContext
from porterchain_api.models import Order
from porterchain_api.pricing_engine import get_pricing_service
from porterchain_api.schemas import AddressInput
from porterchain_api.schemas_merchant import MerchantBookDeliveryRequest
from porterchain_api.booking_engine.order_metadata import resolve_order_type
from porterchain_api.services.routing import resolve_route_distance
from porterchain_pricing import GeoPoint, PricingRequest


class MerchantBookingService:
    def build_pricing_request(
        self,
        ctx: MerchantContext,
        body: MerchantBookDeliveryRequest,
        *,
        vehicle_class: str | None = None,
        volume_units: int = 1,
    ) -> PricingRequest:
        pickup = body.pickup
        dropoff = body.dropoff
        pickup_geo = GeoPoint(lat=pickup.lat, lng=pickup.lng, formatted=pickup.formatted)
        dropoff_geo = GeoPoint(lat=dropoff.lat, lng=dropoff.lng, formatted=dropoff.formatted)
        stops = [GeoPoint(lat=s.lat, lng=s.lng, formatted=s.formatted) for s in (body.additional_stops or [])]
        distance, duration_seconds, routing_source = resolve_route_distance(pickup_geo, dropoff_geo, stops)
        return PricingRequest(
            pickup=pickup_geo,
            dropoff=dropoff_geo,
            vehicle_class=vehicle_class or body.vehicle_class,
            package_type=body.package_type,
            service_type=getattr(body, "service_type", "same_day"),
            weight_kg=body.weight_kg,
            schedule_mode=body.schedule_mode,
            scheduled_at=body.scheduled_at,
            additional_stops=stops,
            distance_meters=distance,
            estimated_duration_minutes=int(duration_seconds / 60) if duration_seconds else None,
            routing_source=routing_source,
            channel="merchant",
            merchant_id=ctx.merchant.id,
            volume_units=volume_units,
            requires_liftgate=body.requires_liftgate,
        )

    def create_shipment(
        self,
        db: Session,
        settings: Settings,
        ctx: MerchantContext,
        body: MerchantBookDeliveryRequest,
        *,
        order_source: str = OrderSource.MERCHANT.value,
    ) -> Order:
        pickup = body.pickup
        dropoff = body.dropoff
        pricing_request = self.build_pricing_request(ctx, body)
        breakdown = get_pricing_service(db).calculate_merchant(pricing_request)
        amount_cents = breakdown.final_cents

        # WORKFLOW: validate merchant → pricing → contract → payment terms
        # before an order is generated. A merchant never reaches Fleetbase directly.
        validated = MerchantSyncService().validate_booking(db, ctx.merchant, amount_cents=amount_cents)

        compliance = build_compliance_metadata(body) or {}
        if body.additional_stops:
            compliance["additional_stops"] = [s.model_dump() for s in body.additional_stops]

        order = Order(
            order_number=generate_order_number(),
            tracking_number=generate_tracking_number(),
            state=OrderState.BOOKED.value,
            merchant_id=ctx.merchant.id,
            customer_id=None,
            order_source=order_source,
            order_type=resolve_order_type(
                schedule_mode=body.schedule_mode or "now",
                has_contract=bool(validated.contract_id),
                is_rush=body.schedule_mode == "now",
            ),
            payment_terms=ctx.merchant.payment_terms,
            amount_cents=amount_cents,
            pickup=pickup.model_dump(),
            dropoff=enrich_dropoff(dropoff.model_dump(), body.site_access_notes),
            scheduled_at=body.scheduled_at,
            internal_reference=body.internal_reference,
            purchase_order_number=body.purchase_order_number,
            cost_centre=body.cost_centre,
            special_instructions=body.special_instructions,
            compliance_metadata=compliance or None,
        )
        db.add(order)
        db.flush()

        try:
            from porterchain_api.authz.tuples import TupleWriter

            TupleWriter().link_order_to_org(order.id, ctx.merchant.id)
        except Exception:  # noqa: BLE001
            pass

        emit_event(
            db,
            event_type=E.MERCHANT_BOOKING_CREATED,
            aggregate_type="order",
            aggregate_id=order.id,
            correlation_id=ctx.merchant.id,
            actor_type="merchant",
            actor_id=ctx.user.id,
            payload={
                "tracking_number": order.tracking_number,
                "purchase_order_number": body.purchase_order_number,
                "contract_id": validated.contract_id,
                "validation_warnings": list(validated.warnings),
            },
        )
        db.commit()

        # Publish dispatch-ready → the registered event handler pushes the order
        # to Fleetbase via the adapter (event-driven; no direct call here).
        transition_to_dispatch_ready(
            db,
            order,
            event_type="order.dispatch_ready",
            actor_type="merchant",
            actor_id=ctx.user.id,
        )
        db.refresh(order)
        return order

    def cancel_order(self, db: Session, ctx: MerchantContext, order: Order, settings: Settings | None = None) -> Order:
        if order.merchant_id != ctx.merchant.id:
            raise PermissionError("order_not_owned")
        result = transition_order_state(
            db,
            order,
            OrderState.CANCELLED,
            event_type="order.cancelled",
            actor_type="merchant",
            actor_id=ctx.user.id,
        )
        # Propagate cancellation to Fleetbase (best-effort + durable retry).
        if settings is not None:
            BookingSyncService().sync_cancellation(db, settings, order)
        return result

    def duplicate_order(self, db: Session, settings: Settings, ctx: MerchantContext, order: Order) -> Order:
        body = MerchantBookDeliveryRequest(
            pickup=AddressInput(**order.pickup),
            dropoff=AddressInput(**order.dropoff),
            vehicle_class="cargoVan",
            package_type="looseParcel",
            scheduled_at=order.scheduled_at,
            internal_reference=order.internal_reference,
            purchase_order_number=order.purchase_order_number,
            cost_centre=order.cost_centre,
            special_instructions=order.special_instructions,
        )
        return self.create_shipment(db, settings, ctx, body)
