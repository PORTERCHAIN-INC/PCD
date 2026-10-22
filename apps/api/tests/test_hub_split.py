"""Split at warehouse: pickup leg to our hub and delivery leg from the hub, each with its own driver."""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from porterchain_api.admin_engine.fleet_plan_service import FleetPlanService
from porterchain_api.admin_engine.logistics_partners_service import HubSplitService
from porterchain_api.admin_engine.operations_service import AdminOperationsService
from porterchain_api.booking_models import Order, OrderEvent
from porterchain_api.config import get_settings
from porterchain_api.dispatch_engine.hub_legs import AT_HUB, TO_HUB, hub_leg
from porterchain_api.dispatch_engine.models import LogisticsPartner
from porterchain_driver.jobs import JobsService
from porterchain_driver.next_stop import NextStopResolver
from porterchain_driver.stops import StopsService
from tests.test_dispatch_phase2 import S, W, _ctx, _driver, _order

pytestmark = pytest.mark.usefixtures("quiet_pool")
HUB = {"lat": 43.7001, "lng": -79.5002}


@pytest.fixture(autouse=True)
def _quiet(monkeypatch):
    monkeypatch.setattr(AdminOperationsService, "_enqueue_driver_book_optimize", staticmethod(lambda *a, **k: None))
    monkeypatch.setattr("porterchain_driver.sequence_store.read_sequence", lambda *_a, **_k: None)
    monkeypatch.setattr(NextStopResolver, "_driver_origin", lambda *_a, **_k: None)


def _hub(db: Session, kind: str = "warehouse") -> LogisticsPartner:
    p = LogisticsPartner(name=f"Etobicoke Hub {uuid4().hex[:4]}", kind=kind, active=True, **HUB)
    db.add(p)
    db.flush()
    return p


def _events(db: Session, oid: str, kind: str) -> int:
    return db.query(OrderEvent).filter(OrderEvent.order_id == oid, OrderEvent.event_type == kind).count()


def test_full_split_flow_two_drivers(db: Session) -> None:
    ctx, hub = _ctx(db), _hub(db)
    first, second = _driver(db), _driver(db)
    o = _order(db, W, S, state="PICKED_UP", assigned_driver_id=first.id)
    db.commit()
    out = HubSplitService().split(db, get_settings(), ctx, o.id, hub_partner_id=hub.id,
                                  delivery_driver_id=second.id)
    assert out["split"] and out["stage"] == TO_HUB and out["pickup_driver_id"] == first.id

    # Pickup driver: the drop is the hub, no OTP/POD, no "out for delivery" to the receiver.
    stops = StopsService()
    nxt = NextStopResolver().resolve(db, first)
    assert nxt["stop_type"] == "dropoff" and nxt["hub_leg"] == "to_hub"
    assert nxt["address"]["lat"] == HUB["lat"] and "DROP AT HUB" in nxt["special_instructions"]
    stops.start_delivery(db, first, f"{o.id}-dropoff")
    arrived = stops.arrive_stop(db, first, f"{o.id}-dropoff")
    db.commit()
    assert arrived.status == "arrived" and not arrived.otp_required
    assert db.get(Order, o.id).state == "PICKED_UP" and _events(db, o.id, "order.in_transit") == 0

    done = stops.deliver_stop(db, first, f"{o.id}-dropoff")
    db.commit()
    order = db.get(Order, o.id)
    assert done.status == "completed" and order.state == "PICKED_UP"
    assert order.assigned_driver_id == second.id and _events(db, o.id, "order.hub_received") == 1
    assert hub_leg(db, o.id).stage == AT_HUB

    # Delivery driver: collect at the hub, then the real drop to the customer.
    job = JobsService()._job_summary(db, second, order)  # noqa: SLF001
    assert job["hub_leg"] == AT_HUB and job["pickup_address"] == hub.name
    nxt = NextStopResolver().resolve(db, second)
    assert nxt["stop_type"] == "dropoff" and nxt["address"]["lat"] == S["lat"]
    assert "Collect from hub" in nxt["special_instructions"]
    stops.start_delivery(db, second, f"{o.id}-dropoff")
    db.commit()
    assert db.get(Order, o.id).state == "IN_TRANSIT" and _events(db, o.id, "order.in_transit") == 1


