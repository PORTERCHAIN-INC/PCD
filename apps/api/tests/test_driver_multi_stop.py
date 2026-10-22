"""Multi-stop orders on the driver side: every stop straight from the assigned order.

Hub & spoke (1 pickup -> N drops) and multi pickup/drop (N -> N) are one order with the
whole plan in ``compliance_metadata.stops``. The driver sees each stop in order with its own
actions; no committed dispatch-route card is needed.
"""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from porterchain_api.admin_engine.operations_service import AdminOperationsService
from porterchain_api.booking_models import Order, OrderEvent
from porterchain_driver import multi_stops, stops as stops_mod
from porterchain_driver.jobs import JobsService
from porterchain_driver.next_stop import NextStopResolver
from porterchain_driver.pod import ProofOfDeliveryService
from porterchain_driver.pod_policy import PodMissing
from porterchain_driver.stops import StopsService
from tests.test_dispatch_phase2 import B, M, S, W, _driver, _order

pytestmark = pytest.mark.usefixtures("quiet_pool")


@pytest.fixture(autouse=True)
def _quiet(monkeypatch):
    monkeypatch.setattr(AdminOperationsService, "_enqueue_driver_book_optimize", staticmethod(lambda *a, **k: None))
    monkeypatch.setattr("porterchain_driver.sequence_store.read_sequence", lambda *_a, **_k: None)
    monkeypatch.setattr(NextStopResolver, "_driver_origin", lambda *_a, **_k: None)
    monkeypatch.setattr("porterchain_driver.pod_policy.assert_on_duty", lambda *_a, **_k: None)
    monkeypatch.setattr(stops_mod, "ENFORCE_DROP_POD", True)
    monkeypatch.setattr("porterchain_api.merchant_engine.scan_gate_service.ScanGateService.assert_complete",
                        lambda *_a, **_k: None)


def _stop(sid: str, kind: str, seq: int, addr: dict) -> dict:
    return {"id": sid, "type": kind, "sequence": seq, **addr}


def _multi(db: Session, driver_id: str, plan: list[dict], state: str = "DRIVER_EN_ROUTE") -> Order:
    first = next(s for s in plan if s["type"] == "pickup")
    last = [s for s in plan if s["type"] == "dropoff"][-1]
    o = _order(db, first, last, boxes=0, state=state, assigned_driver_id=driver_id,
               compliance_metadata={"booking_mode": "hub_spoke", "stops": plan})
    db.commit()
    return o


HUB_SPOKE = [_stop("p1", "pickup", 0, W), _stop("d1", "dropoff", 1, S), _stop("d2", "dropoff", 2, M),
             _stop("d3", "dropoff", 3, B)]


def _detail(db: Session, d, o: Order) -> list[dict]:
    return JobsService().job_detail(db, d, o.id)["stops"]


def test_job_detail_lists_every_stop_in_order(db: Session) -> None:
    d = _driver(db)
    o = _multi(db, d.id, HUB_SPOKE)
    rows = _detail(db, d, o)
    assert [r["stop_id"] for r in rows] == [
        f"{o.id}-pickup", f"{o.id}-dropoff.d1", f"{o.id}-dropoff.d2", f"{o.id}-dropoff"]
    assert [r["stop_type"] for r in rows] == ["pickup", "dropoff", "dropoff", "dropoff"]
    assert [r["status"] for r in rows] == ["driver_en_route", "locked", "locked", "locked"]
    assert [r["actions"] for r in rows] == [["arrive", "complete"], [], [], []]
    assert [r["stop_index"] for r in rows] == [1, 2, 3, 4] and rows[0]["stop_total"] == 4
    assert rows[2]["address"]["formatted"] == M["formatted"] and rows[2]["address"]["lat"] == M["lat"]
    # Same list on the driver's queue (no dispatch route needed).
    route = StopsService().assigned_route(db, d)
    assert [s.stop_id for s in route.stops] == [r["stop_id"] for r in rows]


