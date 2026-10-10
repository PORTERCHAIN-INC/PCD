"""Dispatch Phase 1: fleet capacity, vehicle/driver recommendation, ETA risk,
job offers (expiry + cascade), Exceptions queue and metrics."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from porterchain_api import crm_models, merchant_models, user_models  # noqa: F401 — FK targets
from porterchain_api.admin_engine.dispatch_board_service import DispatchBoardService
from porterchain_api.admin_engine.job_offers_service import JobOffersService
from porterchain_api.admin_models import AdminUser, Driver, Vehicle
from porterchain_api.booking_engine.numbers import (
    generate_order_number,
    generate_tracking_number,
)
from porterchain_api.booking_models import Order, OrderException, Package
from porterchain_api.dispatch_engine import eta_risk
from porterchain_api.dispatch_engine import fleet_capacity as fc
from porterchain_api.dispatch_engine import recommend as rc
from porterchain_api.dispatch_engine.models import DispatchJobOffer
from porterchain_api.domain.admin_states import DriverStatus
from porterchain_api.domain.states import OrderState

# ---------- pure ----------


def test_default_fleet_is_g_licence_only_and_ordered() -> None:
    fleet = fc.default_fleet()
    assert [v["id"] for v in fleet["vehicles"]] == ["sedan", "suv", "van", "box_truck"]
    assert fleet["hourly_cost_cents"] == 2700
    assert fleet["max_fill"] == 0.85
    assert fleet["offer_ttl_seconds"] == 180


def test_normalize_rejects_bad_rows() -> None:
    with pytest.raises(ValueError):
        fc.normalize_fleet({"vehicles": [{"id": "semi_trailer", "max_kg": 1, "max_m3": 1, "max_boxes": 1}]})
    with pytest.raises(ValueError):
        fc.normalize_fleet({"max_fill": 1.5})
    with pytest.raises(ValueError):
        fc.normalize_fleet({"offer_ttl_seconds": 5})
    ok = fc.normalize_fleet({"vehicles": [{"id": "Cargo Van", "max_kg": 800, "max_m3": 3, "max_boxes": 40}]})
    assert ok["vehicles"][0]["id"] == "van"


def test_smallest_fitting_respects_85_percent() -> None:
    fleet = fc.default_fleet()
    assert fc.smallest_fitting(fc.Load(10, 0.05, 2), fleet)["id"] == "sedan"
    # 140 kg is 93% of a sedan → SUV.
    assert fc.smallest_fitting(fc.Load(140, 0.1, 3), fleet)["id"] == "suv"
    # Volume drives it: 2 m3 → van.
    assert fc.smallest_fitting(fc.Load(50, 2.0, 5), fleet)["id"] == "van"
    assert fc.smallest_fitting(fc.Load(5000, 1, 1), fleet) is None


def test_order_load_from_packages() -> None:
    order = SimpleNamespace(
        packages=[
            SimpleNamespace(weight_kg=10, dimensions={"length": 50, "width": 40, "height": 30, "unit": "cm"}),
            SimpleNamespace(weight_kg=5, dimensions=None),
        ]
    )
    load = fc.order_load(order)
    assert load.kg == 15 and load.boxes == 2 and load.m3 == pytest.approx(0.06, abs=1e-3)
    assert fc.order_load(SimpleNamespace(packages=[])) == fc.Load(0, 0, 1)


def test_rank_prefers_feasible_then_cost_then_smaller() -> None:
    a = rc.Candidate("a", "A", "van", 0, fc.Load(), (0, 0), "GPS", cost_cents=900)
    b = rc.Candidate("b", "B", "sedan", 0, fc.Load(), (0, 0), "GPS", cost_cents=900)
    c = rc.Candidate("c", "C", "sedan", 0, fc.Load(), (0, 0), "GPS", cost_cents=500, blocked="over_capacity")
    d = rc.Candidate("d", "D", "suv", 1, fc.Load(), (0, 0), "GPS", cost_cents=700)
    assert [x.driver_id for x in rc.rank([a, b, c, d])] == ["d", "b", "a", "c"]


def test_score_insertion_uses_matrix_and_pay_plan() -> None:
    cands = [rc.Candidate("a", "A", "sedan", 0, fc.Load(), (1, 1), "GPS")]
    # rows: start, pickup, dropoff
    matrix = [[0, 600, 0], [0, 0, 1200], [0, 0, 0]]
    plan = {"mode": "hourly", "hourly_cents": 2700}
    rc.score_insertion(cands, (2, 2), (3, 3), matrix=matrix, service_minutes=8, plan_raw=plan, hourly_cents=2700)
    assert cands[0].minutes == pytest.approx(46.0)  # 10 + 20 + 2×8
    assert cands[0].cost_cents and cands[0].cost_cents > 0


def test_score_insertion_without_valhalla_does_not_guess() -> None:
    cands = [rc.Candidate("a", "A", "sedan", 0, fc.Load(), (1, 1), "GPS")]
    rc.score_insertion(cands, (2, 2), (3, 3), matrix=None, service_minutes=8, plan_raw=None, hourly_cents=2700)
    assert cands[0].minutes is None and cands[0].cost_cents is None


def test_eta_classify() -> None:
    now = datetime(2026, 10, 9, 15, 0, tzinfo=UTC)
    promise = now + timedelta(minutes=30)
    assert eta_risk.classify(now=now, eta=now + timedelta(minutes=10), promise=promise, at_risk_minutes=10) == "on_time"
    assert eta_risk.classify(now=now, eta=now + timedelta(minutes=25), promise=promise, at_risk_minutes=10) == "at_risk"
    assert eta_risk.classify(now=now + timedelta(hours=1), eta=None, promise=promise, at_risk_minutes=10) == "late"
    assert eta_risk.classify(now=now, eta=None, promise=promise, at_risk_minutes=10) == "unknown"
    assert eta_risk.classify(now=now, eta=now, promise=None, at_risk_minutes=10) == "unknown"


def test_eta_for_before_and_after_pickup() -> None:
    now = datetime(2026, 10, 9, 15, 0, tzinfo=UTC)
    order = SimpleNamespace(state="DRIVER_EN_ROUTE", pickup={"lat": 1, "lng": 1}, dropoff={"lat": 2, "lng": 2})
    fn = lambda pts, _v: [[0, 300, 0], [0, 0, 600], [0, 0, 0]][: len(pts)]
    eta = eta_risk.eta_for(order, (0, 0), now=now, service_minutes=5, matrix_fn=fn)
    assert eta == now + timedelta(seconds=900, minutes=10)
    order.state = "IN_TRANSIT"
    fn2 = lambda pts, _v: [[0, 120], [0, 0]]
    assert eta_risk.eta_for(order, (0, 0), now=now, service_minutes=5, matrix_fn=fn2) == now + timedelta(seconds=120, minutes=5)
    assert eta_risk.eta_for(order, None, now=now, service_minutes=5, matrix_fn=fn2) is None


# ---------- DB ----------


def _order(state: OrderState = OrderState.DISPATCH_READY, **kw) -> Order:
    return Order(
        id=str(uuid4()),
        order_number=generate_order_number(),
        tracking_number=generate_tracking_number(),
        state=state.value,
        amount_cents=3200,
        currency="cad",
        pickup={"lat": 43.6488, "lng": -79.3817},
        dropoff={"lat": 43.6426, "lng": -79.3744},
        scheduled_at=datetime.now(UTC) + timedelta(hours=2),
        **kw,
    )


def _driver(db: Session, cls: str = "sedan") -> Driver:
    s = uuid4().hex[:8]
    d = Driver(
        email=f"d-{s}@dispatch.test",
        full_name=f"Driver {s}",
        status=DriverStatus.APPROVED.value,
        clerk_user_id=f"clerk_dispatch_{s}",
        is_online=True,
        license_verified=True,
        insurance_verified=True,
        background_check_status="cleared",
    )
    db.add(d)
    db.flush()
    db.add(Vehicle(driver_id=d.id, vehicle_class=cls, plate_number=f"T{s[:6]}", is_active=True))
    db.flush()
    return d


def _admin(db: Session) -> AdminUser:
    a = AdminUser(email=f"ops-{uuid4().hex[:6]}@dispatch.test", role="admin", is_active=True)
    db.add(a)
    db.flush()
    return a


def test_recommend_for_order_picks_vehicle_and_ranks(db: Session) -> None:
    o = _order()
    db.add(o)
    db.flush()
    db.add(Package(order_id=o.id, parcel_index=1, total_parcels=1, tracking_suffix=f"{o.tracking_number}-1", weight_kg=200))
    near, far = _driver(db, "suv"), _driver(db, "sedan")
    db.commit()
    pos = {near.id: (43.65, -79.38), far.id: (43.80, -79.20)}

    def matrix(points, _v):
        # start rows: whichever driver is closer to pickup gets fewer seconds.
        n = len(points)
        m = [[0] * n for _ in range(n)]
        for i, p in enumerate(points[:-2]):
            m[i][n - 2] = 300 if p == pos[near.id] else 2400
        m[n - 2][n - 1] = 600
        return m

    from porterchain_api.admin_engine.dispatch_board_service import recommend

    out = recommend(db, o.id, matrix_fn=matrix, position_fn=lambda did: pos.get(did), driver_ids=list(pos))
    assert out["vehicle"]["id"] == "suv"  # 200 kg > 85% of a sedan
    mine = [d for d in out["drivers"] if d["driver_id"] in pos]
    blocked = {d["driver_id"]: d["blocked"] for d in mine}
    assert blocked[far.id] == "over_capacity"  # sedan cannot take 200 kg
    assert blocked[near.id] is None
    assert out["matrix"] == "valhalla"


def test_offer_expires_and_passes_to_next_driver(db: Session) -> None:
    o = _order()
    db.add(o)
    a, b = _driver(db), _driver(db)
    admin = _admin(db)
    db.commit()
    ranked = {"drivers": [{"driver_id": a.id, "blocked": None}, {"driver_id": b.id, "blocked": None}]}
    svc = JobOffersService(recommend_fn=lambda _db, _oid: ranked)
    t0 = datetime.now(UTC)

    first = svc.offer(db, o.id, actor_id=admin.id, now=t0)["offer"]
    assert first["driver_id"] == a.id and first["seconds_left"] == 180
    # Second offer call is idempotent while one is pending.
    assert svc.offer(db, o.id, actor_id=admin.id, now=t0)["created"] is False

    res = svc.sweep(db, now=t0 + timedelta(seconds=181))
    assert res["expired"] >= 1
    rows = db.query(DispatchJobOffer).filter(DispatchJobOffer.order_id == o.id).order_by(DispatchJobOffer.rank).all()
    assert [(r.driver_id, r.status) for r in rows] == [(a.id, "expired"), (b.id, "pending")]

    # b declines → nobody left → DRIVER_TIMEOUT exception for the queue.
    svc.respond(db, rows[1].id, driver_id=b.id, accept=False, now=t0 + timedelta(seconds=190))
    exc = db.query(OrderException).filter(OrderException.order_id == o.id, OrderException.type == "DRIVER_TIMEOUT").one()
    assert exc.status == "open"


def test_offer_accept_assigns_and_accepts(db: Session) -> None:
    o = _order()
    db.add(o)
    a = _driver(db)
    admin = _admin(db)
    db.commit()
    svc = JobOffersService(recommend_fn=lambda _db, _oid: {"drivers": [{"driver_id": a.id, "blocked": None}]})
    offer = svc.offer(db, o.id, actor_id=admin.id)["offer"]
    with pytest.raises(LookupError):
        svc.respond(db, offer["id"], driver_id="someone-else", accept=True)
    svc.respond(db, offer["id"], driver_id=a.id, accept=True)
    db.refresh(o)
    assert o.assigned_driver_id == a.id
    assert o.state == OrderState.DRIVER_ACCEPTED.value
    with pytest.raises(ValueError):
        svc.respond(db, offer["id"], driver_id=a.id, accept=True)


def test_exceptions_queue_unifies_sources(db: Session) -> None:
    old = _order(created_at=datetime.now(UTC) - timedelta(minutes=40))
    failed = _order(OrderState.FAILED)
    damaged = _order(OrderState.DAMAGED)
    db.add_all([old, failed, damaged])
    db.commit()
    eta_rows = [{"order_id": "x-late", "order_number": "PC-X", "state": "IN_TRANSIT", "status": "late", "eta": None, "promise": None}]
    out = DispatchBoardService().exceptions_queue(db, etas_fn=lambda _db: eta_rows)
    by_order = {i["order_id"]: i for i in out["items"]}
    assert by_order[old.id]["kind"] == "unassigned"
    assert by_order[failed.id]["kind"] == "failed"
    assert by_order[damaged.id]["severity"] == "critical"
    assert by_order["x-late"]["kind"] == "late"
    sev = [i["severity"] for i in out["items"]]
    assert sev == sorted(sev, key=lambda s: {"critical": 0, "high": 1, "medium": 2, "low": 3}[s])


def test_exceptions_queue_survives_eta_outage(db: Session) -> None:
    def boom(_db):
        raise RuntimeError("valhalla down")

    out = DispatchBoardService().exceptions_queue(db, etas_fn=boom)
    assert out["eta"] == "unavailable"


def test_metrics_shape(db: Session) -> None:
    out = DispatchBoardService().metrics(db, days=7)
    for key in (
        "order_to_dispatch_min",
        "on_time_pct",
        "first_attempt_pct",
        "cost_per_stop_cents",
        "fill_pct",
        "stops_per_driver_hour",
    ):
        assert key in out
    assert out["hourly_cost_cents"] == 2700


def test_fleet_put_admin_only_and_validated(db: Session) -> None:
    svc = DispatchBoardService()
    admin = _admin(db)
    sales = SimpleNamespace(user=admin, role=SimpleNamespace(value="sales"))
    with pytest.raises(PermissionError):
        svc.fleet_put(db, sales, {"max_fill": 0.8})
    ctx = SimpleNamespace(user=admin, role=SimpleNamespace(value="admin"))
    with pytest.raises(ValueError):
        svc.fleet_put(db, ctx, {"max_fill": 2})
    saved = svc.fleet_put(db, ctx, {"max_fill": 0.8})
    assert saved["max_fill"] == 0.8
    assert svc.fleet_get(db)["max_fill"] == 0.8
    svc.fleet_put(db, ctx, fc.default_fleet())
