"""Dispatch Phase 2: stop shapes, multi-vehicle VRP, re-plan, legs, retention, explain."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from porterchain_api import crm_models, merchant_models, user_models  # noqa: F401 — FK targets
from porterchain_api.admin_engine.control_tower.service import ControlTowerService
from porterchain_api.admin_engine.fleet_plan_service import FleetPlanService
from porterchain_api.admin_engine.logistics_partners_service import (
    LogisticsPartnersService,
)
from porterchain_api.admin_models import AdminUser, Driver, Vehicle
from porterchain_api.booking_engine.numbers import (
    generate_order_number,
    generate_tracking_number,
)
from porterchain_api.booking_models import Order, Package
from porterchain_api.dispatch_engine import legs, plan_explain, retention, vrp
from porterchain_api.dispatch_engine.models import OrderLeg
from porterchain_api.dispatch_engine.stop_shapes import StopSpec, fsa, order_stops
from porterchain_api.driver_engine.retention_purge import purge
from porterchain_api.driver_models import DriverLocationPing, DriverStopMeta

pytestmark = pytest.mark.usefixtures("quiet_pool")

W = {"lat": 43.6467, "lng": -79.3832, "postal": "M5H 2N2", "formatted": "100 Wellington St W"}
S = {"lat": 43.7615, "lng": -79.4111, "postal": "M2N 5Y7", "formatted": "2 Sheppard Ave E"}
M = {"lat": 43.5933, "lng": -79.6426, "postal": "L5B 2C9", "formatted": "1 Square One Dr"}
B = {"lat": 43.7167, "lng": -79.7240, "postal": "L6T 4X3", "formatted": "40 Peel Centre Dr"}


def _road(points, kmh: float = 32.0):
    """Test-only stand-in for the Valhalla matrix (great-circle × 1.35 at city speed)."""
    import math

    out = []
    for a in points:
        row = []
        for b in points:
            dlat, dlng = math.radians(b[0] - a[0]), math.radians(b[1] - a[1])
            h = math.sin(dlat / 2) ** 2 + math.cos(math.radians(a[0])) * math.cos(math.radians(b[0])) * math.sin(dlng / 2) ** 2
            row.append(int(2 * 6371 * math.asin(math.sqrt(h)) * 1.35 / kmh * 3600))
        out.append(row)
    return out


def _o(pickup, dropoff, **kw):
    return SimpleNamespace(id=kw.pop("id", str(uuid4())), pickup=pickup, dropoff=dropoff,
                           order_type=kw.pop("order_type", "instant"), state=kw.pop("state", "DISPATCH_READY"),
                           compliance_metadata=kw.pop("meta", None))


# ---------------------------------------------------------------- shapes
def test_fsa() -> None:
    assert fsa("m5h 2n2") == "M5H" and fsa("12345") is None and fsa(None) is None


@pytest.mark.parametrize(
    ("pickup", "dropoff", "shape", "pairs"),
    [
        (W, S, "1→1", 1),
        (W, {"stops": [S, M, B]}, "1→N", 3),
        ({"stops": [S, M]}, W, "N→1", 2),
        ({"stops": [S, M]}, {"stops": [W, B]}, "N→N", 2),
    ],
)
def test_order_shapes(pickup, dropoff, shape, pairs) -> None:
    out = order_stops(_o(pickup, dropoff), boxes=6, kg=30)
    assert out.shape == shape and len(out.pairs) == pairs and out.skipped is None
    assert sum(s.boxes for s in out.stops if s.kind == "pickup") == 6
    assert all(s.fsa for s in out.stops)


def test_n_to_n_pickup_ref() -> None:
    out = order_stops(_o({"stops": [S, M]}, {"stops": [{**W, "pickup_ref": 1}, {**B, "pickup_ref": 0}]}))
    p_of = {d: p for p, d in out.pairs}
    by = {s.key: s for s in out.stops}
    assert [by[p_of[d]].fsa for d in p_of] == ["L5B", "M2N"]


def test_return_is_pickup_stop() -> None:
    out = order_stops(_o(S, W, meta={"is_return": True}))
    assert out.shape == "return 1→1"
    assert [s.kind for s in out.stops] == ["return_pickup", "return_drop"]


def test_missing_coords_skipped() -> None:
    assert order_stops(_o({"formatted": "x"}, W)).skipped == "address not geocoded"


# ---------------------------------------------------------------- VRP
def _spec(key, kind, lat, lng, boxes=1, kg=10.0, oid="o"):
    return StopSpec(key=key, order_id=oid, kind=kind, lat=lat, lng=lng, boxes=boxes, kg=kg, service_s=60)


def _problem(cap_boxes=10, n_pairs=4, boxes=4, vehicles=2):
    stops, pairs = [], []
    for i in range(n_pairs):
        p = _spec(f"p{i}", "pickup", 43.65 + i * 0.01, -79.38, boxes=boxes, oid=f"o{i}")
        d = _spec(f"d{i}", "drop", 43.70 + i * 0.01, -79.40, boxes=boxes, oid=f"o{i}")
        stops += [p, d]
        pairs.append((p.key, d.key))
    vs = [vrp.Vehicle(id=f"v{k}", driver_id=None, vehicle_class="van", cap_kg=900, cap_boxes=cap_boxes,
                      start=(43.65, -79.38)) for k in range(vehicles)]
    prob = vrp.Problem(stops=stops, pairs=pairs, vehicles=vs, matrix=[], time_limit_s=1)
    prob.matrix = _road(vrp.points(vs, stops))
    return prob


def test_ortools_multi_vehicle_respects_capacity_and_precedence() -> None:
    prob = _problem(cap_boxes=8, n_pairs=4, boxes=4, vehicles=3)
    routes = vrp.solve_ortools(prob)
    ev = vrp.evaluate(prob, routes)
    assert ev["feasible"], ev["violations"]
    assert ev["dropped"] == []
    assert all(r["peak_boxes"] <= 8 for r in ev["routes"])
    for keys in routes.values():
        for i in range(4):
            if f"d{i}" in keys:
                assert keys.index(f"p{i}") < keys.index(f"d{i}")


def test_ortools_drops_when_nothing_fits() -> None:
    prob = _problem(cap_boxes=3, n_pairs=2, boxes=4, vehicles=1)
    ev = vrp.evaluate(prob, vrp.solve_ortools(prob))
    assert len(ev["dropped"]) == 2


def test_capacity_overflow_keeps_the_rush_job() -> None:
    prob = _problem(cap_boxes=4, n_pairs=2, boxes=4, vehicles=1)
    prob.vehicles[0].max_route_s = 1200  # shift fits one of the two jobs
    assert vrp.evaluate(prob, vrp.solve_ortools(prob))["dropped"] == ["p1"]  # without rush the far job goes
    for st in prob.stops:
        st.rush = st.order_id == "o1"  # the farther job is the same-day rush
    assert vrp.evaluate(prob, vrp.solve_ortools(prob))["dropped"] == ["p0"]


def test_replan_keeps_loaded_freight_on_vehicle() -> None:
    prob = _problem(cap_boxes=20, n_pairs=3, boxes=2, vehicles=2)
    routes = {"v0": ["p0", "p1", "d0", "d1"], "v1": ["p2", "d2"]}
    re = vrp.replan_problem(prob, routes, done_keys={"p0", "d0", "p1"}, positions={"v0": (43.7, -79.4)})
    re.matrix = _road(vrp.points(re.vehicles, re.stops))
    v0 = re.vehicles[0]
    assert v0.must_deliver == ["d1"] and v0.onboard_boxes == 2 and v0.start == (43.7, -79.4)
    assert {s.key for s in re.stops} == {"d1", "p2", "d2"}
    out = vrp.solve_ortools(re)
    assert "d1" in out.get("v0", [])
    assert vrp.evaluate(re, out)["feasible"]


def test_better_prefers_feasible_then_fewer_drops_then_cost() -> None:
    a = {"feasible": True, "dropped": [], "cost_cents": 900}
    assert vrp.better(a, {"feasible": True, "dropped": ["x"], "cost_cents": 100})
    assert vrp.better({"feasible": True, "dropped": [], "cost_cents": 800}, a)
    assert not vrp.better({"feasible": False, "dropped": [], "cost_cents": 1}, a)


# ---------------------------------------------------------------- legs
PARTNERS = [
    {"id": "wh", "name": "Etobicoke DC", "kind": "warehouse", "lat": 43.65, "lng": -79.57, "active": True},
    {"id": "ltl1", "name": "LTL A", "kind": "ltl", "rate_per_kg_cents": 40, "min_charge_cents": 9000, "active": True},
    {"id": "ltl2", "name": "LTL B", "kind": "ltl", "rate_per_kg_cents": 30, "min_charge_cents": 12000, "active": True},
    {"id": "ftl", "name": "FTL", "kind": "ftl", "rate_per_kg_cents": 5, "min_charge_cents": 90000, "active": True},
    {"id": "3pl", "name": "Ottawa 3PL", "kind": "3pl", "fsa_coverage": ["K1", "K2"], "active": True},
]


def test_legs_local() -> None:
    out = legs.plan_legs({"pickup": (43.64, -79.38), "drop": (43.76, -79.41), "kg": 20}, PARTNERS)
    assert out["mode"] == "local" and [x["mode"] for x in out["legs"]] == ["local"]


def test_legs_ltl_via_warehouse_and_3pl() -> None:
    out = legs.plan_legs({"pickup": (43.64, -79.38), "drop": (45.42, -75.69), "kg": 200, "drop_fsa": "K1P"}, PARTNERS)
    assert [x["mode"] for x in out["legs"]] == ["local", "ltl", "3pl"]
    assert out["legs"][1]["partner_id"] == "ltl1"  # 9000 vs 12000 min charge
    assert out["legs"][0]["meta"]["stop_kind"] == "hub"


def test_legs_ftl_direct_and_missing_partner_note() -> None:
    out = legs.plan_legs({"pickup": (43.64, -79.38), "drop": (45.5, -73.56), "kg": 8000, "drop_fsa": "H2X"}, PARTNERS)
    assert [x["mode"] for x in out["legs"]] == ["ftl"]
    out2 = legs.plan_legs({"pickup": (43.64, -79.38), "drop": (45.5, -73.56), "kg": 8000}, [])
    assert any("FTL" in n for n in out2["notes"])


def test_legs_warehouse_hold() -> None:
    out = legs.plan_legs({"pickup": (43.64, -79.38), "drop": (43.76, -79.41), "kg": 20, "warehouse_hold": True}, PARTNERS)
    assert [x["mode"] for x in out["legs"]] == ["local", "warehouse", "local"]


# ---------------------------------------------------------------- explain
def test_summarize_and_rules_explain() -> None:
    prob = _problem(n_pairs=2, vehicles=2)
    ev = vrp.evaluate(prob, vrp.solve_ortools(prob)) | {"solver": "ortools"}
    summary = plan_explain.summarize(ev, {s.key: s for s in prob.stops})
    assert all(len(str(s["at"][0]).split(".")[1]) <= 2 for r in summary["routes"] for s in r["stops"])
    out = plan_explain.rules_explain(summary)
    assert out["suggest_only"] and out["explanation"]


# ---------------------------------------------------------------- retention
def test_normalize_retention_limits() -> None:
    assert retention.normalize_retention({}) == retention.default_retention()
    with pytest.raises(ValueError):
        retention.normalize_retention({"gps_days": 1})


def all_exceptions(board, db, **kw) -> dict:
    """Every page of the Exceptions queue, merged (the queue itself is paged)."""
    items, offset = [], 0
    while True:
        out = board.exceptions_queue(db, offset=offset, limit=200, **kw)
        items += out["items"]
        offset += 200
        if offset >= out["total"]:
            return {**out, "items": items}


def _driver(db: Session, cls: str = "van") -> Driver:
    s = uuid4().hex[:8]
    d = Driver(email=f"p2-{s}@dispatch.test", full_name=f"P2 {s}", status="APPROVED", clerk_user_id=f"clerk_p2_{s}",
               is_online=True, license_verified=True, insurance_verified=True, background_check_status="cleared")
    db.add(d)
    db.flush()
    db.add(Vehicle(driver_id=d.id, vehicle_class=cls, plate_number=f"P{s[:6]}", is_active=True))
    db.flush()
    return d


def _order(db: Session, pickup, dropoff, boxes=2, **kw) -> Order:
    o = Order(id=str(uuid4()), order_number=generate_order_number(), tracking_number=generate_tracking_number(),
              state=kw.pop("state", "DISPATCH_READY"), amount_cents=4500, currency="cad", pickup=pickup,
              dropoff=dropoff, scheduled_at=datetime.now(UTC) + timedelta(hours=1), **kw)
    db.add(o)
    db.flush()
    for i in range(boxes):
        db.add(Package(order_id=o.id, parcel_index=i + 1, total_parcels=boxes, tracking_suffix=f"{o.tracking_number}-{i}",
                       weight_kg=5, dimensions=None))
    db.flush()
    return o


def test_retention_purge(db: Session) -> None:
    d = _driver(db)
    old = datetime.now(UTC) - timedelta(days=40)
    db.add(DriverLocationPing(driver_id=d.id, lat=1, lng=1, created_at=old))
    db.add(DriverLocationPing(driver_id=d.id, lat=1, lng=1))
    o = _order(db, W, S, state="DELIVERED")
    o.updated_at = datetime.now(UTC) - timedelta(days=400)
    db.add(DriverStopMeta(order_id=o.id, driver_id=d.id, meta={"proofs": [{"type": "photo", "value": "s3://x"}]}))
    db.flush()
    policy = retention.default_retention()
    dry = purge(db, policy, dry_run=True)
    assert dry["gps_pings"] >= 1 and dry["pod_refs"] >= 1
    purge(db, policy, dry_run=False)
    assert db.query(DriverLocationPing).filter(DriverLocationPing.driver_id == d.id).count() == 1
    meta = db.query(DriverStopMeta).filter(DriverStopMeta.order_id == o.id).one().meta
    assert meta["proofs"][0]["value"] == "redacted" and meta["proofs"][0]["type"] == "photo"


# ---------------------------------------------------------------- service
def _ctx(db: Session):
    a = AdminUser(email=f"p2-{uuid4().hex[:6]}@dispatch.test", role="admin", is_active=True)
    db.add(a)
    db.flush()
    return SimpleNamespace(user=a, role=SimpleNamespace(value="admin"))


def test_plan_commit_explain_and_replan(db: Session, monkeypatch) -> None:
    d1, d2 = _driver(db), _driver(db, "sedan")
    o1 = _order(db, W, {"stops": [S, M]}, boxes=4)
    o2 = _order(db, M, B, boxes=2)
    o3 = _order(db, S, W, boxes=1, compliance_metadata={"is_return": True})
    svc = FleetPlanService(matrix_fn=_road, position_fn=lambda _d: (43.65, -79.38))
    out = svc.plan(db, actor="t", order_ids=[o1.id, o2.id, o3.id], driver_ids=[d1.id, d2.id], time_limit_s=1)
    assert out["status"] == "draft" and out["solver"] == "ortools"
    assert out["summary"]["shapes"] == {"1→N": 1, "1→1": 1, "return 1→1": 1}
    assert out["summary"]["dropped"] == [] and out["summary"]["matrix"] == "valhalla"
    kinds = {s["kind"] for r in out["routes"] for s in r["stops"]}
    assert {"pickup", "drop", "return_pickup", "return_drop"} <= kinds
    assert db.get(Order, o1.id).assigned_driver_id is None  # draft never assigns

    ex = svc.explain(db, out["id"])
    assert ex["source"] == "rules" and ex["suggest_only"]

    from porterchain_api.admin_engine.operations_service import AdminOperationsService

    monkeypatch.setattr(AdminOperationsService, "_enqueue_driver_book_optimize", staticmethod(lambda *a, **k: None))
    from porterchain_api.config import get_settings

    done = svc.commit(db, get_settings(), _ctx(db), out["id"])
    assert done["status"] == "committed" and done["summary"]["commit"]["assigned"] == 3
    assert db.get(Order, o1.id).assigned_driver_id in {d1.id, d2.id}

    o1_row = db.get(Order, o1.id)
    o1_row.state = "PICKED_UP"
    db.flush()
    re = svc.replan(db, out["id"], actor="t")
    assert re["version"] == 2 and re["parent_id"] == out["id"] and re["summary"]["kind"] == "replan"
    o1_driver = o1_row.assigned_driver_id
    for r in re["routes"]:
        if any(s["order_id"] == o1.id for s in r["stops"]):
            assert r["driver_id"] == o1_driver
            assert all(s["kind"] != "pickup" for s in r["stops"] if s["order_id"] == o1.id)


def test_partner_and_legs_saved(db: Session) -> None:
    ctx = _ctx(db)
    svc = LogisticsPartnersService()
    with pytest.raises(ValueError):
        svc.upsert(db, ctx, {"name": "x", "kind": "warehouse"})
    wh = svc.upsert(db, ctx, {"name": f"DC {uuid4().hex[:4]}", "kind": "warehouse", "lat": 43.65, "lng": -79.57})
    assert wh["kind"] == "warehouse"
    o = _order(db, W, S, compliance_metadata={"warehouse_hold": True})
    out = svc.plan_legs(db, ctx, o.id, save=True)
    assert out["mode"] == "warehouse" and len(out["current"]) == 3
    assert db.query(OrderLeg).filter(OrderLeg.order_id == o.id).count() == 3
    # The fleet plan sends the van to the hub, not the customer.
    hub = FleetPlanService()._hub_override(db, o)
    assert hub.dropoff["kind"] == "hub"


def test_board_excludes_sandbox(db: Session) -> None:
    o = _order(db, W, S, is_sandbox=True)
    cols = ControlTowerService().board(db)
    assert all(c["id"] != o.id for col in cols for c in col["orders"])


def test_plan_refuses_without_road_router(db: Session) -> None:
    d1 = _driver(db)
    o = _order(db, W, S)
    svc = FleetPlanService(matrix_fn=lambda pts: None, position_fn=lambda _d: (43.65, -79.38))
    with pytest.raises(ValueError, match="road_router_unavailable"):
        svc.plan(db, actor="t", order_ids=[o.id], driver_ids=[d1.id], time_limit_s=1)
