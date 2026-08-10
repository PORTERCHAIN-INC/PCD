"""Control tower KPI strip + board card enrichments (P1-6 / P1-7)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

from sqlalchemy.orm import Session

from porterchain_api.admin_engine.control_tower_service import ControlTowerService
from porterchain_api.booking_engine.numbers import generate_order_number, generate_tracking_number
from porterchain_api.domain.states import OrderState
from porterchain_api.models import Order


def _order(state: OrderState = OrderState.IN_TRANSIT, **overrides) -> Order:
    addr = {"formatted": "1 King St W, Toronto", "lat": 43.6488, "lng": -79.3817}
    dest = {"formatted": "10 Yonge St, Toronto", "lat": 43.6426, "lng": -79.3744}
    return Order(
        id=str(uuid4()),
        order_number=generate_order_number(),
        tracking_number=generate_tracking_number(),
        state=state.value,
        amount_cents=3200,
        currency="cad",
        pickup=addr,
        dropoff=dest,
        scheduled_at=datetime.now(UTC) + timedelta(hours=2),
        created_at=datetime.now(UTC),
        **overrides,
    )


def test_stats_include_sla_and_deltas(db: Session) -> None:
    today = _order(OrderState.DELIVERED)
    today.created_at = datetime.now(UTC)
    today.updated_at = datetime.now(UTC)
    yesterday = _order(OrderState.DELIVERED)
    yesterday.created_at = datetime.now(UTC) - timedelta(days=1)
    yesterday.updated_at = datetime.now(UTC) - timedelta(days=1)
    db.add_all([today, yesterday])
    db.commit()

    stats = ControlTowerService().stats(db)
    assert "sla_at_risk" in stats
    assert "sla_breached" in stats
    assert "deltas" in stats
    assert "orders_today" in stats["deltas"]
    assert "revenue_today_cents" in stats["deltas"]
    assert "completed_today" in stats["deltas"]


def test_stop_progress_rich_stops() -> None:
    o = SimpleNamespace(
        state=OrderState.IN_TRANSIT.value,
        compliance_metadata={
            "stops": [
                {"type": "pickup", "sequence": 1},
                {"type": "dropoff", "sequence": 2},
                {"type": "dropoff", "sequence": 3},
            ]
        },
    )
    done, total = ControlTowerService._stop_progress(o)  # type: ignore[arg-type]
    assert total == 3
    assert done == 1


def test_order_card_exposes_sla_countdown(db: Session) -> None:
    order = _order(OrderState.DRIVER_EN_ROUTE)
    order.created_at = datetime.now(UTC)
    order.scheduled_at = datetime.now(UTC)  # instant — deadline = create + SLA hours
    db.add(order)
    db.commit()

    svc = ControlTowerService()
    card = svc._order_card(order, {}, {}, datetime.now(UTC).replace(tzinfo=None))
    assert card["stop_count"] >= 2
    assert "sla_minutes_remaining" in card
    assert card["sla_deadline"] is not None
