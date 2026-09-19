"""Merchant booking — Net terms flow per BUSINESS_WORKFLOW.md §2.3."""

from collections.abc import Callable
from typing import TypeVar

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from porterchain_api.booking_engine.compliance_metadata import build_compliance_metadata
from porterchain_api.booking_engine.site_access import enrich_dropoff
from porterchain_api.booking_engine._core import emit_event
from porterchain_api.booking_engine.numbers import generate_order_number, generate_tracking_number
from porterchain_api.booking_engine.order_transitions import transition_order_state, transition_to_dispatch_ready
from porterchain_api.config import Settings
from porterchain_api.fleetbase_engine import MerchantSyncService
from porterchain_api.domain.states import OrderState, OrderSource
from porterchain_api.merchant_engine import events as E
from porterchain_api.merchant_engine.rbac import MerchantContext
from porterchain_api.booking_models import Order
from porterchain_api.pricing_engine import get_pricing_service
from porterchain_api.schemas import AddressInput
from porterchain_api.schemas_merchant import MerchantBookDeliveryRequest
from porterchain_api.booking_engine.order_metadata import resolve_order_type
from porterchain_api.services.routing import resolve_route_distance
from porterchain_pricing import GeoPoint, PricingRequest
from porterchain_api.domain.merchant_states import MerchantStatus
from porterchain_api.fleetbase_engine.merchant_sync_service import BookingValidationError
from porterchain_api.merchant_engine.service_area import assert_ontario_booking
from porterchain_api.merchant_engine.stop_cargo import (
    book_stops_for_request,
    cargo_rollup,
    fleetbase_stop,
    packages_from_stops,
    parse_dt,
    pickup_stop,
)


T = TypeVar("T")


def parse_idempotency_key(raw: str | None, *, max_len: int = 128) -> str | None:
    key = (raw or "").strip() or None
    if key and len(key) > max_len:
        raise ValueError("idempotency_key_too_long")
    return key


def booking_value_error_detail(exc: BaseException) -> str:
    detail = str(exc)
    if detail == "quote_expired":
        return "This quote expired. Request a new price before booking."
    return detail


def confirm_replay_payload(order: Order) -> dict:
    from porterchain_api.domain.sandbox import order_is_sandbox

    sandbox = order_is_sandbox(order)
    return {
        "order_id": order.id,
        "order_number": order.order_number,
        "tracking_number": order.tracking_number,
        "amount_cents": order.amount_cents,
        "preview": {"valid": True, "amount_cents": order.amount_cents},
        "is_sandbox": sandbox,
        "public_track_url": None,
        "consignee_email": None,
        "consignee_emailed": False,
    }


def _canonical_vehicle(code: str | None) -> str:
    raw = (code or "").strip() or "cargoVan"
    try:
        from porterchain_pricing.gta_rate import normalize_vehicle_type

        return normalize_vehicle_type(raw)
    except ValueError:
        return raw


def _geo(addr: AddressInput) -> GeoPoint:
    """Address to pricing point, keeping the postal code FSA rates need."""
    return GeoPoint(
        lat=addr.lat,
        lng=addr.lng,
        formatted=addr.formatted,
        postal=getattr(addr, "postal", None) or "",
    )


def _assert_credit_headroom(db: Session, ctx: MerchantContext) -> None:
    limit = ctx.merchant.credit_limit_cents
    if limit is None or limit <= 0:
        return
    from porterchain_api.merchant_engine.billing_service import MerchantBillingService

    owed = MerchantBillingService().outstanding_balance(db, ctx)
    if owed >= limit:
        raise BookingValidationError(
            "credit_hold",
            "This account is at its credit limit. Contact PorterChain before booking.",
        )


def assert_pickup_window(body: MerchantBookDeliveryRequest) -> None:
    start, end = body.pickup_window_start, body.pickup_window_end
    if end and not start:
        raise BookingValidationError(
            "pickup_window_start_required",
            "Choose when the shipment is ready before the pickup-by time.",
        )
    if start and end and end <= start:
        raise BookingValidationError(
            "pickup_window_invalid",
            "Pickup by must be after ready from.",
        )


