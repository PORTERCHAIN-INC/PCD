"""Driver Preview→Accept optimize — apply_on_ready deferral."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from porterchain_driver.jobs import JobsService


def test_driver_optimize_preview_sets_apply_on_ready_false() -> None:
    db = MagicMock()
    driver = SimpleNamespace(id="drv-1", fleetbase_driver_id="driver_abc123xyz")
    order = SimpleNamespace(
        id="ord-1",
        fleetbase_order_id="order_abc123xyz",
        state="DRIVER_ACCEPTED",
        assigned_driver_id="drv-1",
        pickup={"lat": 43.65, "lng": -79.38},
        dropoff={"lat": 43.7, "lng": -79.4},
    )
    vehicle = SimpleNamespace(
        driver_id="drv-1",
        is_active=True,
        fleetbase_vehicle_id="vehicle_abc123xyz",
    )

    svc = JobsService()
    with (
        patch.object(svc, "_today_orders", return_value=[order]),
        patch.object(svc, "list_jobs", return_value={"jobs": [], "upcoming": [], "completed": []}),
        patch("porterchain_driver.sequence_store.read_sequence", return_value=None),
        patch(
            "porterchain_api.dispatch_engine.day_plan.queue_one_van",
            return_value={
                "run_id": "run-1",
                "status": "pending",
                "assignments": [],
                "metrics": {"engine": "porterchain"},
                "apply_on_ready": False,
                "engine": "porterchain",
            },
        ) as enqueue,
        patch(
            "porterchain_api.admin_models.Vehicle"
        ),
    ):
        # Query chain for vehicles
        db.query.return_value.filter.return_value.all.return_value = [vehicle]
        out = svc.optimize_route(db, driver, preview=True)

    assert out["preview"] is True
    assert out["apply_on_ready"] is False
    assert enqueue.call_args.args[0]["apply_on_ready"] is False
    assert enqueue.call_args.args[0]["pc_driver_id"] == "drv-1"


def test_optimize_run_status_preview_does_not_apply() -> None:
    db = MagicMock()
    driver = SimpleNamespace(id="drv-1")
    svc = JobsService()
    rec = {
        "run_id": "run-1",
        "status": "ready",
        "assignments": [{"order_id": "o1", "sequence": 1}],
        "metrics": {},
        "apply_on_ready": False,
    }
    with (
        patch(
            "porterchain_api.admin_engine.orchestrator_ops_service.OrchestratorOpsService.get_run",
            return_value=rec,
        ),
        patch("porterchain_driver.sequence_store.read_sequence", return_value=None),
        patch("porterchain_driver.sequence_store.apply_run_to_driver") as apply,
        patch.object(svc, "list_jobs", return_value={"jobs": []}),
        patch.object(svc, "plan_from_run", return_value={"status": "ready", "jobs": {}}),
    ):
        out = svc.optimize_run_status(db, driver, "run-1", apply=False)
    apply.assert_not_called()
    assert out.get("applied") is False


def test_accept_optimize_run_applies() -> None:
    db = MagicMock()
    driver = SimpleNamespace(id="drv-1")
    svc = JobsService()
    rec = {
        "run_id": "run-1",
        "status": "ready",
        "assignments": [{"order_id": "o1", "sequence": 1}],
        "metrics": {"after_distance_km": 10},
        "apply_on_ready": False,
    }
    with (
        patch(
            "porterchain_api.admin_engine.orchestrator_ops_service.OrchestratorOpsService.get_run",
            return_value=rec,
        ),
        patch("porterchain_driver.sequence_store.read_sequence", return_value=None),
        patch(
            "porterchain_driver.sequence_store.apply_run_to_driver",
            return_value=[{"sequence": 0}],
        ) as apply,
        patch("porterchain_api.dispatch_engine.optimize_events.emit_applied"),
        patch.object(svc, "list_jobs", return_value={"jobs": []}),
        patch.object(
            svc,
            "plan_from_run",
            return_value={"status": "ready", "jobs": {}, "applied": True},
        ),
    ):
        out = svc.accept_optimize_run(db, driver, "run-1")
    apply.assert_called_once()
    assert out.get("applied") is True
