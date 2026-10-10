"""Phase 4 — interleaved Fleetbase waypoint sequence + next-stop policy."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from porterchain_driver.next_stop import NextStopResolver
from porterchain_driver.sequence_store import waypoints_from_assignments
from porterchain_driver.stops import StopsService


def test_accept_assignment_enqueues_driver_optimize() -> None:
    from porterchain_driver.availability import AvailabilityService

    db = MagicMock()
    driver = SimpleNamespace(id="drv-1")
    order = SimpleNamespace(
        id="ord-1",
        assigned_driver_id="drv-1",
        fleetbase_order_id=None,
        state="DRIVER_ACCEPTED",
    )
    db.query.return_value.filter.return_value.first.return_value = order
    with (
        patch(
            "porterchain_api.booking_engine.order_transitions.transition_order_state",
            return_value=order,
        ),
        patch("porterchain_driver.jobs.JobsService.optimize_route") as opt,
    ):
        out = AvailabilityService().accept_assignment(db, driver, "ord-1")
    assert out["order_id"] == "ord-1"
    opt.assert_called_once()


def test_execute_queued_run_applies_sequence_for_pc_driver() -> None:
    from porterchain_api.admin_engine.orchestrator_ops_service import OrchestratorOpsService
    from porterchain_api.dispatch_engine.optimize_run_store import STATUS_PENDING, STATUS_READY

    pending = {
        "run_id": "run-1",
        "status": STATUS_PENDING,
        "pc_driver_id": "drv-1",
        "order_ids": ["ord-1"],
        "mode": "optimize_routes",
        "engine": "porterchain",
        "vehicle_ids": ["veh-1"],
        "driver_ids": ["drv-1"],
    }
    ready_result = {
        "ok": True,
        "status": STATUS_READY,
        "pc_driver_id": "drv-1",
        "apply_on_ready": True,
        "assignments": [
            {
                "porterchain_order_id": "ord-1",
                "order_id": "ord-1",
                "sequence": 1,
                "stops": [{"type": "pickup"}, {"type": "delivery"}],
            }
        ],
        "metrics": {},
    }
    with (
        patch(
            "porterchain_api.admin_engine.orchestrator_ops_service.read_optimize_run",
            return_value=pending,
        ),
        patch(
            "porterchain_api.dispatch_engine.day_plan.finish_porterchain_run",
            return_value=ready_result,
        ),
        patch("porterchain_driver.sequence_store.apply_run_to_driver") as apply,
        patch("porterchain_api.dispatch_engine.optimize_events.emit_ready"),
        patch("porterchain_api.dispatch_engine.optimize_events.emit_applied"),
    ):
        out = OrchestratorOpsService().execute_queued_run(MagicMock(), "run-1")
    assert out["status"] == STATUS_READY
    apply.assert_called_once()
    assert apply.call_args.args[0] == "drv-1"


def test_waypoints_from_nested_fleetbase_stops_interleave() -> None:
    assignments = [
        {
            "porterchain_order_id": "ord-1",
            "sequence": 1,
            "stops": [{"type": "pickup"}, {"type": "delivery"}],
        },
        {
            "porterchain_order_id": "ord-2",
            "sequence": 2,
            "stops": [{"type": "pickup"}, {"type": "dropoff"}],
        },
    ]
    interleaved = [
        {
            "porterchain_order_id": "ord-1",
            "sequence": 1,
            "stops": [{"type": "pickup"}],
        },
        {
            "porterchain_order_id": "ord-2",
            "sequence": 2,
            "stops": [{"type": "pickup"}],
        },
        {
            "porterchain_order_id": "ord-1",
            "sequence": 3,
            "stops": [{"type": "delivery"}],
        },
        {
            "porterchain_order_id": "ord-2",
            "sequence": 4,
            "stops": [{"type": "delivery"}],
        },
    ]
    wps = waypoints_from_assignments(interleaved)
    assert [(w["order_id"], w["stop_type"]) for w in wps] == [
        ("ord-1", "pickup"),
        ("ord-2", "pickup"),
        ("ord-1", "dropoff"),
        ("ord-2", "dropoff"),
    ]
    assert len(waypoints_from_assignments(assignments)) == 4


def test_stops_for_orders_applies_interleaved_sequence() -> None:
    o1 = SimpleNamespace(
        id="ord-1",
        state="DRIVER_ASSIGNED",
        pickup={"lat": 1},
        dropoff={"lat": 2},
        scheduled_at=None,
        tracking_number="T1",
        order_number="N1",
        special_instructions=None,
    )
    o2 = SimpleNamespace(
        id="ord-2",
        state="DRIVER_ASSIGNED",
        pickup={"lat": 3},
        dropoff={"lat": 4},
        scheduled_at=None,
        tracking_number="T2",
        order_number="N2",
        special_instructions=None,
    )
    plan = {
        "run_id": "run-1",
        "waypoints": [
            {"sequence": 0, "order_id": "ord-1", "stop_type": "pickup"},
            {"sequence": 1, "order_id": "ord-2", "stop_type": "pickup"},
            {"sequence": 2, "order_id": "ord-1", "stop_type": "dropoff"},
            {"sequence": 3, "order_id": "ord-2", "stop_type": "dropoff"},
        ],
    }
    with patch("porterchain_driver.sequence_store.read_sequence", return_value=plan):
        stops = StopsService()._stops_for_orders([o1, o2], driver_id="drv-1")
    assert [s.stop_id for s in stops] == [
        "ord-1-pickup",
        "ord-2-pickup",
        "ord-1-dropoff",
        "ord-2-dropoff",
    ]
    assert [s.sequence for s in stops] == [0, 1, 2, 3]
    # Dropoffs still locked until pickup
    assert stops[2].status == "locked"
    assert stops[3].status == "locked"


def test_next_stop_follows_day_plan_when_applied() -> None:
    near = SimpleNamespace(
        stop_id="ord-2-pickup",
        stop_type="pickup",
        order_id="ord-2",
        order_number="N2",
        tracking_number="T2",
        sequence=1,
        address={"lat": 43.70, "lng": -79.40},
        status="pending",
    )
    first = SimpleNamespace(
        stop_id="ord-1-pickup",
        stop_type="pickup",
        order_id="ord-1",
        order_number="N1",
        tracking_number="T1",
        sequence=0,
        address={"lat": 43.66, "lng": -79.39},
        status="pending",
    )
    maps = MagicMock()
    maps.matrix_durations.return_value = ([[(120, 800), (900, 9000)]], "valhalla")
    resolver = NextStopResolver(maps=maps)
    route = SimpleNamespace(stops=[first, near])
    driver = SimpleNamespace(id="drv-1")
    db = MagicMock()
    with (
        patch("porterchain_driver.stops.StopsService.assigned_route", return_value=route),
        patch(
            "porterchain_driver.sequence_store.read_sequence",
            return_value={"waypoints": [{"order_id": "ord-1", "stop_type": "pickup"}]},
        ),
        patch(
            "porterchain_api.driver_engine.last_known.read_last_known",
            return_value=SimpleNamespace(lat=43.65, lng=-79.38),
        ),
    ):
        out = resolver.resolve(db, driver)
    assert out is not None
    assert out["stop_id"] == "ord-1-pickup"
    assert str(out["source"]).startswith("day_plan")
