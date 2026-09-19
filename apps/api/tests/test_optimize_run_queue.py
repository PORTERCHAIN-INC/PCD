"""Step 2 Wave 0 — admin optimize run is queued, not inline Fleetbase HTTP."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from porterchain_api.admin_engine.orchestrator_ops_service import OrchestratorOpsService


def test_enqueue_run_does_not_call_adapter() -> None:
    db = MagicMock()
    svc = OrchestratorOpsService()
    with (
        patch.object(
            svc, "_resolve_fleetbase_ids", return_value=(["order_abc123"], {"order_abc123": "pc-1"}, [])
        ),
        patch.object(svc, "_synced_fleet", return_value=(["vehicle_abc123"], ["driver_abc123"])),
        patch("porterchain_api.admin_engine.orchestrator_ops_service.write_optimize_run") as write,
        patch("porterchain_api.admin_engine.orchestrator_ops_service.enqueue_optimize_job") as enq,
        patch("porterchain_api.admin_engine.orchestrator_ops_service.get_fleetbase_integration") as fb,
    ):
        out = svc.enqueue_run(db, mode="allocate", engine="greedy")
    assert out["status"] == "pending"
    assert out["ok"] is True
    assert out["run_id"]
    assert out["assignments"] == []
    write.assert_called_once()
    enq.assert_called_once_with(out["run_id"])
    fb.assert_not_called()


def test_enqueue_run_no_synced_orders_skips_queue() -> None:
    db = MagicMock()
    svc = OrchestratorOpsService()
    with (
        patch.object(svc, "_resolve_fleetbase_ids", return_value=([], {}, ["pc-missing"])),
        patch("porterchain_api.admin_engine.orchestrator_ops_service.enqueue_optimize_job") as enq,
        patch("porterchain_api.admin_engine.orchestrator_ops_service.get_fleetbase_integration") as fb,
    ):
        out = svc.enqueue_run(db)
    assert out["status"] == "error"
    assert out["error"] == "no_synced_orders"
    assert out["ok"] is False
    enq.assert_not_called()
    fb.assert_not_called()


def test_enqueue_run_no_synced_vehicles_skips_queue() -> None:
    db = MagicMock()
    svc = OrchestratorOpsService()
    with (
        patch.object(
            svc, "_resolve_fleetbase_ids", return_value=(["order_abc123"], {"order_abc123": "pc-1"}, [])
        ),
        patch.object(svc, "_synced_fleet", return_value=([], [])),
        patch("porterchain_api.admin_engine.orchestrator_ops_service.enqueue_optimize_job") as enq,
        patch("porterchain_api.admin_engine.orchestrator_ops_service.get_fleetbase_integration") as fb,
    ):
        out = svc.enqueue_run(db)
    assert out["status"] == "error"
    assert out["error"] == "no_synced_vehicles"
    assert out["ok"] is False
    enq.assert_not_called()
    fb.assert_not_called()


def test_run_passes_vehicle_ids_to_adapter() -> None:
    db = MagicMock()
    svc = OrchestratorOpsService()
    adapter = MagicMock()
    adapter.run_orchestrator.return_value = {
        "ok": True,
        "assignments": [{"order_id": "order_abc123"}],
        "metrics": {},
    }
    with (
        patch.object(
            svc, "_resolve_fleetbase_ids", return_value=(["order_abc123"], {"order_abc123": "pc-1"}, [])
        ),
        patch.object(svc, "_synced_fleet", return_value=(["vehicle_abc123"], ["driver_abc123"])),
        patch(
            "porterchain_api.admin_engine.orchestrator_ops_service.get_settings"
        ),
        patch(
            "porterchain_api.admin_engine.orchestrator_ops_service.get_fleetbase_integration",
            return_value=adapter,
        ),
    ):
        out = svc.run(db, engine="greedy")
    adapter.run_orchestrator.assert_called_once_with(
        ["order_abc123"],
        mode="allocate",
        engine="greedy",
        vehicle_ids=["vehicle_abc123"],
        driver_ids=["driver_abc123"],
        prior_assignments=None,
    )
    assert out["assignments"][0]["porterchain_order_id"] == "pc-1"
    assert out["vehicle_ids"] == ["vehicle_abc123"]
    # Fuel scorecard attaches even when Fleetbase metrics are empty (0 km → 0¢).
    assert "estimated_fuel_cents" in (out.get("metrics") or {})
    assert "estimated_fuel_liters" in (out.get("metrics") or {})


def test_execute_queued_run_writes_ready() -> None:
    db = MagicMock()
    svc = OrchestratorOpsService()
    pending = {
        "run_id": "run-1",
        "status": "pending",
        "order_ids": ["pc-1"],
        "mode": "allocate",
        "engine": "greedy",
        "assignments": [],
    }
    solved = {
        "ok": True,
        "assignments": [{"order_id": "fb-1", "porterchain_order_id": "pc-1"}],
        "metrics": {"assigned_count": 1},
    }
    with (
        patch(
            "porterchain_api.admin_engine.orchestrator_ops_service.read_optimize_run",
            return_value=pending,
        ),
        patch("porterchain_api.admin_engine.orchestrator_ops_service.write_optimize_run") as write,
        patch.object(svc, "run", return_value=solved),
    ):
        out = svc.execute_queued_run(db, "run-1")
    assert out["status"] == "ready"
    assert out["ok"] is True
    assert len(out["assignments"]) == 1
    write.assert_called_once()
    assert write.call_args[0][0] == "run-1"
    assert write.call_args[0][1]["status"] == "ready"
