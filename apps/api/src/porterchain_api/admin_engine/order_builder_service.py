"""Admin multi-waypoint order builder — creates PC orders with rich stops[].

Persists adapter-shaped compliance_metadata.stops so the P0-2 Fleetbase mapper
emits waypoints. Pricing uses Valhalla/OSRM via resolve_route_distance.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.admin_engine.rbac import AdminContext
from porterchain_api.booking_engine._core import emit_event
from porterchain_api.booking_engine.numbers import generate_order_number, generate_tracking_number
from porterchain_api.booking_engine.order_metadata import resolve_order_type
from porterchain_api.booking_engine.order_transitions import transition_to_dispatch_ready
from porterchain_api.config import Settings
from porterchain_api.domain.customer_goods import persist_vehicle_class
from porterchain_api.domain.states import OrderSource, OrderState
from porterchain_api.fleetbase_engine import MerchantSyncService
from porterchain_api.fleetbase_engine.merchant_sync_service import BookingValidationError
from porterchain_api.merchant_engine.lookups import get_merchant
from porterchain_api.booking_models import Order
from porterchain_api.pricing_engine import get_pricing_service
from porterchain_api.schemas_admin import AdminCreateOrderRequest, AdminOrderStopInput
from porterchain_api.services.routing import resolve_route_distance
from porterchain_pricing import GeoPoint, PricingRequest

VALID_KINDS = frozenset({"single", "hub_spoke", "multi_pickup_delivery", "scheduled_pickup"})


def _normalize_stops(stops: list[AdminOrderStopInput]) -> list[dict[str, Any]]:
    ordered = sorted(stops, key=lambda s: s.sequence)
    out: list[dict[str, Any]] = []
    for i, s in enumerate(ordered):
        stop_type = s.type.strip().lower()
        if stop_type == "drop":
            stop_type = "dropoff"
        if stop_type not in {"pickup", "dropoff"}:
            raise ValueError(f"invalid_stop_type:{s.type}")
        out.append(
            {
                "id": s.id or f"s{i}",
                "type": stop_type,
                "sequence": i,
                "formatted": s.formatted,
                "address": s.formatted,
                "lat": s.lat,
                "lng": s.lng,
                "city": s.city,
                "time_window_start": s.time_window_start.isoformat() if s.time_window_start else None,
                "time_window_end": s.time_window_end.isoformat() if s.time_window_end else None,
                "service_time_seconds": s.service_time_seconds,
                "notes": s.notes,
                "pod_required": s.pod_required,
            }
        )
    return out


def _validate_kind(kind: str, stops: list[dict[str, Any]]) -> None:
    if kind not in VALID_KINDS:
        raise ValueError("invalid_order_kind")
    pickups = [s for s in stops if s["type"] == "pickup"]
    dropoffs = [s for s in stops if s["type"] == "dropoff"]
    if not pickups or not dropoffs:
        raise ValueError("need_pickup_and_dropoff")
    if kind == "single" and (len(pickups) != 1 or len(dropoffs) != 1):
        raise ValueError("single_requires_one_pickup_one_dropoff")
    if kind == "hub_spoke" and (len(pickups) != 1 or len(dropoffs) < 2):
        raise ValueError("hub_spoke_requires_one_pickup_and_multi_dropoff")
    if kind == "multi_pickup_delivery" and (len(pickups) < 2 or len(dropoffs) < 2):
        raise ValueError("multi_requires_at_least_two_pickups_and_dropoffs")


def _stop_addr(stop: dict[str, Any]) -> dict[str, Any]:
    return {
        "formatted": stop["formatted"],
        "lat": stop.get("lat"),
        "lng": stop.get("lng"),
        "city": stop.get("city"),
    }


class OrderBuilderService:
    def create(
        self,
        db: Session,
        settings: Settings,
        ctx: AdminContext,
        body: AdminCreateOrderRequest,
    ) -> dict[str, Any]:
        del settings  # reserved for future Fleetbase sync options
        merchant = get_merchant(db, body.merchant_id)
        if not merchant:
            raise LookupError("merchant_not_found")

        stops = _normalize_stops(body.stops)
        _validate_kind(body.order_kind, stops)

        pickups = [s for s in stops if s["type"] == "pickup"]
        dropoffs = [s for s in stops if s["type"] == "dropoff"]
        pickup = pickups[0]
        dropoff = dropoffs[-1]
        ends = {pickup["id"], dropoff["id"]}
        middles = [s for s in stops if s["id"] not in ends]

        pickup_geo = GeoPoint(lat=pickup.get("lat"), lng=pickup.get("lng"), formatted=pickup["formatted"])
        dropoff_geo = GeoPoint(lat=dropoff.get("lat"), lng=dropoff.get("lng"), formatted=dropoff["formatted"])
        mid_geo = [
            GeoPoint(lat=s.get("lat"), lng=s.get("lng"), formatted=s["formatted"]) for s in middles
        ]
        distance, duration_seconds, routing_source = resolve_route_distance(
            pickup_geo, dropoff_geo, mid_geo
        )

        # "later" maps to OrderType.SCHEDULED (merchant path); keep pricing on later too.
        schedule_mode = "later" if body.order_kind == "scheduled_pickup" else body.schedule_mode
        pricing_request = PricingRequest(
            pickup=pickup_geo,
            dropoff=dropoff_geo,
            vehicle_class=persist_vehicle_class(body.vehicle_class),
            package_type=body.package_type,
            service_type="scheduled" if schedule_mode == "later" else "same_day",
            weight_kg=body.weight_kg,
            schedule_mode=schedule_mode,
            scheduled_at=body.scheduled_at,
            additional_stops=mid_geo,
            total_pickups=len(pickups),
            total_drops=len(dropoffs),
            distance_meters=distance,
            estimated_duration_minutes=int(duration_seconds / 60) if duration_seconds else None,
            routing_source=routing_source,
            channel="merchant",
            merchant_id=merchant.id,
            volume_units=1,
        )
        breakdown = get_pricing_service(db).calculate_merchant(pricing_request)
        amount_cents = breakdown.final_cents

        try:
            validated = MerchantSyncService().validate_booking(
                db, merchant, amount_cents=amount_cents
            )
            warnings = list(validated.warnings)
            contract_id = validated.contract_id
        except BookingValidationError as exc:
            raise ValueError(exc.code) from exc

        compliance: dict[str, Any] = {
            "stops": stops,
            "order_kind": body.order_kind,
            "schedule_mode": schedule_mode,
            "vehicle_class": persist_vehicle_class(body.vehicle_class),
            "additional_stops": [_stop_addr(s) for s in middles],
        }

        order_type = resolve_order_type(
            schedule_mode=schedule_mode,
            has_contract=bool(contract_id),
            is_rush=schedule_mode == "now",
        )
        order = Order(
            order_number=generate_order_number(),
            tracking_number=generate_tracking_number(),
            state=OrderState.BOOKED.value,
            merchant_id=merchant.id,
            customer_id=None,
            order_source=OrderSource.ADMIN.value,
            order_type=order_type,
            payment_terms=merchant.payment_terms,
            amount_cents=amount_cents,
            pickup=_stop_addr(pickup),
            dropoff=_stop_addr(dropoff),
            scheduled_at=body.scheduled_at,
            internal_reference=body.internal_reference,
            special_instructions=body.special_instructions,
            compliance_metadata=compliance,
        )

        db.add(order)
        db.flush()

        try:
            from porterchain_api.authz.tuples import TupleWriter

            TupleWriter().link_order_to_org(order.id, merchant.id)
        except Exception:  # noqa: BLE001
            pass

        emit_event(
            db,
            event_type="admin.order_builder.created",
            aggregate_type="order",
            aggregate_id=order.id,
            correlation_id=merchant.id,
            actor_type="admin",
            actor_id=ctx.user.id,
            payload={
                "tracking_number": order.tracking_number,
                "order_kind": body.order_kind,
                "stop_count": len(stops),
                "contract_id": contract_id,
                "warnings": warnings,
            },
        )
        db.commit()

        transition_to_dispatch_ready(
            db,
            order,
            event_type="order.dispatch_ready",
            actor_type="admin",
            actor_id=ctx.user.id,
        )
        db.refresh(order)

        return {
            "order_id": order.id,
            "order_number": order.order_number,
            "tracking_number": order.tracking_number,
            "state": order.state,
            "amount_cents": order.amount_cents,
            "currency": order.currency,
            "stop_count": len(stops),
            "warnings": warnings,
        }
