"""One-van day solver: Valhalla seconds, pickup before dropoff, insertion fallback."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import patch

from porterchain_api.dispatch_engine.capacity import VehicleCapacity
from porterchain_api.dispatch_engine.day_plan import costing_for, toronto_window_seconds
from porterchain_api.dispatch_engine.sequencer import DayJob, DayStop, solve_day


def _stops(*ids: str, **extra: int) -> list[DayStop]:
    rows = []
    for index, stop_id in enumerate(ids):
        rows.append(DayStop(id=stop_id, lat=43.6 + index / 100, lng=-79.3, **extra))
    return rows


def _matrix(stop_count: int, fill: int = 60) -> list[list[int]]:
    size = stop_count + 1
    return [[0 if left == right else fill for right in range(size)] for left in range(size)]


def _solve(stops: list[DayStop], jobs: list[DayJob], **kwargs) -> object:
    return solve_day(
        stops=stops,
        jobs=jobs,
        matrix=kwargs.pop("matrix", _matrix(len(stops))),
        matrix_source=kwargs.pop("matrix_source", "valhalla"),
        time_limit_s=kwargs.pop("time_limit_s", 0),
        **kwargs,
    )


def test_pickup_before_dropoff_and_extra_between() -> None:
    stops = _stops("p", "x", "d")
    plan = _solve(stops, [DayJob(id="j", pickup_id="p", dropoff_id="d", extra_ids=("x",))])
    assert plan.label == "ortools"
    assert plan.waypoints.index("p") < plan.waypoints.index("x") < plan.waypoints.index("d")
    assert plan.unassigned == []


def test_service_minutes_are_not_the_road_cell() -> None:
    stops = _stops("p", "d", service_seconds=3600)
    matrix = _matrix(2, fill=120)
    plan = _solve(stops, [DayJob(id="j", pickup_id="p", dropoff_id="d")], matrix=matrix)
    assert plan.added_minutes["p"] == 2
    assert plan.added_minutes["d"] == 2


def test_non_valhalla_matrix_does_not_search() -> None:
    stops = _stops("p", "d")
    plan = _solve(
        stops,
        [DayJob(id="j", pickup_id="p", dropoff_id="d")],
        matrix_source="osrm",
        current_order=["d", "p"],
    )
    assert plan.label == "routing_down"
    assert plan.waypoints == ["d", "p"]


def test_capacity_skill_and_missing_coords() -> None:
    stops = [
        DayStop(id="p", lat=43.6, lng=-79.3),
        DayStop(id="d", lat=43.7, lng=-79.4),
        DayStop(id="np", lat=None, lng=-79.3),
        DayStop(id="nd", lat=43.7, lng=-79.4),
        DayStop(id="sp", lat=43.6, lng=-79.3),
        DayStop(id="sd", lat=43.7, lng=-79.4),
    ]
    plan = _solve(
        stops,
        [
            DayJob(id="heavy", pickup_id="p", dropoff_id="d", kg=11),
            DayJob(id="blind", pickup_id="np", dropoff_id="nd"),
            DayJob(id="wrong", pickup_id="sp", dropoff_id="sd", skill="box_truck"),
        ],
        capacity=VehicleCapacity(kg=10),
        vehicle_class="cargo_van",
    )
    reasons = {row["job_id"]: row["reason"] for row in plan.unassigned}
    assert reasons == {"heavy": "capacity", "blind": "no_coords", "wrong": "skill"}


def test_missing_capacity_is_not_applied() -> None:
    stops = _stops("p", "d")
    plan = _solve(stops, [DayJob(id="j", pickup_id="p", dropoff_id="d", parcels=500)])
    assert plan.unassigned == []
    assert plan.waypoints == ["p", "d"]


def test_time_window_leaves_the_late_job() -> None:
    stops = [
        DayStop(id="p", lat=43.6, lng=-79.3),
        DayStop(id="d", lat=43.7, lng=-79.4),
        DayStop(id="late_p", lat=43.8, lng=-79.5, window_end_s=5),
        DayStop(id="late_d", lat=43.9, lng=-79.6, window_end_s=5),
    ]
    plan = _solve(
        stops,
        [
            DayJob(id="ok", pickup_id="p", dropoff_id="d"),
            DayJob(id="late", pickup_id="late_p", dropoff_id="late_d"),
        ],
        matrix=_matrix(4, fill=100),
    )
    assert plan.waypoints == ["p", "d"]
    assert plan.unassigned == [{"job_id": "late", "reason": "time_window"}]


def test_locked_prefix_and_break() -> None:
    stops = _stops("done", "drop", "p", "d")
    locked = DayJob(id="gone", pickup_id="done", dropoff_id="drop", locked=True)
    fresh = DayJob(id="next", pickup_id="p", dropoff_id="d")
    plan = _solve(stops, [locked, fresh], current_order=["done", "drop", "d", "p"])
    assert plan.waypoints[:2] == ["done", "drop"]
    assert plan.waypoints.index("p") < plan.waypoints.index("d")

    resting = _solve(stops, [locked, fresh], on_break=True, current_order=["d", "p"])
    assert resting.label == "on_break"
    assert resting.waypoints == ["d", "p"]


def test_too_many_stops_keeps_the_list() -> None:
    ids = [f"s{i}" for i in range(26)]
    stops = _stops(*ids)
    plan = _solve(stops, [], current_order=ids)
    assert plan.label == "too_large"
    assert plan.waypoints == ids


def test_insertion_when_the_search_returns_nothing() -> None:
    stops = _stops("p", "d")
    with patch("porterchain_api.dispatch_engine.sequencer._ortools", return_value=None):
        plan = _solve(stops, [DayJob(id="j", pickup_id="p", dropoff_id="d")])
    assert plan.label == "insertion"
    assert plan.waypoints == ["p", "d"]


def test_picked_up_stop_stays_in_front() -> None:
    stops = _stops("p", "d", "p2", "d2")
    plan = _solve(
        stops,
        [
            DayJob(id="gone", pickup_id="p", dropoff_id="d", picked_up=True),
            DayJob(id="next", pickup_id="p2", dropoff_id="d2"),
        ],
    )
    assert plan.waypoints[0] == "p"
    assert plan.waypoints.index("p") < plan.waypoints.index("d")
    assert "p2" in plan.waypoints and "d2" in plan.waypoints
    same_day = datetime(2026, 10, 5, 18, 30, tzinfo=UTC)
    other_day = datetime(2026, 10, 6, 15, 0, tzinfo=UTC)
    toronto = same_day.astimezone(__import__("zoneinfo").ZoneInfo("America/Toronto"))
    assert toronto_window_seconds(same_day, day=toronto.date()) == toronto.hour * 3600 + toronto.minute * 60
    assert toronto_window_seconds(other_day, day=toronto.date()) is None
    assert costing_for("box_truck") == "truck"
    assert costing_for("cargo_van") == "auto"


def test_accept_draws_the_stored_order_and_does_not_search() -> None:
    from porterchain_api.dispatch_engine.day_plan import accept_line

    with (
        patch("porterchain_services.maps.service.MapsService.route_multi", return_value={"trip": {}}) as draw,
        patch("porterchain_api.dispatch_engine.sequencer.solve_day") as search,
    ):
        line = accept_line([(43.6, -79.3), (43.7, -79.4)], vehicle_class="cargo_van")
    assert line is not None
    assert line["polyline_encoding"] == "google"
    draw.assert_called_once()
    search.assert_not_called()
