"""Opt-in: 78-stop Toronto fixture on real self-hosted Valhalla + VROOM test containers (scripts/test-routing.sh up).
Skipped unless PCD_TEST_VALHALLA_URL / PCD_TEST_VROOM_URL are set. Never the live :8002/:5000 engines."""
from __future__ import annotations

import os

import pytest

from porterchain_api.batch_engine import vrp
from tests.test_vrp_routing import DEPOT, _fleet, _jobs

VAL = os.environ.get("PCD_TEST_VALHALLA_URL", "")
VRM = os.environ.get("PCD_TEST_VROOM_URL", "")
LIVE = (":8002", ":5000")


def _guard(url: str) -> None:
    if not url:
        pytest.skip("routing test containers not configured")
    assert not url.rstrip("/").endswith(LIVE), "refusing the live routing engines"


def test_valhalla_matrix_is_road_time():
    _guard(VAL)
    pts = [DEPOT, (43.6426, -79.3756)]
    t = vrp.valhalla_travel(pts, VAL, vtype="cargo_van")
    assert t is not None
    secs = t(pts[0], pts[1], 12 * 3600, "cargo_van")
    assert 600 < secs < 3600  # Scarborough -> 1 Yonge on roads: 10-60 min


def test_78_stops_builtin_on_valhalla():
    _guard(VAL)
    jobs = _jobs()
    out = vrp.solve_best(_fleet(type="cargo_van"), jobs, valhalla_url=VAL)
    served = sorted(p for r in out["routes"] for s in r["stops"] for p in s["parcels"])
    assert out["unassigned"] == [] and served == sorted(j.id for j in jobs)
    assert out["saved_s"] > 0


def test_78_stops_vroom_on_valhalla():
    _guard(VAL)
    _guard(VRM)
    jobs = _jobs()
    out = vrp.solve_best(_fleet(type="cargo_van"), jobs, vroom_url=VRM, valhalla_url=VAL)
    assert out["solver"] == "vroom", out.get("solver")
    assert out["unassigned"] == []
    stops = [s["job_id"] for r in out["routes"] for s in r["stops"]]
    assert len(stops) == len(set(stops)) and len(stops) == len(vrp.group_building(jobs))
    assert all(r["duration_s"] <= 9 * 3600 for r in out["routes"])
    assert out["total_s"] < out["naive_s"]


def test_with_matrix_offline():
    fleet = _fleet(n=1, type="cargo_van")
    jobs = _jobs()[:4]
    prob = vrp.with_matrix(vrp.vroom_problem(fleet, jobs), vrp.Travel({}), fleet)
    n = len(prob["matrices"]["truck"]["durations"])
    assert n == 5 and prob["vehicles"][0]["start_index"] == 0
    assert all("location" not in j and "location_index" in j for j in prob["jobs"])
