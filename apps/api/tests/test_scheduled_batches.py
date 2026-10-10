"""Scheduled pickup batch grouping (P1-5)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from porterchain_api.admin_engine.scheduled_batches_service import (
    _is_scheduled_pickup,
    _pickup_window,
    _stop_count,
)
from porterchain_api.booking_engine.numbers import generate_order_number, generate_tracking_number
from porterchain_api.domain.states import OrderState, OrderType
from porterchain_api.booking_models import Order


def _order(**overrides) -> Order:
    now = datetime.now(UTC).replace(tzinfo=None)
    defaults = dict(
        id=str(uuid4()),
        order_number=generate_order_number(),
        tracking_number=generate_tracking_number(),
        state=OrderState.DISPATCH_READY.value,
        order_type=OrderType.INSTANT.value,
        amount_cents=2500,
        currency="cad",
        pickup={"formatted": "100 King St W", "lat": 43.65, "lng": -79.38},
        dropoff={"formatted": "200 Bay St", "lat": 43.64, "lng": -79.37},
        scheduled_at=now,
        created_at=now,
        compliance_metadata=None,
    )
    defaults.update(overrides)
    return Order(**defaults)


def test_is_scheduled_by_order_kind():
    o = _order(compliance_metadata={"order_kind": "scheduled_pickup", "schedule_mode": "later"})
    assert _is_scheduled_pickup(o) is True


def test_is_scheduled_by_order_type():
    o = _order(order_type=OrderType.SCHEDULED.value)
    assert _is_scheduled_pickup(o) is True


def test_instant_not_scheduled():
    o = _order(compliance_metadata={"order_kind": "single"})
    assert _is_scheduled_pickup(o) is False


def test_stop_count_from_rich_stops():
    o = _order(
        compliance_metadata={
            "stops": [
                {"type": "pickup", "sequence": 0},
                {"type": "dropoff", "sequence": 1},
                {"type": "dropoff", "sequence": 2},
            ]
        }
    )
    assert _stop_count(o) == 3


def test_pickup_window_from_first_pickup_stop():
    o = _order(
        compliance_metadata={
            "stops": [
                {
                    "type": "pickup",
                    "sequence": 0,
                    "time_window_start": "2026-08-07T14:00:00",
                    "time_window_end": "2026-08-07T16:00:00",
                },
                {"type": "dropoff", "sequence": 1},
            ]
        }
    )
    start, end = _pickup_window(o)
    assert start == "2026-08-07T14:00:00"
    assert end == "2026-08-07T16:00:00"


def test_scheduled_at_far_future_still_typed():
    o = _order(
        order_type=OrderType.SCHEDULED.value,
        scheduled_at=datetime.now(UTC).replace(tzinfo=None) + timedelta(days=2),
    )
    assert _is_scheduled_pickup(o) is True