def test_hub_and_spoke_walks_each_drop_with_live_tracking(db: Session) -> None:
    d, svc, pod = _driver(db), StopsService(), ProofOfDeliveryService()
    o = _multi(db, d.id, HUB_SPOKE)
    d1, d2, final = f"{o.id}-dropoff.d1", f"{o.id}-dropoff.d2", f"{o.id}-dropoff"

    with pytest.raises(ValueError, match="pickup_required"):
        svc.arrive_stop(db, d, d1, skip_presence=True)
    svc.deliver_stop(db, d, f"{o.id}-pickup")
    db.commit()
    assert db.get(Order, o.id).state == "PICKED_UP"

    nxt = NextStopResolver().resolve(db, d)
    assert nxt["stop_id"] == d1 and nxt["stop_key"] == "d1" and nxt["stop_index"] == 2
    rows = _detail(db, d, o)
    assert rows[1]["actions"][0] == "start_delivery" and rows[2]["status"] == "locked"

    # Start delivery on the first drop: out for delivery + live tracking, exactly once.
    svc.start_delivery(db, d, d1)
    svc.start_delivery(db, d, d1)
    db.commit()
    assert db.get(Order, o.id).state == "IN_TRANSIT"
    assert db.query(OrderEvent).filter(OrderEvent.order_id == o.id,
                                       OrderEvent.event_type == "order.in_transit").count() == 1

    assert svc.arrive_stop(db, d, d1, skip_presence=True).status == "arrived"
    with pytest.raises(PodMissing):
        svc.deliver_stop(db, d, d1)  # each drop needs its own proof
    with pytest.raises(ValueError, match="earlier_stops_open"):
        svc.arrive_stop(db, d, d2, skip_presence=True)
    with pytest.raises(ValueError, match="earlier_stops_open"):
        svc.deliver_stop(db, d, final, enforce_sequence=False)
    pod.capture_photo(db, d, d1, file_url="https://cdn.test/d1.jpg")
    assert svc.deliver_stop(db, d, d1).status == "delivered"
    db.commit()
    assert db.get(Order, o.id).state == "IN_TRANSIT"  # the order is not done after one drop
    assert NextStopResolver().resolve(db, d)["stop_id"] == d2

    pod.capture_photo(db, d, d2, file_url="https://cdn.test/d2.jpg")
    svc.deliver_stop(db, d, d2)
    db.commit()
    assert NextStopResolver().resolve(db, d)["stop_id"] == final
    # A middle drop's photo is not the final drop's proof.
    with pytest.raises(PodMissing):
        svc.deliver_stop(db, d, final)
    assert pod.complete_pod(db, d, d2).message == "not_final_stop"
    pod.capture_photo(db, d, final, file_url="https://cdn.test/final.jpg")
    svc.arrive_stop(db, d, final, skip_presence=True)
    svc.deliver_stop(db, d, final)
    db.commit()
    assert db.get(Order, o.id).state == "DELIVERED"
    assert [r["status"] for r in _detail(db, d, o)] == ["picked_up", "delivered", "delivered", "delivered"]


def test_multi_pickup_multi_drop_n_to_n(db: Session) -> None:
    d, svc = _driver(db), StopsService()
    plan = [_stop("pa", "pickup", 0, W), _stop("pb", "pickup", 1, M), _stop("da", "dropoff", 2, S),
            _stop("db", "dropoff", 3, B)]
    o = _multi(db, d.id, plan)
    rows = _detail(db, d, o)
    assert [r["stop_id"] for r in rows] == [
        f"{o.id}-pickup", f"{o.id}-pickup.pb", f"{o.id}-dropoff.da", f"{o.id}-dropoff"]
    svc.deliver_stop(db, d, f"{o.id}-pickup")
    db.commit()
    nxt = NextStopResolver().resolve(db, d)
    assert nxt["stop_id"] == f"{o.id}-pickup.pb" and nxt["stop_type"] == "pickup"
    with pytest.raises(ValueError, match="not_a_delivery_stop"):
        svc.start_delivery(db, d, f"{o.id}-pickup.pb")
    assert svc.arrive_stop(db, d, f"{o.id}-pickup.pb", skip_presence=True).status == "arrived"
    assert svc.deliver_stop(db, d, f"{o.id}-pickup.pb").status == "picked_up"  # pickup: no POD
    db.commit()
    rows = _detail(db, d, o)
    assert rows[2]["status"] == "pending" and rows[2]["actions"][0] == "start_delivery"
    assert rows[3]["status"] == "locked"


def test_legacy_additional_stops_and_single_orders(db: Session) -> None:
    d = _driver(db)
    legacy = _order(db, W, S, boxes=0, state="DRIVER_EN_ROUTE", assigned_driver_id=d.id,
                    compliance_metadata={"additional_stops": [{"formatted": "Mid St"}]})
    single = _order(db, W, S, boxes=0, state="PICKED_UP", assigned_driver_id=d.id)
    db.commit()
    rows = _detail(db, d, legacy)
    assert [r["stop_type"] for r in rows] == ["pickup", "dropoff", "dropoff"]
    assert rows[1]["stop_id"] == f"{legacy.id}-dropoff.s1" and rows[1]["address"]["formatted"] == "Mid St"
    rows = _detail(db, d, single)
    assert [r["stop_id"] for r in rows] == [f"{single.id}-pickup", f"{single.id}-dropoff"]
    assert rows[1]["actions"][0] == "start_delivery"
    assert multi_stops.split_stop_id(f"{single.id}-dropoff") == (single.id, "dropoff", None)


def test_api_schema_keeps_the_stops() -> None:
    from porterchain_api.schemas_driver import DriverJobDetailResponse, DriverNextStop

    assert "stops" in DriverJobDetailResponse.model_fields
    assert {"stop_key", "stop_index", "stop_total"} <= set(DriverNextStop.model_fields)