def test_parcel_at_hub_without_driver_goes_to_plan_the_day(db: Session) -> None:
    ctx, hub, first = _ctx(db), _hub(db), _driver(db)
    o = _order(db, W, S, state="PICKED_UP", assigned_driver_id=first.id)
    db.commit()
    HubSplitService().split(db, get_settings(), ctx, o.id, hub_partner_id=hub.id)
    StopsService().deliver_stop(db, first, f"{o.id}-dropoff")
    db.commit()
    assert db.get(Order, o.id).assigned_driver_id is None

    plan = FleetPlanService()
    assert o.id in {x.id for x in plan._orders(db, None)}  # noqa: SLF001
    view = plan._hub_override(db, db.get(Order, o.id))  # noqa: SLF001
    assert view.pickup["lat"] == HUB["lat"] and view.dropoff["lat"] == S["lat"]

    later = _driver(db)
    AdminOperationsService().assign_driver(db, get_settings(), ctx, o.id, later.id)
    order = db.get(Order, o.id)
    assert order.assigned_driver_id == later.id and order.state == "PICKED_UP"
    assert hub_leg(db, o.id).delivery_driver_id == later.id


def test_split_before_pickup_routes_first_van_to_hub(db: Session) -> None:
    ctx, hub, first = _ctx(db), _hub(db), _driver(db)
    o = _order(db, W, S)
    db.commit()
    HubSplitService().split(db, get_settings(), ctx, o.id, hub_partner_id=hub.id, pickup_driver_id=first.id)
    assert db.get(Order, o.id).assigned_driver_id == first.id
    view = FleetPlanService()._hub_override(db, db.get(Order, o.id))  # noqa: SLF001
    assert view.dropoff["lat"] == HUB["lat"] and view.pickup["lat"] == W["lat"]
    drop = StopsService()._order_to_stop(db.get(Order, o.id), "dropoff")  # noqa: SLF001
    assert drop.status == "locked" and drop.hub_leg == "to_hub"


def test_split_guards(db: Session) -> None:
    ctx, hub = _ctx(db), _hub(db)
    svc = HubSplitService()
    delivered = _order(db, W, S, state="DELIVERED")
    fresh = _order(db, W, S)
    db.commit()
    with pytest.raises(ValueError, match="split_not_allowed_in_state"):
        svc.split(db, get_settings(), ctx, delivered.id, hub_partner_id=hub.id)
    with pytest.raises(LookupError, match="hub_not_found"):
        svc.split(db, get_settings(), ctx, fresh.id, hub_partner_id=_hub(db, "ftl").id)
    svc.split(db, get_settings(), ctx, fresh.id, hub_partner_id=hub.id)
    with pytest.raises(ValueError, match="already_split"):
        svc.split(db, get_settings(), ctx, fresh.id, hub_partner_id=hub.id)
    assert svc.view(db, delivered.id) == {"order_id": delivered.id, "split": False}


def test_unsplit_orders_unchanged(db: Session) -> None:
    d = _driver(db)
    o = _order(db, W, S, state="PICKED_UP", assigned_driver_id=d.id)
    db.commit()
    stop = StopsService()._order_to_stop(o, "dropoff")  # noqa: SLF001
    assert stop.hub_leg is None and stop.address["lat"] == S["lat"] and stop.otp_required


# ---------------------------------------------------------------- gaps closed
def _drop_at_hub(db, ctx, hub, first, second=None):
    o = _order(db, W, S, state="PICKED_UP", assigned_driver_id=first.id)
    db.commit()
    HubSplitService().split(db, get_settings(), ctx, o.id, hub_partner_id=hub.id,
                            delivery_driver_id=second.id if second else None)
    return o