def schedule_from_body(body: MerchantBookDeliveryRequest) -> tuple:
    start = body.pickup_window_start
    later = bool(start or body.pickup_window_end)
    scheduled_at = start or body.scheduled_at
    mode = "later" if later else (body.schedule_mode or "now")
    return scheduled_at, mode


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
        pickup_geo = _geo(pickup)
        dropoff_geo = _geo(dropoff)
        stops = [_geo(s) for s in (body.additional_stops or [])]
        distance, duration_seconds, routing_source = resolve_route_distance(pickup_geo, dropoff_geo, stops)
        weight_kg, dimensions = cargo_rollup(body)
        scheduled_at, schedule_mode = schedule_from_body(body)
        return PricingRequest(
            pickup=pickup_geo,
            dropoff=dropoff_geo,
            vehicle_class=_canonical_vehicle(vehicle_class or body.vehicle_class),
            package_type=body.package_type,
            service_type=getattr(body, "service_type", "same_day"),
            weight_kg=weight_kg,
            dimensions=dimensions,
            schedule_mode=schedule_mode,
            scheduled_at=scheduled_at,
            additional_stops=stops,
            distance_meters=distance,
            estimated_duration_minutes=int(duration_seconds / 60) if duration_seconds else None,
            routing_source=routing_source,
            channel="merchant",
            merchant_id=ctx.merchant.id,
            volume_units=volume_units,
            requires_liftgate=body.requires_liftgate,
        )

    def find_by_idempotency_key(
        self,
        db: Session,
        ctx: MerchantContext,
        key: str,
        *,
        is_sandbox: bool = False,
    ) -> Order | None:
        """Existing order for a replayed programmatic create, scoped to merchant + env."""
        return (
            db.query(Order)
            .filter(
                Order.merchant_id == ctx.merchant.id,
                Order.idempotency_key == key,
                Order.is_sandbox.is_(bool(is_sandbox)),
            )
            .first()
        )

    def run_idempotent(
        self,
        db: Session,
        ctx: MerchantContext,
        key: str | None,
        create: Callable[[], T],
        *,
        replay_map: Callable[[Order], T] | None = None,
        is_sandbox: bool = False,
    ) -> T:
        """Create once; replay the existing row when the idempotency key collides."""
        if key:
            existing = self.find_by_idempotency_key(db, ctx, key, is_sandbox=is_sandbox)
            if existing:
                return replay_map(existing) if replay_map else existing  # type: ignore[return-value]
        try:
            return create()
        except IntegrityError:
            db.rollback()
            existing = self.find_by_idempotency_key(db, ctx, key, is_sandbox=is_sandbox) if key else None
            if not existing:
                raise
            return replay_map(existing) if replay_map else existing  # type: ignore[return-value]

    def create_shipment(
        self,
        db: Session,
        settings: Settings,
        ctx: MerchantContext,
        body: MerchantBookDeliveryRequest,
        *,
        order_source: str = OrderSource.MERCHANT.value,
        idempotency_key: str | None = None,
        sandbox: bool = False,
    ) -> Order:
        if ctx.merchant.status != MerchantStatus.ACTIVE.value:
            raise BookingValidationError(
                "merchant_not_active",
                f"Merchant must be ACTIVE to book (status={ctx.merchant.status}).",
            )
        assert_ontario_booking(body)
        assert_pickup_window(body)

        # Explicit caller flag only — org profile preference must not silently dry-run.
        is_sandbox = bool(sandbox)
        if not is_sandbox:
            _assert_credit_headroom(db, ctx)

        pickup = body.pickup
        dropoff = body.dropoff
        pricing_request = self.build_pricing_request(ctx, body)
        breakdown = get_pricing_service(db).calculate_merchant(pricing_request)
        amount_cents = breakdown.final_cents

        # WORKFLOW: validate merchant → pricing → contract → payment terms
        # before an order is generated. A merchant never reaches Fleetbase directly.
        validated = MerchantSyncService().validate_booking(db, ctx.merchant, amount_cents=amount_cents)

        pricing = get_pricing_service(db)
        api_breakdown = pricing.to_api_breakdown(breakdown)
        from porterchain_api.merchant_engine.quote_snapshot import merchant_quote_picture

        snapshot = merchant_quote_picture(
            api_breakdown,
            vehicle_class=body.vehicle_class,
            package_type=body.package_type,
            distance_meters=breakdown.metadata.get("distance_meters")
            if isinstance(breakdown.metadata, dict)
            else None,
        )
        from porterchain_api.merchant_engine.consignee_notify import resolve_consignee_email

        consignee_email = resolve_consignee_email(db, ctx, body)

        compliance = build_compliance_metadata(body) or {}
        if body.additional_stops:
            compliance["additional_stops"] = [s.model_dump() for s in body.additional_stops]
        # Order.is_sandbox is SoT — do not write compliance.sandbox (legacy rows still dual-read).
        compliance["quote"] = snapshot
        compliance["vehicle_class"] = body.vehicle_class
        compliance["package_type"] = body.package_type
        if consignee_email:
            compliance["consignee"] = {"email": consignee_email}

        scheduled_at, schedule_mode = schedule_from_body(body)
        weight_kg, dimensions = cargo_rollup(body)
        cargo_stops = book_stops_for_request(body)
        compliance["stops"] = [fleetbase_stop(stop) for stop in cargo_stops]
        compliance["schedule_mode"] = schedule_mode
        if weight_kg is not None:
            compliance["weight_kg"] = weight_kg
        if dimensions:
            compliance["dimensions"] = dimensions

        from porterchain_api.domain.states import CodStatus

        cod_amount = body.cod_amount_cents
        cod_status = None
        if not is_sandbox and cod_amount and cod_amount > 0:
            if not getattr(ctx.merchant, "cod_enabled", False):
                raise ValueError("cod_not_enabled_for_merchant")
            if not getattr(ctx.merchant, "stripe_connect_account_id", None):
                raise ValueError("connect_account_required")
            cod_status = CodStatus.PENDING_COLLECTION.value
        elif is_sandbox:
            # Test bookings never collect COD.
            cod_amount = None

        order = Order(
            order_number=generate_order_number(),
            tracking_number=generate_tracking_number(),
            state=OrderState.BOOKED.value,
            merchant_id=ctx.merchant.id,
            customer_id=None,
            order_source=order_source,
            order_type=resolve_order_type(
                schedule_mode=schedule_mode,
                has_contract=bool(validated.contract_id),
                is_rush=schedule_mode == "now",
            ),
            payment_terms=ctx.merchant.payment_terms,
            amount_cents=amount_cents,
            pickup=pickup.model_dump(),
            dropoff=enrich_dropoff(dropoff.model_dump(), body.site_access_notes),
            scheduled_at=scheduled_at,
            internal_reference=body.internal_reference,
            idempotency_key=idempotency_key,
            is_sandbox=is_sandbox,
            purchase_order_number=body.purchase_order_number,
            cost_centre=body.cost_centre,
            special_instructions=body.special_instructions,
            compliance_metadata=compliance or None,
            cod_amount_cents=cod_amount,
            cod_status=cod_status,
        )
        db.add(order)
        db.flush()
        from porterchain_api.booking_engine.stop_sync import dual_write_stops

        dual_write_stops(db, order)

        from porterchain_api.merchant_engine.package_service import PackageService

        PackageService().sync_from_order(db, order)

        if not is_sandbox:
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
                "is_sandbox": is_sandbox,
            },
        )
        db.commit()

        if is_sandbox:
            db.refresh(order)
            return order

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
        if consignee_email:
            from porterchain_api.merchant_engine.consignee_notify import send_consignee_tracking_safe

            send_consignee_tracking_safe(
                db,
                settings,
                order,
                consignee_email,
                merchant_name=ctx.merchant.company_name,
            )
            db.commit()
            db.refresh(order)
        return order

    def cancel_order(self, db: Session, ctx: MerchantContext, order: Order, settings: Settings | None = None) -> Order:
        from porterchain_api.merchant_engine.cancel_policy import assert_merchant_can_cancel

        if order.merchant_id != ctx.merchant.id:
            raise PermissionError("order_not_owned")
        assert_merchant_can_cancel(order.state)
        result = transition_order_state(
            db,
            order,
            OrderState.CANCELLED,
            event_type="order.cancelled",
            actor_type="merchant",
            actor_id=ctx.user.id,
        )
        # Fleetbase cancel is enqueued once via order.cancelled (no in-request HTTP).
        return result

    def duplicate_order(self, db: Session, settings: Settings, ctx: MerchantContext, order: Order) -> Order:
        from porterchain_api.schemas_merchant import RouteImportPackageInput

        meta = order.compliance_metadata if isinstance(order.compliance_metadata, dict) else {}
        consignee = meta.get("consignee") if isinstance(meta.get("consignee"), dict) else {}
        stops = meta.get("stops") if isinstance(meta.get("stops"), list) else []
        origin = pickup_stop(stops) or {}
        window_start = parse_dt(origin.get("time_window_start"))
        window_end = parse_dt(origin.get("time_window_end"))
        packages = []
        for raw in packages_from_stops(stops):
            packages.append(RouteImportPackageInput.model_validate(raw))
        additional = meta.get("additional_stops") if isinstance(meta.get("additional_stops"), list) else None
        body = MerchantBookDeliveryRequest(
            pickup=order.pickup,
            dropoff=order.dropoff,
            additional_stops=[
                s for s in additional or [] if isinstance(s, dict) and s.get("formatted")
            ],
            vehicle_class=str(meta.get("vehicle_class") or "cargoVan"),
            package_type=str(meta.get("package_type") or "looseParcel"),
            weight_kg=meta.get("weight_kg"),
            dimensions=meta.get("dimensions"),
            scheduled_at=window_start or order.scheduled_at,
            schedule_mode="later" if window_start or window_end else "now",
            pickup_window_start=window_start,
            pickup_window_end=window_end,
            packages=packages or None,
            internal_reference=order.internal_reference,
            purchase_order_number=order.purchase_order_number,
            cost_centre=order.cost_centre,
            special_instructions=order.special_instructions,
            consignee_email=consignee.get("email") if isinstance(consignee, dict) else None,
        )
        # Never silent-promote: duplicate inherits source env.
        src_sandbox = bool(getattr(order, "is_sandbox", False) or meta.get("sandbox") is True)
        return self.create_shipment(db, settings, ctx, body, sandbox=src_sandbox)
