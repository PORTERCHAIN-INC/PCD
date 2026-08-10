"""Exception actions — acknowledge / resolve / retry dispatch (control tower, P0-5)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from porterchain_api.admin_engine.control_tower_service import ControlTowerService
from porterchain_api.admin_engine.rbac import AdminContext, AdminRole
from porterchain_api.admin_models import AdminUser
from porterchain_api.booking_engine.numbers import generate_order_number, generate_tracking_number
from porterchain_api.domain.states import OrderState
from porterchain_api.models import Order, OrderException


def _ctx() -> AdminContext:
    return AdminContext(
        user=AdminUser(id=str(uuid4()), clerk_user_id="test", email="ops@porterchain.test"),
        role=AdminRole.SUPER_ADMIN,
    )


def _order(state: OrderState) -> Order:
    addr = {"formatted": "1 King St W, Toronto", "lat": 43.6488, "lng": -79.3817}
    return Order(
        id=str(uuid4()),
        order_number=generate_order_number(),
        tracking_number=generate_tracking_number(),
        state=state.value,
        amount_cents=3200,
        currency="cad",
        pickup=addr,
        dropoff=addr,
        scheduled_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
    )


def _exception(db: Session, order: Order) -> OrderException:
    exc = OrderException(
        id=str(uuid4()),
        order_id=order.id,
        type="delivery_failed",
        status="open",
        reported_by_type="driver",
        evidence={},
    )
    db.add(exc)
    db.commit()
    return exc


def test_acknowledge_marks_status_and_actor(db: Session) -> None:
    order = _order(OrderState.IN_TRANSIT)
    db.add(order)
    db.commit()
    exc = _exception(db, order)

    svc = ControlTowerService()
    out = svc.acknowledge_exception(db, _ctx(), exc.id)

    assert out["status"] == "acknowledged"
    assert out["acknowledged_by"] == "ops@porterchain.test"
    assert out["acknowledged_at"] is not None

    # Idempotent — second acknowledge keeps the original audit stamp.
    again = svc.acknowledge_exception(db, _ctx(), exc.id)
    assert again["acknowledged_at"] == out["acknowledged_at"]


def test_resolve_records_note_and_timestamp(db: Session) -> None:
    order = _order(OrderState.DELIVERED)
    db.add(order)
    db.commit()
    exc = _exception(db, order)

    svc = ControlTowerService()
    out = svc.resolve_exception(db, _ctx(), exc.id, note="Customer refunded")

    assert out["status"] == "resolved"
    assert out["resolution_note"] == "Customer refunded"
    assert out["resolved_at"] is not None

    with pytest.raises(ValueError, match="already_resolved"):
        svc.acknowledge_exception(db, _ctx(), exc.id)


def test_retry_requeues_failed_order_and_resolves(db: Session) -> None:
    order = _order(OrderState.FAILED)
    db.add(order)
    db.commit()
    exc = _exception(db, order)

    svc = ControlTowerService()
    out = svc.retry_exception_dispatch(db, _ctx(), exc.id)

    db.refresh(order)
    assert order.state == OrderState.DISPATCH_READY.value
    assert out["exception"]["status"] == "resolved"
    assert out["exception"]["resolved_at"] is not None
    assert (order.exceptions[0].resolution or {}).get("action") == "retry_dispatch"


def test_retry_rejects_non_failed_order(db: Session) -> None:
    order = _order(OrderState.IN_TRANSIT)
    db.add(order)
    db.commit()
    exc = _exception(db, order)

    svc = ControlTowerService()
    with pytest.raises(ValueError, match="order_not_retryable"):
        svc.retry_exception_dispatch(db, _ctx(), exc.id)


def test_missing_exception_raises_lookup(db: Session) -> None:
    svc = ControlTowerService()
    with pytest.raises(LookupError):
        svc.acknowledge_exception(db, _ctx(), str(uuid4()))
