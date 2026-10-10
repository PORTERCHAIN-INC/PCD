"""Operations scenario matrix: every real-world failure lands in Exceptions with a next step.

Shapes, FTL/LTL/3PL legs, short drops, scan gates and plan→commit→replan are covered in
test_dispatch_phase2/round3/round4; this file proves the exception side end to end.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from porterchain_api.admin_engine.dispatch_board_service import DispatchBoardService
from porterchain_api.admin_engine.exception_fixes_service import ExceptionFixesService
from porterchain_api.booking_models import OrderException
from tests.test_dispatch_phase2 import M, S, W, _driver, _order, all_exceptions

SCENARIOS = {  # exception type → first fix the dispatcher sees
    "VEHICLE_BREAKDOWN": "reassign",
    "DRIVER_TIMEOUT": "reassign",  # driver no-show on an offer
    "CUSTOMER_UNAVAILABLE": "reschedule",  # receiver absent
    "FAILED_DELIVERY": "reschedule",
    "PARCEL_DAMAGED": "contact",
    "PARCEL_LOST": "contact",
    "package_short_at_drop": "contact",
    "WRONG_ADDRESS": "contact",
}


def test_every_exception_has_a_first_fix(db: Session, monkeypatch) -> None:
    from porterchain_api.admin_engine import exception_fixes_service

    monkeypatch.setattr(exception_fixes_service, "MAX_RECOMMEND", 10_000)  # shared test DB: rank every row
    d = _driver(db)
    orders = {}
    for typ in SCENARIOS:
        o = _order(db, W, S if typ != "WRONG_ADDRESS" else M, state="DRIVER_ASSIGNED")
        db.add(OrderException(order_id=o.id, type=typ, reported_by_type="driver", reported_by_id=d.id))
        orders[o.id] = typ
    damaged = _order(db, W, S, state="DAMAGED")
    db.commit()

    best = {"driver_id": d.id, "name": d.full_name, "insertion_minutes": 4}
    fixes = ExceptionFixesService(recommend_fn=lambda _db, oid: {"best_driver_id": d.id, "drivers": [best]})
    items = all_exceptions(DispatchBoardService(), db, etas_fn=lambda _db: [], fixes=fixes)["items"]
    by_order = {i["order_id"]: i for i in items}
    for oid, typ in orders.items():
        got = by_order[oid].get("fixes") or []
        assert got and got[0]["action"] == SCENARIOS[typ], (typ, got)
    first = by_order[damaged.id]["fixes"][0]
    assert first["action"] == "contact" and "late" not in first["params"]["message"]


def test_queue_pages_and_never_hides_new_problems(db: Session) -> None:
    from datetime import UTC, datetime, timedelta

    d = _driver(db)
    old = datetime.now(UTC) - timedelta(days=2)
    mine = []
    for _ in range(205):  # more than the old 200-row cap, all older than the new problem
        o = _order(db, W, S, boxes=1, state="DRIVER_ASSIGNED")
        mine.append(o.id)
        db.add(OrderException(order_id=o.id, type="WRONG_ADDRESS", reported_by_type="driver",
                              reported_by_id=d.id, created_at=old))
    fresh = _order(db, W, S, boxes=1, state="DRIVER_ASSIGNED")
    db.add(OrderException(order_id=fresh.id, type="WRONG_ADDRESS", reported_by_type="driver", reported_by_id=d.id))
    db.commit()

    board = DispatchBoardService()
    noop = ExceptionFixesService(recommend_fn=lambda _db, _oid: {})
    first = board.exceptions_queue(db, etas_fn=lambda _db: [], fixes=noop, limit=50)
    assert first["total"] >= 206 and len(first["items"]) == 50
    assert all("fixes" in i for i in first["items"])
    items = all_exceptions(board, db, etas_fn=lambda _db: [], fixes=noop)["items"]
    assert len({i["id"] for i in items}) == first["total"]  # every row reachable, none capped
    rank = [i["order_id"] for i in items]
    ours = [rank.index(o) for o in mine]
    assert rank.index(fresh.id) < min(ours)  # newest of its severity comes first


def test_breakdown_rescue_moves_freight_scans_over_and_emails_only_on_slip(db: Session, monkeypatch) -> None:
    from porterchain_api.admin_engine.exception_fixes_service import rescue_service
    from porterchain_api.admin_engine.fleet_plan_service import FleetPlanService
    from porterchain_api.admin_engine.operations_service import AdminOperationsService
    from porterchain_api.booking_models import Order
    from porterchain_api.config import get_settings
    from porterchain_api.dispatch_engine.driver_route import DriverRouteService
    from porterchain_api.merchant_engine.scan_gate_service import ScanGateService
    from tests.test_dispatch_phase2 import _ctx, _road

    monkeypatch.setattr(AdminOperationsService, "_enqueue_driver_book_optimize", staticmethod(lambda *a, **k: None))
    broken, near = _driver(db), _driver(db)
    pos = {broken.id: (43.70, -79.40), near.id: (43.705, -79.40)}
    a, b = _order(db, W, S, boxes=3), _order(db, W, M, boxes=2)
    plans = FleetPlanService(matrix_fn=_road, position_fn=lambda d: pos.get(d, (43.65, -79.38)))
    plan = plans.plan(db, actor="t", order_ids=[a.id, b.id], driver_ids=[broken.id], time_limit_s=1)
    ctx = _ctx(db)
    plans.commit(db, get_settings(), ctx, plan["id"])
    gate = ScanGateService()
    for o in (a, b):  # broken van picked both up
        for p in o.packages:
            gate.scan_qr(db, o, p.tracking_suffix, phase="pickup")
        db.refresh(o)
        o.state = "IN_TRANSIT"
    db.add(OrderException(order_id=a.id, type="VEHICLE_BREAKDOWN", reported_by_type="driver", reported_by_id=broken.id))
    db.commit()

    item = {"kind": "exception", "type": "VEHICLE_BREAKDOWN", "state": "IN_TRANSIT", "driver_id": broken.id}
    from porterchain_api.dispatch_engine.exception_fixes import suggest
    assert suggest(item, plan_id=None, best_driver=None, next_slot=None)[0]["action"] == "rescue"  # one action

    def slow_road(points):  # every rescue van is 20+ min from the meet point → ETA slips → email
        m = _road(points)
        for row in m[1:]:
            row[0] += 20 * 60
        return m

    from porterchain_api.admin_engine import fleet_plan_service as fps

    monkeypatch.setattr(fps, "_valhalla", slow_road)
    monkeypatch.setattr(fps, "_position", lambda d: pos.get(d))
    out = ExceptionFixesService().apply(db, get_settings(), ctx, item_id="exc:x", order_id=a.id, action="rescue",
                                        params={"driver_id": broken.id})["result"]
    assert out["rescue_driver_id"] == near.id and out["boxes_to_scan"] == 5
    assert set(out["emailed"]) == {a.id, b.id}
    assert db.get(Order, a.id).assigned_driver_id == near.id

    view = DriverRouteService().view(db, near.id)["route"]
    first = view["stops"][0]
    assert first["kind"] == "pickup" and first["address"].startswith("Rescue handover")
    assert not DriverRouteService().view(db, broken.id)["route"]["stops"] or all(
        s["status"] == "done" for s in DriverRouteService().view(db, broken.id)["route"]["stops"])
    assert gate.scan_progress(db, db.get(Order, a.id), phase="pickup")["complete"] is False  # must scan over

    # A fast rescue (no slip) sends no email.
    c = _order(db, W, S, boxes=1, state="IN_TRANSIT")
    c.assigned_driver_id = near.id
    db.commit()
    fast = rescue_service()
    fast.matrix_fn, fast.position_fn = (lambda pts: [[0] * len(pts) for _ in pts]), (lambda d: (43.7, -79.4))
    spare = _driver(db)
    blind = rescue_service()
    blind.matrix_fn, blind.position_fn = fast.matrix_fn, (lambda d: (43.7, -79.4) if d == near.id else None)
    import pytest

    with pytest.raises(ValueError, match="no_rescue_vehicle_fits"):  # no GPS fix → never the rescue van
        blind.rescue(db, ctx, broken_driver_id=near.id, rescue_driver_id=spare.id)
    res = fast.rescue(db, ctx, broken_driver_id=near.id, rescue_driver_id=spare.id)
    assert res["emailed"] == [] and res["rescue_driver_id"] == spare.id
