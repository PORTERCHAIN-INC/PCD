"""Dispatch round 3: stop check-ins, POD files + retention, partner booking, end-to-end day."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from porterchain_api import crm_models, merchant_models, user_models  # noqa: F401 — FK targets
from porterchain_api.admin_engine.dispatch_board_service import DispatchBoardService
from porterchain_api.admin_engine.fleet_plan_service import FleetPlanService
from porterchain_api.admin_engine.logistics_partners_service import LogisticsPartnersService
from porterchain_api.booking_models import Order
from porterchain_api.dispatch_engine import driver_route, retention
from porterchain_api.dispatch_engine.driver_route import DriverRouteService
from porterchain_api.dispatch_engine.models import DispatchStopEvent, OrderLeg
from porterchain_api.driver_engine import pod_store
from porterchain_api.driver_engine.retention_purge import purge
from porterchain_api.driver_models import DriverStopMeta
from tests.test_dispatch_phase2 import B, M, S, W, _ctx, _driver, _order, _road

pytestmark = pytest.mark.usefixtures("quiet_pool")

PHOTO = "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwg"


@pytest.fixture(autouse=True)
def _pod_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("POD_MEDIA_DIR", str(tmp_path / "pod"))
    from porterchain_api.admin_engine.operations_service import AdminOperationsService

    monkeypatch.setattr(AdminOperationsService, "_enqueue_driver_book_optimize", staticmethod(lambda *a, **k: None))


# ---------------------------------------------------------------- pure rules
def test_group_and_status_rules() -> None:
    stops = [{"key": "o:p0:0", "order_id": "o", "kind": "pickup"}, {"key": "o:p0:1", "order_id": "o", "kind": "pickup"},
             {"key": "o:d0:0", "order_id": "o", "kind": "drop"}, {"key": "o:d1:1", "order_id": "o", "kind": "drop"}]
    g = driver_route.group(stops)
    assert [x["keys"] for x in g] == [["o:p0:0", "o:p0:1"], ["o:d0:0"], ["o:d1:1"]]
    assert driver_route.stop_status("pickup", {"arrived"}) == "arrived"
    assert driver_route.stop_status("drop", {"arrived", "delivered"}) == "done"
    assert driver_route.allowed("pickup", "picked_up", "pending")
    assert not driver_route.allowed("pickup", "delivered", "arrived")
    assert not driver_route.allowed("drop", "arrived", "arrived")
    assert not driver_route.allowed("drop", "delivered", "done")


def test_pod_store_roundtrip() -> None:
    oid = str(uuid4())
    ref = pod_store.save_data_url(oid, PHOTO)
    assert ref.startswith("pod://" + oid) and pod_store.size(ref) > 0
    assert pod_store.delete(ref) and not pod_store.delete(ref)
    with pytest.raises(ValueError):
        pod_store.save_data_url(oid, "data:text/html;base64,PGI+")
    assert not pod_store.delete("pod://../../etc/passwd")


def test_retention_deletes_pod_files_and_dry_run_keeps_them(db: Session) -> None:
    d = _driver(db)
    o = _order(db, W, S, state="DELIVERED")
    o.updated_at = datetime.now(UTC) - timedelta(days=400)
    ref = pod_store.save_data_url(o.id, PHOTO)
    db.add(DriverStopMeta(order_id=o.id, driver_id=d.id, meta={"proofs": [{"type": "photo", "value": ref}]}))
    db.flush()
    policy = retention.default_retention()
    dry = purge(db, policy, dry_run=True)
    assert dry["pod_files"] >= 1 and dry["pod_file_bytes"] > 0 and dry["pod_files_deleted"] == 0
    assert pod_store.size(ref) > 0  # dry run touches nothing
    real = purge(db, policy, dry_run=False)
    assert real["pod_files_deleted"] >= 1 and pod_store.size(ref) == 0
    meta = db.query(DriverStopMeta).filter(DriverStopMeta.order_id == o.id).one().meta
    assert meta["proofs"][0]["value"] == "redacted"


# ---------------------------------------------------------------- partner booking
def test_partner_booking_workflow(db: Session) -> None:
    ctx = _ctx(db)
    svc = LogisticsPartnersService()
    with pytest.raises(ValueError):
        svc.upsert(db, ctx, {"name": "x", "kind": "3pl", "contact_email": "nope"})
    p = svc.upsert(db, ctx, {"name": f"3PL {uuid4().hex[:4]}", "kind": "3pl", "fsa_coverage": ["L6T"],
                             "contact_email": "ops@partner.test"})
    o = _order(db, W, B)
    leg = OrderLeg(order_id=o.id, seq=1, mode="3pl", partner_id=p["id"], from_label="Toronto", to_label="Brampton",
                   est_cost_cents=4200, status="planned")
    db.add(leg)
    db.flush()
    pdf, name = svc.job_sheet_pdf(db, leg.id)
    assert pdf.startswith(b"%PDF") and name.endswith(".pdf")
    draft = svc.draft_request(db, ctx, leg.id)
    assert draft["to"] == "ops@partner.test" and "not sent" in draft["status"] and o.order_number in draft["subject"]
    with pytest.raises(ValueError):
        svc.set_leg_status(db, ctx, leg.id, "delivered")
    for st in ("requested", "accepted", "picked_up", "delivered"):
        out = svc.set_leg_status(db, ctx, leg.id, st, note=f"{st} by phone")
    assert out["status"] == "delivered" and out["next"] == [] and len(out["history"]) == 4
    assert any(x["id"] == leg.id for x in svc.partner_legs(db, status="delivered"))


# ---------------------------------------------------------------- end to end
def test_dispatch_day_end_to_end(db: Session) -> None:
    """Every shape → plan → commit → driver check-ins → delivered → metrics move."""
    d1, d2 = _driver(db), _driver(db)
    shapes = [
        _order(db, W, S, boxes=1),                                   # 1→1
        _order(db, W, {"stops": [S, M]}, boxes=2),                   # 1→N
        _order(db, {"stops": [S, M]}, W, boxes=2),                   # N→1
        _order(db, {"stops": [S, M]}, {"stops": [W, B]}, boxes=2),   # N→N
        _order(db, S, W, boxes=1, compliance_metadata={"is_return": True}),  # return
    ]
    ids = [o.id for o in shapes]
    board = DispatchBoardService()
    before = board.metrics(db, days=1)

    plans = FleetPlanService(matrix_fn=_road, position_fn=lambda _d: (43.65, -79.38), cuopt_fn=lambda p: {})
    plan = plans.plan(db, actor="t", order_ids=ids, driver_ids=[d1.id, d2.id], time_limit_s=1)
    assert plan["summary"]["dropped"] == []
    assert set(plan["summary"]["shapes"]) == {"1→1", "1→N", "N→1", "N→N", "return 1→1"}
    from porterchain_api.config import get_settings

    plans.commit(db, get_settings(), _ctx(db), plan["id"])

    rs = DriverRouteService()
    drove = 0
    for drv in (d1, d2):
        view = rs.view(db, drv.id)["route"]
        if view is None:
            continue
        # One-tap "next stop" loop: arrive → picked up / delivered until the route is done.
        while view["next_index"] is not None:
            stop = view["stops"][view["next_index"]]
            rs.check_in(db, drv, keys=stop["keys"], event="arrived", lat=43.65, lng=-79.38, accuracy_m=8)
            final = "picked_up" if stop["kind"] in driver_route.PICKUP_KINDS else "delivered"
            if final == "delivered" and stop["needs_pod"]:
                if not pod_store.has_photo(db, stop["order_id"]):
                    with pytest.raises(PermissionError):  # no photo, no delivered
                        rs.check_in(db, drv, keys=stop["keys"], event=final)
                out = rs.check_in(db, drv, keys=stop["keys"], event=final, lat=43.65, lng=-79.38, pod_photo=PHOTO)
            else:
                out = rs.check_in(db, drv, keys=stop["keys"], event=final, lat=43.65, lng=-79.38)
            view = out["route"]
            drove += 1
        assert view["done"] == view["total"]
    assert drove >= 10
    assert {db.get(Order, i).state for i in ids} == {"DELIVERED"}
    assert db.query(DispatchStopEvent).filter(DispatchStopEvent.order_id.in_(ids), DispatchStopEvent.lat.isnot(None)).count() >= drove
    after = board.metrics(db, days=1)
    assert after["delivered"] >= before["delivered"] + 5

    # Re-plan sees the check-ins: nothing left to route for these orders.
    re = plans.replan(db, plan["id"], actor="t")
    assert not any(s["order_id"] in ids for r in re["routes"] for s in r["stops"])


def test_checkin_guards(db: Session) -> None:
    d, other = _driver(db), _driver(db)
    o = _order(db, W, S)
    plans = FleetPlanService(matrix_fn=_road, position_fn=lambda _d: (43.65, -79.38), cuopt_fn=lambda p: {})
    plan = plans.plan(db, actor="t", order_ids=[o.id], driver_ids=[d.id], time_limit_s=1)
    from porterchain_api.config import get_settings

    plans.commit(db, get_settings(), _ctx(db), plan["id"])
    rs = DriverRouteService()
    with pytest.raises(LookupError):
        rs.check_in(db, other, keys=["x"], event="arrived")
    stop = rs.view(db, d.id)["route"]["stops"][0]
    with pytest.raises(ValueError):
        rs.check_in(db, d, keys=stop["keys"], event="delivered")
    with pytest.raises(LookupError):
        rs.check_in(db, d, keys=["nope"], event="arrived")
    out = rs.check_in(db, d, keys=stop["keys"], event="failed", note="closed")
    assert out["order_state"] in {"FAILED", "DRIVER_ASSIGNED"}
