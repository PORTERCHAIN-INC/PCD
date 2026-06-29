"""Merchant booking — Net terms flow per BUSINESS_WORKFLOW.md §2.3."""

from sqlalchemy.orm import Session

from porterchain_api.booking_engine._core import emit_event
from porterchain_api.booking_engine.numbers import generate_order_number, generate_tracking_number
from porterchain_api.booking_engine.order_transitions import transition_order_state
from porterchain_api.config import Settings
from porterchain_api.domain.states import OrderState
from porterchain_api.merchant_engine import events as E
from porterchain_api.merchant_engine.rbac import MerchantContext
from porterchain_api.models import Order
from porterchain_api.pricing_engine import get_pricing_service
from porterchain_api.schemas import AddressInput
from porterchain_api.schemas_merchant import MerchantBookDeliveryRequest
from porterchain_pricing import GeoPoint, PricingRequest, total_route_meters


class MerchantBookingService:
    def create_shipment(
        self,
        db: Session,
        settings: Settings,
        ctx: MerchantContext,
        body: MerchantBookDeliveryRequest,
    ) -> Order:
        pickup = body.pickup
        dropoff = body.dropoff
        pickup_geo = GeoPoint(lat=pickup.lat, lng=pickup.lng, formatted=pickup.formatted)
        dropoff_geo = GeoPoint(lat=dropoff.lat, lng=dropoff.lng, formatted=dropoff.formatted)
        stops = [GeoPoint(lat=s.lat, lng=s.lng, formatted=s.formatted) for s in (body.additional_stops or [])]
        distance = total_route_meters(pickup_geo, dropoff_geo, stops)

        pricing_request = PricingRequest(
            pickup=pickup_geo,
            dropoff=dropoff_geo,
            vehicle_class=body.vehicle_class,
            package_type=body.package_type,
            service_type=getattr(body, "service_type", "same_day"),
            weight_kg=body.weight_kg,
            schedule_mode=body.schedule_mode,
            scheduled_at=body.scheduled_at,
            additional_stops=stops,
            distance_meters=distance,
            channel="merchant",
            merchant_id=ctx.merchant.id,
            volume_units=1,
        )
        breakdown = get_pricing_service(db).calculate_merchant(pricing_request)
        amount_cents = breakdown.final_cents

        order = Order(
            order_number=generate_order_number(),
            tracking_number=generate_tracking_number(),
            state=OrderState.BOOKED.value,
            merchant_id=ctx.merchant.id,
            customer_id=None,
            payment_terms=ctx.merchant.payment_terms,
            amount_cents=amount_cents,
            pickup=pickup.model_dump(),
            dropoff=dropoff.model_dump(),
            scheduled_at=body.scheduled_at,
            internal_reference=body.internal_reference,
            purchase_order_number=body.purchase_order_number,
            cost_centre=body.cost_centre,
            special_instructions=body.special_instructions,
        )
        db.add(order)
        db.flush()

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
            },
        )
        db.commit()

        transition_order_state(
            db,
            order,
            OrderState.DISPATCH_READY,
            event_type="order.dispatch_ready",
            actor_type="merchant",
            actor_id=ctx.user.id,
        )
        db.refresh(order)
        return order

    def cancel_order(self, db: Session, ctx: MerchantContext, order: Order) -> Order:
        if order.merchant_id != ctx.merchant.id:
            raise PermissionError("order_not_owned")
        return transition_order_state(
            db,
            order,
            OrderState.CANCELLED,
            event_type="order.cancelled",
            actor_type="merchant",
            actor_id=ctx.user.id,
        )

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
