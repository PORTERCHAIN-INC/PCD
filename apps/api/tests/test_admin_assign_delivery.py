"""Admin can reassign the delivery driver after pickup (handoff keeps the order state)."""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from porterchain_api.admin_engine.operations_service import AdminOperationsService
from porterchain_api.admin_engine.orders_service import AdminOrdersService
from porterchain_api.admin_models import AdminAuditLog
from porterchain_api.booking_models import DomainEvent, Order, OrderEvent
from porterchain_api.config import get_settings
from tests.test_dispatch_phase2 import M, S, W, _commit_two, _ctx, _driver, _order

pytestmark = pytest.mark.usefixtures("quiet_pool")


@pytest.fixture(autouse=True)
def _no_optimize(monkeypatch):
    monkeypatch.setattr(AdminOperationsService, "_enqueue_driver_book_optimize", staticmethod(lambda *a, **k: None))


def _events(db: Session, order_id: str) -> list:
    return db.query(DomainEvent).filter(DomainEvent.aggregate_id == order_id).all()


@pytest.mark.parametrize("state", ["PICKED_UP", "IN_TRANSIT", "AT_DESTINATION", "DRIVER_ACCEPTED", "AT_PICKUP"])
def test_reassign_in_flight_keeps_state_and_notifies(db: Session, state: str) -> None:
    old, new = _driver(db), _driver(db)
    o = _order(db, W, S, state=state, assigned_driver_id=old.id)
    ctx = _ctx(db)
    db.commit()

    out = AdminOperationsService().assign_driver(db, get_settings(), ctx, o.id, new.id)
    assert out.assigned_driver_id == new.id and out.state == state

    ev = db.query(OrderEvent).filter(OrderEvent.order_id == o.id, OrderEvent.event_type == "order.driver_handoff").one()
    assert ev.from_state == ev.to_state == state and ev.payload["from_driver_id"] == old.id
    assert ev.payload["leg"] == ("delivery" if state in {"PICKED_UP", "IN_TRANSIT", "AT_DESTINATION"} else "pickup")
    audit = db.query(AdminAuditLog).filter(AdminAuditLog.resource_id == o.id,
                                           AdminAuditLog.action == "dispatch.reassigned").one()
    assert audit.payload == {"from_driver_id": old.id, "driver_id": new.id, "state": state, "leg": ev.payload["leg"]}
    kinds = {(e.event_type, (e.payload or {}).get("driver_id")) for e in _events(db, o.id)}
    assert ("order.driver_job_removed", old.id) in kinds
    assert ("order.driver_handoff", new.id) in kinds


def test_reassign_same_driver_is_rejected(db: Session) -> None:
    d = _driver(db)
    o = _order(db, W, S, state="PICKED_UP", assigned_driver_id=d.id)
    ctx = _ctx(db)
    db.commit()
    with pytest.raises(ValueError, match="driver_already_assigned"):
        AdminOperationsService().assign_driver(db, get_settings(), ctx, o.id, d.id)


def test_reassign_blocks_unapproved_driver(db: Session) -> None:
    old, bad = _driver(db), _driver(db)
    bad.status = "PENDING"
    o = _order(db, W, S, state="IN_TRANSIT", assigned_driver_id=old.id)
    ctx = _ctx(db)
    db.commit()
    with pytest.raises(ValueError, match="driver_not_approved"):
        AdminOperationsService().assign_driver(db, get_settings(), ctx, o.id, bad.id)
    assert db.get(Order, o.id).assigned_driver_id == old.id


def test_delivered_orders_still_cannot_be_reassigned(db: Session) -> None:
    old, new = _driver(db), _driver(db)
    o = _order(db, W, S, state="DELIVERED", assigned_driver_id=old.id)
    ctx = _ctx(db)
    db.commit()
    with pytest.raises(ValueError, match="Invalid order transition"):
        AdminOperationsService().assign_driver(db, get_settings(), ctx, o.id, new.id)


def test_bulk_assign_mixes_dispatch_ready_and_picked_up(db: Session) -> None:
    old, new = _driver(db), _driver(db)
    ready = _order(db, W, S)
    picked = _order(db, M, S, state="PICKED_UP", assigned_driver_id=old.id)
    ctx = _ctx(db)
    db.commit()
    res = AdminOrdersService().bulk_action(db, get_settings(), ctx, [ready.id, picked.id], "assign", driver_id=new.id)
    assert [r["status"] for r in res] == ["assigned", "assigned"]
    assert db.get(Order, ready.id).state == "DRIVER_ASSIGNED"
    p = db.get(Order, picked.id)
    assert p.state == "PICKED_UP" and p.assigned_driver_id == new.id


def test_handoff_moves_pending_plan_stops(db: Session, monkeypatch) -> None:
    from porterchain_api.dispatch_engine.driver_route import DriverRouteService

    _svc, ctx, _done, d1, o1, _o2 = _commit_two(db, monkeypatch)
    db.get(Order, o1.id).state = "PICKED_UP"
    db.commit()
    d2 = _driver(db)
    db.commit()
    AdminOperationsService().assign_driver(db, get_settings(), ctx, o1.id, d2.id)
    routes = DriverRouteService()
    src = routes.current_route(db, d1.id)
    dst = routes.current_route(db, d2.id)
    assert all(s["order_id"] != o1.id for s in (src.stops if src else []))
    assert dst is not None and any(s["order_id"] == o1.id for s in dst.stops)


def test_handoff_notification_specs() -> None:
    from porterchain_shared.events.catalog import DomainEventType

    from porterchain_api.notification_engine.event_router import _specs_for_event
    from porterchain_api.notification_engine.lanes import FAST_TEMPLATES
    from porterchain_api.notification_engine.templates import TEMPLATES

    payload = {"driver_id": "drv-2", "customer_id": "c-1", "merchant_id": "m-1",
               "order_number": "ORD-9", "tracking_number": "TRK-9"}
    specs = _specs_for_event(DomainEventType.DRIVER_HANDOFF, payload)
    got = {(s["recipient_type"], s["channel"], s["template_key"]) for s in specs}
    assert ("driver", "push", "job_handoff") in got and ("driver", "in_app", "job_handoff") in got
    assert ("merchant", "in_app", "driver_assigned") in got and ("customer", "in_app", "driver_assigned") in got
    assert not any(s["recipient_type"] == "merchant" and s["channel"] in ("push", "email", "sms") for s in specs)
    assert "job_handoff" in FAST_TEMPLATES
    assert "ORD-9" in TEMPLATES["job_handoff"]["body"].format(**payload)
