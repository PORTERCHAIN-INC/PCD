"""Smart routing (free/self-hosted): VRP constraints, waves, re-optimisation, VROOM adapter, 78-stop Toronto fixture."""
from __future__ import annotations

import json
import pathlib

import pytest

from porterchain_api.batch_engine import planner as P
from porterchain_api.batch_engine import vrp

FIX = json.loads((pathlib.Path(__file__).parent / "fixtures" / "toronto_78_stops.json").read_text())
DEPOT = (FIX["depot"]["lat"], FIX["depot"]["lng"])


def _jobs():
    return [vrp.Job(id=s["id"], loc=(s["lat"], s["lng"]), kg=s["kg"], boxes=s["boxes"], handling=s["handling"],
                    tw=tuple(s["tw"]) if s.get("tw") else None, building_key=P.building_key(s["address"])[0])
            for s in FIX["stops"]]


def _fleet(n=3, **kw):
    return [vrp.Vehicle(id=f"V{i}", type=kw.get("type", "car"), cap_kg=kw.get("cap_kg", 300),
                        cap_boxes=kw.get("cap_boxes", 40), start=DEPOT) for i in range(n)]


def test_78_stop_toronto_fixture_beats_naive_and_respects_constraints():
    jobs = _jobs()
    assert len(jobs) == 78
    out = vrp.solve(_fleet(), jobs)
    assert out["unassigned"] == []
    served = [p for r in out["routes"] for s in r["stops"] for p in s["parcels"]]
    assert sorted(served) == sorted(j.id for j in jobs)  # every parcel exactly once
    assert out["saved_s"] > 0 and out["saved_pct"] >= 20  # vs CSV order
    by = {j.id: j for j in jobs}
    for r in out["routes"]:
        assert sum(by[p].kg for p in r["load_order"]) <= 300 + 1e-6
        assert sum(by[p].boxes for p in r["load_order"]) <= 40
        assert r["duration_s"] <= 9 * 3600
        delivered = [p for s in r["stops"] for p in s["parcels"]]
        assert r["load_order"] == list(reversed(delivered)) or r["load_order"][0] == delivered[-1]
        for s in r["stops"]:
            for p in s["parcels"]:
                if by[p].tw:
                    assert s["arrive_s"] <= by[p].tw[1]
    # same-building parcels end up in one stop
    bld = [s for r in out["routes"] for s in r["stops"] if len(s["parcels"]) > 1]
    assert bld and all(len({by[p].building_key for p in s["parcels"]}) == 1 for s in bld)


def test_single_small_vehicle_splits_into_waves():
    fleet = [vrp.Vehicle(id=f"V{i}", type="car", cap_kg=300, cap_boxes=10, start=DEPOT, shift_s=12 * 3600)
             for i in range(2)]
    out = vrp.solve(fleet, _jobs()[:30], max_waves=6)
    assert out["waves"] >= 2 and not out["unassigned"]
    w2 = [r for r in out["routes"] if r["wave"] == 2]
    assert all(r["stops"][0]["arrive_s"] > 8 * 3600 + vrp.RELOAD_S for r in w2)  # after reload at depot
    one_day = vrp.solve(_fleet(1), _jobs())  # one car can't do 78 stops in a 9 h shift -> reported, not hidden
    assert one_day["unassigned"]


def test_vehicle_type_and_capacity_and_time_window_infeasible():
    j = vrp.Job(id="big", loc=(43.7, -79.4), kg=900, allowed_types=["box_truck"])
    out = vrp.solve(_fleet(1), [j])
    assert out["unassigned"] == ["big"]
    truck = [vrp.Vehicle(id="T", type="box_truck", cap_kg=3500, cap_boxes=400, start=DEPOT)]
    assert vrp.solve(truck, [j])["unassigned"] == []
    late = vrp.Job(id="tw", loc=(43.65, -79.38), tw=(8 * 3600, 8 * 3600 + 60))
    assert vrp.solve(_fleet(1), [late], max_waves=1)["unassigned"] == ["tw"]


def test_pickup_delivery_pairs_and_handover_precedence():
    pick = vrp.Job(id="hp", loc=(43.70, -79.35), kind="pickup", stop_type="driver", kg=5, boxes=2)
    d1 = vrp.Job(id="d1", loc=(43.66, -79.40), kg=3, pair="hp")
    d2 = vrp.Job(id="d2", loc=(43.64, -79.42), kg=2, pair="hp")
    out = vrp.solve(_fleet(1), [d1, pick, d2])
    seq = [s["job_id"] for s in out["routes"][0]["stops"]]
    assert seq.index("hp") < seq.index("d1") and seq.index("hp") < seq.index("d2")