def test_hub_geofence_follows_stop_presence_rule(db: Session, monkeypatch) -> None:
    from types import SimpleNamespace

    import porterchain_driver.navigation as nav

    ctx, hub, first = _ctx(db), _hub(db), _driver(db)
    o = _drop_at_hub(db, ctx, hub, first)
    monkeypatch.setattr(nav, "ENFORCE_STOP_PRESENCE", True)
    far = SimpleNamespace(lat=W["lat"], lng=W["lng"])  # still at the pickup, ~20 km away
    monkeypatch.setattr("porterchain_api.driver_engine.last_known.read_last_known", lambda _d: far)
    with pytest.raises(ValueError, match="not_at_stop"):
        StopsService().arrive_stop(db, first, f"{o.id}-dropoff")
    with pytest.raises(ValueError, match="not_at_stop"):
        StopsService().deliver_stop(db, first, f"{o.id}-dropoff")
    near = SimpleNamespace(lat=HUB["lat"] + 0.0003, lng=HUB["lng"])  # ~33 m
    monkeypatch.setattr("porterchain_api.driver_engine.last_known.read_last_known", lambda _d: near)
    assert StopsService().arrive_stop(db, first, f"{o.id}-dropoff").status == "arrived"
    # No GPS fix (no consent / off) never blocks, same as customer stops.
    monkeypatch.setattr("porterchain_api.driver_engine.last_known.read_last_known", lambda _d: None)
    StopsService().deliver_stop(db, first, f"{o.id}-dropoff")


def test_each_leg_is_paid_and_total_is_one_payout(db: Session, monkeypatch) -> None:
    from porterchain_api.driver_models import DriverWalletTransaction
    from porterchain_driver import stops as stops_mod
    from porterchain_driver.earnings import EarningsService

    monkeypatch.setattr(EarningsService, "resolve_delivery_payout_cents", lambda *_a, **_k: 3001)
    monkeypatch.setattr(stops_mod, "_assert_dropoff_pod_ready", lambda *_a, **_k: None)
    monkeypatch.setattr("porterchain_driver.pod_policy.assert_on_duty", lambda *_a, **_k: None)
    monkeypatch.setattr("porterchain_api.merchant_engine.scan_gate_service.ScanGateService.assert_complete",
                        lambda *_a, **_k: None)
    ctx, hub, first, second = _ctx(db), _hub(db), _driver(db), _driver(db)
    o = _drop_at_hub(db, ctx, hub, first, second)
    svc = StopsService()
    svc.deliver_stop(db, first, f"{o.id}-dropoff")
    db.commit()
    svc.deliver_stop(db, second, f"{o.id}-dropoff")
    db.commit()

    def paid(d):
        return [t.amount_cents for t in db.query(DriverWalletTransaction).filter(
            DriverWalletTransaction.driver_id == d.id, DriverWalletTransaction.reference_id == o.id)]

    assert paid(first) == [1500] and paid(second) == [1501]
    assert hub_leg(db, o.id) is None  # both legs finished


def test_plan_undo_releases_delivery_driver_of_parcel_at_hub(db: Session) -> None:
    from tests.test_dispatch_phase2 import _road

    ctx, hub, first = _ctx(db), _hub(db), _driver(db)
    o = _drop_at_hub(db, ctx, hub, first)
    StopsService().deliver_stop(db, first, f"{o.id}-dropoff")
    db.commit()
    van = _driver(db)
    svc = FleetPlanService(matrix_fn=_road, position_fn=lambda _d: (43.65, -79.38))
    plan = svc.plan(db, actor="t", order_ids=[o.id], driver_ids=[van.id], time_limit_s=1)
    done = svc.commit(db, get_settings(), ctx, plan["id"])
    assert done["summary"]["commit"]["assigned"] == 1
    assert db.get(Order, o.id).assigned_driver_id == van.id
    out = svc.undo(db, ctx, plan["id"])
    order = db.get(Order, o.id)
    assert out["released"] == 1 and order.assigned_driver_id is None and order.state == "PICKED_UP"
    assert hub_leg(db, o.id).delivery_driver_id is None


def test_unsplit_picked_up_order_plans_from_parcel_position(db: Session) -> None:
    from porterchain_api.driver_models import DriverLocationPing, DriverStopMeta

    d = _driver(db)
    o = _order(db, W, S, state="PICKED_UP")  # driver removed after pickup
    db.add(DriverStopMeta(order_id=o.id, driver_id=d.id, meta={"pickup_completed_at": "x"}))
    db.add(DriverLocationPing(driver_id=d.id, lat=43.70, lng=-79.40))
    db.commit()
    view = FleetPlanService()._hub_override(db, db.get(Order, o.id))  # noqa: SLF001
    assert view.pickup["lat"] == 43.70 and view.pickup["kind"] == "parcel"
    assert view.dropoff["lat"] == S["lat"]
