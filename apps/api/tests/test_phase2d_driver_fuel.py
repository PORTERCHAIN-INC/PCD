"""Phase 2d — sequence-aligned next stop + optimize fuel metrics."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from porterchain_driver.jobs import JobsService
from porterchain_driver.next_stop import NextStopResolver


def _stop(**kwargs):
    base = dict(
        stop_id="s1",
        order_id="o1",
        order_number="PC-1",
        tracking_number="TRK1",
        sequence=1,
        stop_type="pickup",
        status="assigned",
        address={"lat": 43.65, "lng": -79.38, "formatted": "A"},
    )
    base.update(kwargs)
    return SimpleNamespace(**base)


def test_next_stop_follows_sequence_waypoint_order() -> None:
    maps = MagicMock()
    maps.matrix_durations.return_value = ([[(120, 800)]], "valhalla")
    resolver = NextStopResolver(maps=maps)

    pickup = _stop(stop_id="o2-pickup", order_id="o2", sequence=1, stop_type="pickup")
    drop = _stop(
        stop_id="o1-dropoff",
        order_id="o1",
        sequence=2,
        stop_type="dropoff",
        address={"lat": 43.66, "lng": -79.39},
    )
    # Route list order would prefer pickup first; sequence says dropoff next.
    route = SimpleNamespace(stops=[pickup, drop], route_id="r1", status="active")

    with (
        patch(
            "porterchain_driver.stops.StopsService.assigned_route",
            return_value=route,
        ),
        patch(
            "porterchain_driver.sequence_store.read_sequence",
            return_value={
                "waypoints": [
                    {"order_id": "o1", "stop_type": "dropoff", "sequence": 1},
                    {"order_id": "o2", "stop_type": "pickup", "sequence": 2},
                ]
            },
        ),
        patch(
            "porterchain_api.driver_engine.last_known.read_last_known",
            return_value=SimpleNamespace(lat=43.64, lng=-79.37),
        ),
    ):
        out = resolver.resolve(MagicMock(), SimpleNamespace(id="driver-1"))

    assert out is not None
    assert out["order_id"] == "o1"
    assert out["stop_type"] == "dropoff"
    assert out["source"] and "fleetbase_sequence" in out["source"]
    assert out["distance_m"] == 800


def test_plan_from_run_adds_fuel_delta_vs_before() -> None:
    rec = {
        "run_id": "run-1",
        "status": "ready",
        "engine": "vroom",
        "assignments": [],
        "metrics": {"after_distance_km": 40.0},
    }
    jobs = {"route_metrics": {"distance_km": 50.0}}
    out = JobsService.plan_from_run(rec, jobs)
    assert out["metrics"]["before_distance_km"] == 50.0
    assert out["metrics"]["fuel_delta_cents"] > 0
    assert out["metrics"]["estimated_fuel_cents"] > 0