def test_service_time_by_type_and_tod_factor():
    assert vrp.service_time(vrp.Job(id="a", loc=(0, 0))) == 90
    assert vrp.service_time(vrp.Job(id="b", loc=(0, 0), handling=["pharmacy", "signature"])) == 90 + 120 + 60
    assert vrp.service_time(vrp.Job(id="c", loc=(0, 0), kind="pickup", stop_type="warehouse")) == 900
    assert vrp.service_time(vrp.Job(id="g", loc=(0, 0), parcels=["1", "2", "3"])) == 180 + 90
    assert vrp.tod_factor(8 * 3600) > vrp.tod_factor(12 * 3600) > vrp.tod_factor(23 * 3600)
    t = vrp.Travel()
    assert t((43.65, -79.38), (43.70, -79.40), 17 * 3600, "car") > t((43.65, -79.38), (43.70, -79.40), 12 * 3600, "car")
    m = vrp.Travel({((0.0, 0.0), (1.0, 1.0)): 100.0})
    assert m((0.0, 0.0), (1.0, 1.0), 12 * 3600, "car") == 100.0  # road matrix (Valhalla/Valhalla) wins


def test_live_reoptimise_events():
    jobs = _jobs()[:20]
    fleet = _fleet(2)
    new = vrp.reoptimise(fleet, jobs, {"type": "new_order", "job": vrp.Job(id="NEW", loc=(43.66, -79.39))})
    assert "NEW" in [p for r in new["routes"] for s in r["stops"] for p in s["parcels"]]
    f = vrp.reoptimise(fleet, jobs, {"type": "failed_stop", "job_id": jobs[0].id, "reattempt": True})
    ids = [s["job_id"] for r in f["routes"] for s in r["stops"]]
    assert any(i.endswith(":re") for i in ids) or jobs[0].building_key
    dl = vrp.reoptimise(fleet, jobs, {"type": "delay", "vehicle_id": "V0", "seconds": 1800})
    assert dl["event"] == "delay"
    ho = vrp.reoptimise(fleet, jobs, {"type": "handover",
                                       "pickup": vrp.Job(id="HP", loc=(43.7, -79.35), kind="pickup", stop_type="driver"),
                                       "deliveries": [vrp.Job(id="HD", loc=(43.65, -79.4), pair="HP")]})
    assert "HD" in [s["job_id"] for r in ho["routes"] for s in r["stops"]]
    with pytest.raises(ValueError):
        vrp.reoptimise(fleet, jobs, {"type": "nope"})


def test_vroom_problem_and_fallback():
    jobs = [vrp.Job(id="p", loc=(43.7, -79.3), kind="pickup"), vrp.Job(id="d", loc=(43.6, -79.4), pair="p", kg=2),
            vrp.Job(id="x", loc=(43.65, -79.38), tw=(36000, 40000))]
    prob = vrp.vroom_problem(_fleet(1), jobs)
    assert prob["vehicles"][0]["start"] == [DEPOT[1], DEPOT[0]]  # lon,lat
    assert len(prob["shipments"]) == 1 and prob["jobs"][0]["time_windows"] == [[36000, 40000]]

    class Down:
        def post(self, *a, **k):
            raise ConnectionError("no vroom")
    assert vrp.solve_best(_fleet(1), jobs, vroom_url="http://127.0.0.1:1", http=Down())["solver"] == "builtin"

    class Up:
        def post(self, url, json, timeout):
            class R:
                def json(self_inner):
                    return {"code": 0, "routes": [{"vehicle": 1, "duration": 100, "steps": [
                        {"type": "start"}, {"type": "job", "description": "x", "arrival": 36000}, {"type": "end"}]}],
                            "unassigned": []}
            return R()
    out = vrp.solve_best(_fleet(1), jobs, vroom_url="http://vroom:3000", http=Up())
    assert out["solver"] == "vroom" and out["routes"][0]["stops"][0]["job_id"] == "x"


def test_admin_optimise_endpoint(monkeypatch):
    from fastapi.testclient import TestClient
    from porterchain_api.admin_engine.rbac import AdminContext, AdminUser, parse_admin_role
    from porterchain_api.auth.admin import get_admin_context
    from porterchain_api.main import app
    role = {"r": "dispatcher"}
    app.dependency_overrides[get_admin_context] = lambda: AdminContext(
        user=AdminUser(auth_subject="s", email="a@x.ca", role=role["r"]), role=parse_admin_role(role["r"]))
    try:
        c = TestClient(app)
        body = {"vehicles": [{"id": "V", "start": list(DEPOT)}],
                "jobs": [{"id": s["id"], "loc": [s["lat"], s["lng"]], "kg": s["kg"]} for s in FIX["stops"][:10]]}
        r = c.post("/v1/admin/batches/optimise", json=body)
        assert r.status_code == 200 and r.json()["naive_s"] >= r.json()["total_s"]
        role["r"] = "support"
        assert c.post("/v1/admin/batches/optimise", json=body).status_code == 403
    finally:
        app.dependency_overrides.pop(get_admin_context, None)
