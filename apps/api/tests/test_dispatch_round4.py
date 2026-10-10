"""Dispatch round 4: scans, volume, windows, learned stop times, fixes, offline replay, margin."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from porterchain_api import crm_models, merchant_models, user_models  # noqa: F401 — FK targets
from porterchain_api.admin_engine.dispatch_board_service import DispatchBoardService
from porterchain_api.admin_engine.exception_fixes_service import (
    ExceptionFixesService,
    next_slot,
)
from porterchain_api.admin_engine.fleet_plan_service import FleetPlanService
from porterchain_api.booking_models import OrderException
from porterchain_api.config import get_settings
from porterchain_api.dispatch_engine import (
    exception_fixes,
    fleet_capacity,
    margin,
    stop_times,
    vrp,
    windows,
)
from porterchain_api.dispatch_engine.driver_route import (
    PICKUP_KINDS,
    DriverRouteService,
)
from porterchain_api.dispatch_engine.models import (
    DispatchFixAction,
    DispatchStopEvent,
    DispatchStopTime,
)
from porterchain_api.dispatch_engine.stop_shapes import StopSpec
from porterchain_api.merchant_engine.scan_gate_service import ScanGateService
from tests.test_dispatch_phase2 import (
    S,
    W,
    _ctx,
    _driver,
    _order,
    _road,
    all_exceptions,
)

pytestmark = pytest.mark.usefixtures("quiet_pool")
NOW = datetime(2026, 10, 9, 14, 0, tzinfo=UTC)
PHOTO = "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwg"


@pytest.fixture(autouse=True)
def _pod_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("POD_MEDIA_DIR", str(tmp_path / "pod"))
    from porterchain_api.admin_engine.operations_service import AdminOperationsService

    monkeypatch.setattr(AdminOperationsService, "_enqueue_driver_book_optimize", staticmethod(lambda *a, **k: None))


# ---------------------------------------------------------------- windows
def test_drop_window_prefers_customer_choice() -> None:
    booked = {"delivery_window": {"start": "2026-10-09T18:00:00Z", "end": "2026-10-09T20:00:00Z"}}
    chosen = {**booked, "cx": {"schedule": {"window_start": "2026-10-09T15:00:00+00:00",
                                            "window_end": "2026-10-09T16:00:00+00:00"}}}
    assert windows.drop_window(SimpleNamespace(compliance_metadata=booked))[0].hour == 18
    assert windows.drop_window(SimpleNamespace(compliance_metadata=chosen))[0].hour == 15
    assert windows.drop_window(SimpleNamespace(compliance_metadata=None)) == (None, None)
    assert windows.to_offsets(windows.drop_window(SimpleNamespace(compliance_metadata=chosen)), NOW) == (3600, 7200)
    assert windows.to_offsets((None, NOW - timedelta(hours=1)), NOW) == (None, 0)  # closed: late, still served


def _problem(stops, pairs, vehicles):
    pts = vrp.points(vehicles, stops)
    return vrp.Problem(stops=stops, pairs=pairs, vehicles=vehicles, matrix=_road(pts), time_limit_s=1)


def test_vrp_waits_for_window_and_scores_late() -> None:
    p = StopSpec("a:p", "a", "pickup", W["lat"], W["lng"], boxes=1, kg=1, service_s=60)
    d = StopSpec("a:d", "a", "drop", S["lat"], S["lng"], boxes=1, kg=1, service_s=60, window_start_s=7200)
    v = vrp.Vehicle("v1", None, "van", 900, 45, (W["lat"], W["lng"]))
    prob = _problem([p, d], [("a:p", "a:d")], [v])
    plan = vrp.evaluate(prob, vrp.solve_ortools(prob))
    assert plan["dropped"] == [] and plan["routes"][0]["stops"][1]["eta_s"] == 7200
    d.window_start_s, d.window_end_s = None, 10  # impossible close → served late, not dropped
    plan = vrp.evaluate(prob, vrp.solve_ortools(prob))
    assert plan["dropped"] == [] and plan["late_stops"] == ["a:d"]


def test_vrp_volume_capacity_splits_load() -> None:
    stops, pairs = [], []
    for i in range(2):
        stops += [StopSpec(f"{i}:p", str(i), "pickup", W["lat"], W["lng"], boxes=1, kg=1, m3=0.6),
                  StopSpec(f"{i}:d", str(i), "drop", S["lat"], S["lng"], boxes=1, kg=1, m3=0.6)]
        pairs.append((f"{i}:p", f"{i}:d"))
    vans = [vrp.Vehicle(f"v{i}", None, "suv", 300, 16, (W["lat"], W["lng"]), cap_m3=0.9) for i in range(2)]
    plan = vrp.evaluate(_problem(stops, pairs, vans), vrp.solve_ortools(_problem(stops, pairs, vans)))
    assert plan["feasible"] and plan["vehicles_used"] == 2
    assert all(r["peak_m3"] <= 0.9 for r in plan["routes"])


# ---------------------------------------------------------------- cubic feet
def test_fleet_cubic_feet_roundtrip() -> None:
    fleet = fleet_capacity.default_fleet()
    van = fleet_capacity.vehicle_by_id(fleet, "van")
    assert van["max_ft3"] == pytest.approx(3.5 * fleet_capacity.FT3_PER_M3, abs=0.1)
    edited = fleet_capacity.normalize_fleet({"vehicles": [{**van, "max_ft3": 300, "max_m3": None}]})
    assert edited["vehicles"][0]["max_m3"] == pytest.approx(300 / fleet_capacity.FT3_PER_M3, abs=0.001)
    assert fleet_capacity._dims_m3({"length": 1, "width": 1, "height": 1, "unit": "ft"}) == pytest.approx(0.0283, abs=1e-4)
    assert fleet["margin_floor_pct"] == fleet_capacity.MARGIN_FLOOR_PCT
    with pytest.raises(ValueError):
        fleet_capacity.normalize_fleet({"margin_floor_pct": 95})


# ---------------------------------------------------------------- learned stop times
def test_stop_time_durations_and_fallback() -> None:
    t = NOW
    rows = [("r", "k1", "arrived", t), ("r", "k1", "delivered", t + timedelta(seconds=240)),
            ("r", "k2", "arrived", t), ("r", "k2", "delivered", t + timedelta(seconds=5)),  # a double tap
            ("r", "k3", "arrived", t)]  # never finished
    assert stop_times.durations(rows) == {("r", "k1"): 240}
    st = stop_times.StopTimes(default_s=480, table={("fsa", "M5H", "drop"): 200, ("place", "43.6467,-79.3832", "drop"): 90})
    assert st.seconds("drop", fsa="M5H", place="43.6467,-79.3832") == 90
    assert st.seconds("return_drop", fsa="M5H") == 200
    assert st.seconds("pickup", fsa="M5H") == 480 and st.source("pickup", fsa="M5H") == "default"


def test_learn_from_checkins_feeds_planner(db: Session) -> None:
    d = _driver(db)
    fsa = f"Z{uuid4().hex[:2].upper()}"
    from porterchain_api.dispatch_engine.models import DispatchPlan, DispatchRoute

    plan = DispatchPlan(service_date=NOW.date(), status="committed")
    db.add(plan)
    db.flush()
    keys = [f"o{i}:d0:0" for i in range(3)]
    orders = [_order(db, W, S) for _ in keys]
    route = DispatchRoute(plan_id=plan.id, vehicle_id="v", driver_id=d.id, vehicle_class="van", status="committed",
                          stops=[{"key": k, "order_id": o.id, "kind": "drop", "fsa": fsa, "place": None}
                                 for k, o in zip(keys, orders)])
    db.add(route)
    db.flush()
    for k, o, secs in zip(keys, orders, (120, 180, 600)):
        db.add(DispatchStopEvent(route_id=route.id, stop_key=k, order_id=o.id, driver_id=d.id, event="arrived", at=NOW))
        db.add(DispatchStopEvent(route_id=route.id, stop_key=k, order_id=o.id, driver_id=d.id, event="delivered",
                                 at=NOW + timedelta(seconds=secs)))
    db.flush()
    out = stop_times.learn(db, now=NOW + timedelta(hours=1))
    assert out["keys_written"] >= 1
    row = db.query(DispatchStopTime).filter_by(scope="fsa", scope_key=fsa, kind="drop").one()
    assert row.median_s == 180 and row.samples == 3
    assert stop_times.load(db, 480).seconds("drop", fsa=fsa) == 180


# ---------------------------------------------------------------- margin + fix rules
def test_margin_maths() -> None:
    routes = [{"cost_cents": 1000, "stops": [{"order_id": "a"}, {"order_id": "a"}, {"order_id": "b"}, {"order_id": "c"}]}]
    assert margin.order_costs(routes) == {"a": 500, "b": 250, "c": 250}
    assert margin.margin_pct(1000, 750) == 25.0 and margin.below_floor(1000, 850, 20)
    quoted = SimpleNamespace(amount_cents=1130, quote=SimpleNamespace(pricing_breakdown={"summary": {"subtotal_cents": 1000}}))
    assert margin.order_price_cents(quoted) == 1000  # pre-tax, as the pricing engine quoted it
    assert margin.order_price_cents(SimpleNamespace(amount_cents=900, quote=None)) == 900


def test_fix_rules() -> None:
    best = {"driver_id": "d1", "name": "Ada", "insertion_minutes": 6}
    slot = datetime(2026, 10, 12, 13, 0, tzinfo=UTC)
    late = exception_fixes.suggest({"kind": "late", "type": "LATE", "state": "DRIVER_ASSIGNED"},
                                   plan_id="p", best_driver=best, next_slot=slot)
    assert [f["action"] for f in late] == ["reassign", "reroute", "contact"]
    failed = exception_fixes.suggest({"kind": "failed", "type": "FAILED", "state": "FAILED"},
                                     plan_id=None, best_driver=None, next_slot=slot)
    assert [f["action"] for f in failed] == ["reschedule", "contact"]
    assert exception_fixes.suggest({"kind": "unassigned", "type": "UNASSIGNED", "state": "DISPATCH_READY"},
                                   plan_id=None, best_driver=None, next_slot=slot) == []
    for item in ({"kind": "damaged", "type": "DAMAGED"}, {"kind": "lost", "type": "LOST"},
                 {"kind": "exception", "type": "PARCEL_DAMAGED"}, {"kind": "claim", "type": "CLAIM_OPEN"},
                 {"kind": "return", "type": "RETURN_TO_SENDER"}):
        fixes = exception_fixes.suggest({**item, "state": "DAMAGED"}, plan_id="p", best_driver=best, next_slot=slot)
        assert [f["action"] for f in fixes] == ["contact"], item  # critical rows always get a next step
        assert "late" not in fixes[0]["params"]["message"]  # never a "running late" email for a damaged parcel
    assert next_slot(datetime(2026, 10, 10, 15, 0, tzinfo=UTC)).weekday() == 0  # Saturday → Monday 09:00
    assert next_slot(datetime(2026, 10, 9, 11, 0, tzinfo=UTC)).day == 9  # Friday 07:00 Toronto → today 09:00


# ---------------------------------------------------------------- end to end
def test_round4_day_end_to_end(db: Session) -> None:
    """Window → plan → commit → scan-gated check-ins (offline replay) → short drop alert →
    exceptions with suggested fixes → admin applies one → margin alert."""
    d = _driver(db)
    start = datetime.now(UTC) + timedelta(hours=3)
    o = _order(db, W, S, boxes=2, compliance_metadata={
        "cx": {"schedule": {"window_start": start.isoformat(), "window_end": (start + timedelta(hours=1)).isoformat()}}})
    o.amount_cents = 50  # far under any route cost → margin alert
    plans = FleetPlanService(matrix_fn=_road, position_fn=lambda _d: (43.65, -79.38))
    plan = plans.plan(db, actor="t", order_ids=[o.id], driver_ids=[d.id], time_limit_s=1)
    drop = next(s for r in plan["routes"] for s in r["stops"] if s["kind"] == "drop")
    assert drop["eta_s"] >= 3 * 3600 - 120  # waits for the customer's window
    ctx = _ctx(db)
    plans.commit(db, get_settings(), ctx, plan["id"])

    gate_svc = ScanGateService()
    gate = lambda order, phase: gate_svc.scan_progress(db, order, phase=phase)
    rs = DriverRouteService()
    route = rs.view(db, d.id)["route"]
    pickup, dropstop = route["stops"][0], route["stops"][1]
    assert pickup["kind"] in PICKUP_KINDS
    rs.check_in(db, d, keys=pickup["keys"], event="arrived", client_id="c-arrive", scan_gate=gate)
    with pytest.raises(PermissionError, match="scan_required:pickup"):
        rs.check_in(db, d, keys=pickup["keys"], event="picked_up", scan_gate=gate)
    for i in range(2):
        gate_svc.scan_qr(db, o, f"{o.tracking_number}-{i}", phase="pickup")
    rs.check_in(db, d, keys=pickup["keys"], event="picked_up", client_id="c-pick", scan_gate=gate)
    events = db.query(DispatchStopEvent).filter(DispatchStopEvent.order_id == o.id).count()
    replay = rs.check_in(db, d, keys=pickup["keys"], event="picked_up", client_id="c-pick", scan_gate=gate)
    assert replay["replayed"] is True
    assert db.query(DispatchStopEvent).filter(DispatchStopEvent.order_id == o.id).count() == events

    rs.check_in(db, d, keys=dropstop["keys"], event="arrived", scan_gate=gate)
    gate_svc.scan_qr(db, o, f"{o.tracking_number}-0", phase="delivery")
    with pytest.raises(PermissionError, match="scan_required:delivery"):
        rs.check_in(db, d, keys=dropstop["keys"], event="delivered", pod_photo=PHOTO, scan_gate=gate)
    rs.check_in(db, d, keys=dropstop["keys"], event="delivered", pod_photo=PHOTO, short_reason="box 2 not on van",
                scan_gate=gate)
    alert = db.query(OrderException).filter_by(order_id=o.id, type="package_short_at_drop").one()
    assert alert.evidence["missing_suffixes"] == [f"{o.tracking_number}-1"]

    failed = _order(db, W, S, state="FAILED")
    fixes = ExceptionFixesService(recommend_fn=lambda _db, _oid: {"drivers": [], "best_driver_id": None})
    queue = all_exceptions(DispatchBoardService(), db, etas_fn=lambda _db: [], fixes=fixes)
    by_id = {i["id"]: i for i in queue["items"]}
    assert [f["action"] for f in by_id[f"exc:{alert.id}"]["fixes"]] == ["contact"]
    fix = by_id[f"state:{failed.id}"]["fixes"][0]
    assert fix["action"] == "reschedule"
    out = fixes.apply(db, get_settings(), ctx, item_id=f"state:{failed.id}", order_id=failed.id,
                      action=fix["action"], params=fix["params"])
    assert out["result"]["state"] == "DISPATCH_READY"
    assert db.query(DispatchFixAction).filter_by(order_id=failed.id, action="reschedule").count() == 1
    with pytest.raises(ValueError):
        fixes.apply(db, get_settings(), ctx, item_id="x", order_id=failed.id, action="delete", params={})
    alert.status = "resolved"  # leave the shared review DB's queue as we found it
    db.commit()


def test_margin_alert_on_committed_route(db: Session) -> None:
    d = _driver(db)
    o = _order(db, W, S)
    o.amount_cents = 50
    plans = FleetPlanService(matrix_fn=_road, position_fn=lambda _d: (43.65, -79.38))
    plan = plans.plan(db, actor="t", order_ids=[o.id], driver_ids=[d.id], time_limit_s=1)
    plans.commit(db, get_settings(), _ctx(db), plan["id"])
    fixes = ExceptionFixesService(recommend_fn=lambda _db, _oid: {"drivers": [], "best_driver_id": None})
    queue = all_exceptions(DispatchBoardService(), db, etas_fn=lambda _db: [], fixes=fixes)
    item = next(i for i in queue["items"] if i["id"] == f"margin:{o.id}")
    assert item["price_cents"] == 50 and item["cost_cents"] > 50 and item["margin_pct"] < 0
    assert item["fixes"][0]["action"] == "reroute"
