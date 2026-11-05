"""Admin Repeat order — clone an existing order for today at the same locked price.

Ravi (admin ops): one-click repeat with current America/Toronto date and the same
price so staff can rebook identical merchant work without re-quoting.
"""

from __future__ import annotations

import copy
from datetime import UTC, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from porterchain_api.booking_engine import events as E
from porterchain_api.booking_engine._core import emit_event
from porterchain_api.booking_engine.numbers import generate_order_number, generate_tracking_number
from porterchain_api.booking_engine.order_metadata import resolve_order_type
from porterchain_api.booking_models import Order
from porterchain_api.config import Settings
from porterchain_api.domain.states import OrderSource, OrderState

TORONTO = ZoneInfo("America/Toronto")
_DROP_META_KEYS = frozenset(
    {
        "return",
        "returns",
        "repeat",
        "repeated_from",
        "driver_id",
        "assigned_driver_id",
        "dispatch",
        "route_id",
        "batch_route_id",
    }
)


def _meta(order: Order) -> dict[str, Any]:
    return order.compliance_metadata if isinstance(order.compliance_metadata, dict) else {}


def _parse_dt(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    if isinstance(value, str):
        raw = value.strip().replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(raw)
        except ValueError:
            return None
        return dt if dt.tzinfo else dt.replace(tzinfo=UTC)
    return None


def _shift_to_toronto_day(dt: datetime, day: datetime) -> datetime:
    local = dt.astimezone(TORONTO)
    shifted = day.replace(
        hour=local.hour,
        minute=local.minute,
        second=local.second,
        microsecond=0,
    )
    return shifted.astimezone(UTC)


def _toronto_business_now(now: datetime | None = None) -> datetime:
    return (now or datetime.now(UTC)).astimezone(TORONTO)


def _schedule_for_today(
    original: Order,
    *,
    now: datetime | None = None,
) -> tuple[datetime, str, dict[str, Any]]:
    """Return (scheduled_at UTC, schedule_mode, compliance_metadata with windows on today)."""
    today_local = _toronto_business_now(now)
    now_utc = today_local.astimezone(UTC)
    meta = copy.deepcopy(_meta(original))

    src_scheduled = original.scheduled_at
    if src_scheduled is not None and src_scheduled.tzinfo is None:
        src_scheduled = src_scheduled.replace(tzinfo=UTC)
    if src_scheduled is not None:
        scheduled_at = _shift_to_toronto_day(src_scheduled, today_local)
    else:
        scheduled_at = now_utc

    # If the shifted clock time already passed, book ASAP for today.
    schedule_mode = str(meta.get("schedule_mode") or "now")
    if scheduled_at < now_utc - timedelta(minutes=5):
        scheduled_at = now_utc
        schedule_mode = "now"

    stops = meta.get("stops")
    if isinstance(stops, list):
        for stop in stops:
            if not isinstance(stop, dict):
                continue
            start = _parse_dt(stop.get("time_window_start"))
            end = _parse_dt(stop.get("time_window_end"))
            if start is not None:
                start = _shift_to_toronto_day(start, today_local)
            if end is not None:
                end = _shift_to_toronto_day(end, today_local)
            if end is not None and end < now_utc:
                start = now_utc
                end = now_utc + timedelta(hours=3)
                schedule_mode = "now"
            if start is not None:
                stop["time_window_start"] = start.isoformat()
            if end is not None:
                stop["time_window_end"] = end.isoformat()
        meta["stops"] = stops

    meta["schedule_mode"] = schedule_mode
    return scheduled_at, schedule_mode, meta


def _clean_compliance(meta: dict[str, Any], *, original: Order, actor_id: str | None) -> dict[str, Any]:
    out = {k: v for k, v in meta.items() if k not in _DROP_META_KEYS}
    out["repeat"] = {
        "of": original.id,
        "of_tracking": original.tracking_number,
        "of_order_number": original.order_number,
        "locked_price_cents": int(original.amount_cents or 0),
        "reason": "admin_repeat_same_price",
        "booked_by": "admin",
        "admin_user_id": actor_id,
        "created_at": datetime.now(UTC).isoformat(),
    }
    return out


def repeat_summary(order: Order) -> dict[str, Any]:
    link = _meta(order).get("repeat") if isinstance(_meta(order).get("repeat"), dict) else {}
    return {
        "order_id": order.id,
        "order_number": order.order_number,
        "tracking_number": order.tracking_number,
        "state": order.state,
        "amount_cents": int(order.amount_cents or 0),
        "currency": order.currency or "cad",
        "scheduled_at": order.scheduled_at.isoformat() if order.scheduled_at else None,
        "source_order_id": link.get("of"),
        "source_tracking_number": link.get("of_tracking"),
        "price_locked": True,
    }


def create_repeat_order(
    db: Session,
    settings: Settings,
    original: Order,
    *,
    actor_id: str | None = None,
    now: datetime | None = None,
) -> Order:
    """Clone ``original`` into a new admin order for today; keep amount_cents exact."""
    del settings  # reserved for future credit/policy hooks
    if not original.merchant_id and not original.customer_id:
        raise ValueError("repeat_requires_party: order needs a merchant or customer")

    locked_cents = int(original.amount_cents or 0)
    if locked_cents < 0:
        raise ValueError("repeat_invalid_price")

    scheduled_at, schedule_mode, meta = _schedule_for_today(original, now=now)
    compliance = _clean_compliance(meta, original=original, actor_id=actor_id)

    merchant = None
    contract_id = None
    warnings: list[str] = []
    if original.merchant_id:
        from porterchain_api.merchant_engine.booking_validation import (
            BookingValidationError,
            MerchantSyncService,
        )
        from porterchain_api.merchant_engine.lookups import get_merchant

        merchant = get_merchant(db, original.merchant_id)
        if not merchant:
            raise ValueError("repeat_requires_merchant: merchant on source order is missing")
        try:
            validated = MerchantSyncService().validate_booking(
                db, merchant, amount_cents=locked_cents
            )
            warnings = list(validated.warnings)
            contract_id = validated.contract_id
        except BookingValidationError as exc:
            raise ValueError(exc.code) from exc

    order_type = resolve_order_type(
        schedule_mode=schedule_mode,
        has_contract=bool(contract_id),
        is_rush=schedule_mode == "now",
    )

    order = Order(
        order_number=generate_order_number(),
        tracking_number=generate_tracking_number(),
        state=OrderState.BOOKED.value,
        merchant_id=original.merchant_id,
        customer_id=original.customer_id,
        order_source=OrderSource.ADMIN.value,
        order_type=order_type,
        payment_terms=(merchant.payment_terms if merchant else original.payment_terms),
        amount_cents=locked_cents,
        currency=original.currency or "cad",
        pickup=copy.deepcopy(original.pickup) if isinstance(original.pickup, dict) else original.pickup,
        dropoff=copy.deepcopy(original.dropoff) if isinstance(original.dropoff, dict) else original.dropoff,
        scheduled_at=scheduled_at,
        internal_reference=original.internal_reference,
        purchase_order_number=original.purchase_order_number,
        cost_centre=original.cost_centre,
        special_instructions=original.special_instructions,
        compliance_metadata=compliance,
        is_sandbox=bool(getattr(original, "is_sandbox", False)),
        assigned_driver_id=None,
        quote_id=None,
    )
    db.add(order)
    db.flush()

    from porterchain_api.services import collect_only as co

    hub = None
    if co.is_collect_only(order):
        try:
            hub = co.warehouse(db)
        except ValueError:
            hub = None
    co.attach_legs(db, order, hub, actor_type="admin", actor_id=actor_id)

    try:
        from porterchain_api.booking_engine.stop_sync import dual_write_stops

        dual_write_stops(db, order)
    except Exception:  # noqa: BLE001
        pass

    try:
        from porterchain_api.merchant_engine.package_service import PackageService

        PackageService().sync_from_order(db, order)
    except Exception:  # noqa: BLE001
        pass

    if order.merchant_id and not order.is_sandbox:
        try:
            from porterchain_api.authz.tuples import TupleWriter

            TupleWriter().link_order_to_org(order.id, order.merchant_id)
        except Exception:  # noqa: BLE001
            pass

    emit_event(
        db,
        event_type=E.ORDER_CREATED,
        aggregate_type="order",
        aggregate_id=order.id,
        correlation_id=order.merchant_id or order.customer_id,
        actor_type="admin",
        actor_id=actor_id,
        payload={
            "order_number": order.order_number,
            "tracking_number": order.tracking_number,
            "customer_id": order.customer_id,
            "merchant_id": order.merchant_id,
            "amount_cents": order.amount_cents,
            "repeated_from": original.id,
            "price_locked": True,
            "warnings": warnings,
        },
    )
    emit_event(
        db,
        event_type="admin.order.repeated",
        aggregate_type="order",
        aggregate_id=order.id,
        correlation_id=original.id,
        actor_type="admin",
        actor_id=actor_id,
        payload={
            "source_order_id": original.id,
            "source_tracking_number": original.tracking_number,
            "locked_price_cents": locked_cents,
            "scheduled_at": scheduled_at.isoformat(),
        },
    )
    return order
