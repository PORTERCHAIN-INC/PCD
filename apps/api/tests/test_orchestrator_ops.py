"""Orchestrator ops service — fleetbase id resolution helpers."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from porterchain_api.admin_engine.orchestrator_ops_service import OPTIMIZE_STATES
from porterchain_api.booking_engine.numbers import generate_order_number, generate_tracking_number
from porterchain_api.domain.states import OrderState
from porterchain_api.booking_models import Order


def test_optimize_states_include_dispatch_ready():
    assert OrderState.DISPATCH_READY.value in OPTIMIZE_STATES


def test_order_factory_fields_for_pool():
    o = Order(
        id=str(uuid4()),
        order_number=generate_order_number(),
        tracking_number=generate_tracking_number(),
        state=OrderState.DISPATCH_READY.value,
        amount_cents=1000,
        currency="cad",
        pickup={"formatted": "A"},
        dropoff={"formatted": "B"},
        scheduled_at=datetime.now(UTC).replace(tzinfo=None),
        fleetbase_order_id="order_abc",
    )
    assert o.fleetbase_order_id == "order_abc"
    assert o.state in OPTIMIZE_STATES
