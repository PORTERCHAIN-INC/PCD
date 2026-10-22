"""Delivery leg after pickup: the drop stays actionable, carry-overs stay listed,
"Start delivery" sends the order out for delivery (ORD-20261015-71FB4B regression)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from sqlalchemy.orm import Session

from porterchain_api.admin_engine.operations_service import AdminOperationsService
from porterchain_api.booking_models import Order, OrderEvent
from porterchain_api.config import get_settings
from porterchain_api.dispatch_engine.anomalies import stuck_items
from porterchain_api.dispatch_engine.exception_fixes import suggest
from porterchain_api.driver_engine.offline_executor import DriverOfflineExecutor
from porterchain_driver.job_legs import allowed_actions, stop_status_for_leg
from porterchain_driver.jobs import JobsService
from porterchain_driver.next_stop import NextStopResolver
from porterchain_driver.stops import StopsService
from tests.test_dispatch_phase2 import S, W, _ctx, _driver, _order

pytestmark = pytest.mark.usefixtures("quiet_pool")


@pytest.fixture(autouse=True)
def _quiet(monkeypatch):
    monkeypatch.setattr(AdminOperationsService, "_enqueue_driver_book_optimize", staticmethod(lambda *a, **k: None))
    monkeypatch.setattr("porterchain_driver.sequence_store.read_sequence", lambda *_a, **_k: None)
    monkeypatch.setattr(NextStopResolver, "_driver_origin", lambda *_a, **_k: None)


def _old(o: Order, days: int = 7) -> Order:
    o.scheduled_at = datetime.now(UTC) - timedelta(days=days)
    return o


def test_dropoff_is_actionable_once_picked_up() -> None:
    assert stop_status_for_leg("PICKED_UP", "pickup") == "picked_up"
    assert stop_status_for_leg("PICKED_UP", "dropoff") == "pending"
    assert stop_status_for_leg("IN_TRANSIT", "dropoff") == "in_transit"
    assert stop_status_for_leg("AT_PICKUP", "dropoff") == "locked"
    assert stop_status_for_leg("DELIVERED", "dropoff") == "delivered"
    assert allowed_actions("PICKED_UP")[0] == "start_delivery"
    assert "start_delivery" not in allowed_actions("IN_TRANSIT")


def test_next_stop_is_the_drop_after_pickup(db: Session) -> None:
    d = _driver(db)
    o = _order(db, W, S, state="PICKED_UP", assigned_driver_id=d.id)
    db.commit()
    nxt = NextStopResolver().resolve(db, d)
    assert nxt is not None and nxt["order_id"] == o.id and nxt["stop_type"] == "dropoff"


def test_unfinished_orders_from_earlier_days_stay_on_the_list(db: Session) -> None:
    d = _driver(db)
    carried = _old(_order(db, W, S, state="PICKED_UP", assigned_driver_id=d.id))
    done = _old(_order(db, W, S, state="POD_COMPLETED", assigned_driver_id=d.id))
    db.commit()
    jobs = JobsService().list_jobs(db, d)
    ids = {j["order_id"] for j in [jobs.get("current"), *jobs.get("upcoming", []), *jobs.get("jobs", [])] if j}
    assert carried.id in ids and done.id not in ids
    assert jobs["next_stop"]["order_id"] == carried.id
    assert jobs["next_stop"]["stop_id"] == f"{carried.id}-dropoff"


def test_start_delivery_goes_out_for_delivery(db: Session) -> None:
    d = _driver(db)
    o = _order(db, W, S, state="PICKED_UP", assigned_driver_id=d.id)
    db.commit()
    stop = StopsService().start_delivery(db, d, f"{o.id}-dropoff")
    db.commit()
    assert db.get(Order, o.id).state == "IN_TRANSIT" and stop.status == "in_transit"
    ev = db.query(OrderEvent).filter(OrderEvent.order_id == o.id, OrderEvent.event_type == "order.in_transit").all()
    assert len(ev) == 1
    StopsService().start_delivery(db, d, f"{o.id}-dropoff")  # idempotent
    assert db.query(OrderEvent).filter(OrderEvent.order_id == o.id,
                                       OrderEvent.event_type == "order.in_transit").count() == 1


def test_start_delivery_rejects_pickup_and_unpicked(db: Session) -> None:
    d = _driver(db)
    o = _order(db, W, S, state="AT_PICKUP", assigned_driver_id=d.id)
    db.commit()
    with pytest.raises(ValueError, match="not_a_delivery_stop"):
        StopsService().start_delivery(db, d, f"{o.id}-pickup")
    with pytest.raises(ValueError, match="pickup_required"):
        StopsService().start_delivery(db, d, f"{o.id}-dropoff")
    other = _driver(db)
    db.commit()
    with pytest.raises(LookupError):
        StopsService().start_delivery(db, other, f"{o.id}-dropoff")


def test_handoff_driver_gets_the_drop_and_can_start(db: Session) -> None:
    old, new = _driver(db), _driver(db)
    o = _old(_order(db, W, S, state="PICKED_UP", assigned_driver_id=old.id), days=2)
    ctx = _ctx(db)
    db.commit()
    AdminOperationsService().assign_driver(db, get_settings(), ctx, o.id, new.id)
    db.commit()
    assert NextStopResolver().resolve(db, old) is None
    nxt = NextStopResolver().resolve(db, new)
    assert nxt and nxt["stop_id"] == f"{o.id}-dropoff"
    StopsService().start_delivery(db, new, f"{o.id}-dropoff")
    db.commit()
    assert db.get(Order, o.id).state == "IN_TRANSIT"


def test_offline_replay_starts_delivery(db: Session) -> None:
    d = _driver(db)
    o = _order(db, W, S, state="PICKED_UP", assigned_driver_id=d.id)
    db.commit()
    DriverOfflineExecutor().execute(db, d, "start_delivery", {"stop_id": f"{o.id}-dropoff"})
    db.commit()
    assert db.get(Order, o.id).state == "IN_TRANSIT"


def test_stale_pickup_alert_for_admin() -> None:
    now = datetime.now(UTC)
    picked = SimpleNamespace(id="o1", order_number="ORD-1", state="PICKED_UP", assigned_driver_id="d1",
                             updated_at=now - timedelta(hours=3))
    transit = SimpleNamespace(id="o2", order_number="ORD-2", state="IN_TRANSIT", assigned_driver_id="d1",
                              updated_at=now - timedelta(hours=3))
    fresh = SimpleNamespace(id="o3", order_number="ORD-3", state="PICKED_UP", assigned_driver_id="d1",
                            updated_at=now - timedelta(minutes=5))
    items = {i["order_id"]: i for i in stuck_items([picked, transit, fresh], now)}
    assert items["o1"]["kind"] == "stale_pickup" and items["o1"]["type"] == "STALE_PICKUP"
    assert items["o2"]["kind"] == "stuck" and "o3" not in items
    fixes = suggest(items["o1"], plan_id=None, best_driver={"driver_id": "d2", "name": "Sam"}, next_slot=None)
    assert [f["action"] for f in fixes] == ["reassign", "contact"]


def test_start_route_is_served_wherever_arrive_is() -> None:
    from porterchain_api.main import app

    paths = set(app.openapi().get("paths", {}))
    arrive = {p for p in paths if p.endswith("/routes/{route_id}/stops/{stop_id}/arrive")}
    assert arrive
    for p in arrive:
        assert p.replace("/arrive", "/start") in paths
