"""P0 route-optimize commit path — idempotency, CAS, Fleetbase-only apply, no cuOpt SoT.

Maps to docs/ROUTE_OPTIMIZATION_DEV_TEST_CASES.md checklist §21 items 1–3, 8–9
and cases API-A-009/010/016, SEQ-001, ENG-021, API-D-005.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from porterchain_api.admin_engine.orchestrator_ops_service import OrchestratorOpsService
from porterchain_driver.jobs import JobsService
from porterchain_driver.sequence_store import SequenceConflictError


def test_commit_requires_assignments() -> None:
    svc = OrchestratorOpsService()
    with pytest.raises(ValueError, match="assignments_required"):
        svc.commit(MagicMock(), assignments=[])


def test_commit_records_assignments_without_fleetbase() -> None:
    svc = OrchestratorOpsService()
    assignments = [
        {
            "order_id": "order_abc123",
            "vehicle_id": "vehicle_abc123",
            "driver_id": "driver_abc123",
            "porterchain_order_id": "pc-1",
            "distance_m": 1200,
            "duration_s": 400,
            "sequence": 1,
        }
    ]
    with (
        patch(
            "porterchain_api.admin_engine.orchestrator_ops_service._write_commit_cache"
        ) as write_cache,
        patch(
            "porterchain_api.admin_engine.orchestrator_ops_service._read_commit_cache",
            return_value=None,
        ),
    ):
        out = svc.commit(
            MagicMock(),
            assignments=assignments,
            scheduled_date="2026-09-17",
            run_id="run-commit-1",
        )

    assert out["ok"] is True
    assert out["engine"] == "porterchain"
    assert out["idempotent"] is False
    assert out["run_id"] == "run-commit-1"
    assert out["scheduled_date"] == "2026-09-17"
    assert out["assignments"] == assignments
    write_cache.assert_called_once()


def test_commit_idempotent_by_run_id() -> None:
    svc = OrchestratorOpsService()
    prior = {
        "ok": True,
        "run_id": "run-idem",
        "scheduled_date": "2026-09-17",
        "committed_at": "2026-09-17T12:00:00+00:00",
        "idempotent": False,
    }
    with patch(
        "porterchain_api.admin_engine.orchestrator_ops_service._read_commit_cache",
        return_value=prior,
    ):
        out = svc.commit(
            MagicMock(),
            assignments=[{"order_id": "order_abc123", "sequence": 1}],
            run_id="run-idem",
        )

    assert out["idempotent"] is True
    assert out["run_id"] == "run-idem"
    assert out["ok"] is True


def test_commit_sequence_conflict() -> None:
    svc = OrchestratorOpsService()
    with (
        patch(
            "porterchain_api.admin_engine.orchestrator_ops_service._read_commit_cache",
            return_value=None,
        ),
        patch(
            "porterchain_driver.sequence_store.read_sequence",
            return_value={"version": 3},
        ),
    ):
        with pytest.raises(SequenceConflictError) as excinfo:
            svc.commit(
                MagicMock(),
                assignments=[{"order_id": "order_abc123", "sequence": 1}],
                run_id="run-cas",
                pc_driver_id="drv-1",
                expected_sequence_version=1,
            )
    assert excinfo.value.current_version == 3
    assert excinfo.value.expected_version == 1


def test_commit_applies_driver_sequence_when_pc_driver_id() -> None:
    svc = OrchestratorOpsService()
    with (
        patch(
            "porterchain_api.admin_engine.orchestrator_ops_service._read_commit_cache",
            return_value=None,
        ),
        patch(
            "porterchain_api.admin_engine.orchestrator_ops_service._write_commit_cache"
        ),
        patch(
            "porterchain_driver.sequence_store.read_sequence",
            return_value={"version": 0},
        ),
        patch(
            "porterchain_driver.sequence_store.apply_run_to_driver",
            return_value=[],
        ) as apply,
    ):
        out = svc.commit(
            MagicMock(),
            assignments=[{"order_id": "order_abc123", "sequence": 1}],
            run_id="run-seq",
            pc_driver_id="drv-9",
            expected_sequence_version=0,
        )

    assert out["ok"] is True
    apply.assert_called_once()
    assert apply.call_args.args[0] == "drv-9"
    assert apply.call_args.kwargs["expected_version"] == 0


def test_optimize_commit_router_maps_conflict_to_409() -> None:
    from fastapi import HTTPException

    from porterchain_api.routers import operations as ops_router
    from porterchain_api.schemas_admin import OptimizeCommitBody

    body = OptimizeCommitBody(
        assignments=[{"order_id": "o1"}],
        run_id="run-x",
        expected_sequence_version=1,
        pc_driver_id="drv-1",
    )
    ctx = MagicMock()
    with patch.object(
        ops_router,
        "_invoke",
        side_effect=SequenceConflictError(current_version=4, expected_version=1),
    ):
        with pytest.raises(HTTPException) as excinfo:
            ops_router.optimize_commit(body, ctx, MagicMock())
    assert excinfo.value.status_code == 409
    detail = excinfo.value.detail
    assert detail["code"] == "sequence_version_conflict"
    assert detail["current_version"] == 4
    assert detail["expected_version"] == 1


def test_undo_optimize_nothing_to_undo() -> None:
    svc = JobsService()
    driver = SimpleNamespace(id="drv-1")
    with (
        patch(
            "porterchain_driver.sequence_store.rollback_sequence",
            return_value=None,
        ),
        patch.object(svc, "list_jobs", return_value={"jobs": []}),
    ):
        out = svc.undo_optimize(MagicMock(), driver)
    assert out["ok"] is False
    assert out["error"] == "nothing_to_undo"


def test_undo_optimize_restores_snapshot() -> None:
    svc = JobsService()
    driver = SimpleNamespace(id="drv-1")
    restored = {
        "run_id": "run-prev",
        "version": 2,
        "waypoints": [{"order_id": "o1", "sequence": 0}],
        "metrics": {"after_distance_km": 3.0},
    }
    with (
        patch(
            "porterchain_driver.sequence_store.rollback_sequence",
            return_value=restored,
        ),
        patch.object(svc, "list_jobs", return_value={"jobs": [{"id": "j1"}]}),
    ):
        out = svc.undo_optimize(MagicMock(), driver)
    assert out["ok"] is True
    assert out["run_id"] == "run-prev"
    assert out["sequence_version"] == 2
    assert out["optimized_stops"] == restored["waypoints"]


def test_accept_optimize_propagates_sequence_conflict() -> None:
    svc = JobsService()
    driver = SimpleNamespace(id="drv-1")
    rec = {
        "run_id": "run-1",
        "status": "ready",
        "assignments": [{"order_id": "o1", "sequence": 1}],
        "metrics": {},
    }
    with (
        patch(
            "porterchain_api.admin_engine.orchestrator_ops_service.OrchestratorOpsService.get_run",
            return_value=rec,
        ),
        patch("porterchain_driver.sequence_store.read_sequence", return_value={"version": 5}),
        patch(
            "porterchain_driver.sequence_store.apply_run_to_driver",
            side_effect=SequenceConflictError(current_version=5, expected_version=2),
        ),
        patch.object(svc, "list_jobs", return_value={"jobs": []}),
    ):
        with pytest.raises(SequenceConflictError) as excinfo:
            svc.accept_optimize_run(MagicMock(), driver, "run-1", expected_version=2)
    assert excinfo.value.current_version == 5


def test_execute_queued_run_is_porterchain_only() -> None:
    """Commit and the worker finish path never write through Fleetbase or cuOpt."""
    import inspect

    commit_src = inspect.getsource(OrchestratorOpsService.commit)
    assert "run_cuopt_shadow" not in commit_src
    assert "cuopt_shadow" not in commit_src
    exec_src = inspect.getsource(OrchestratorOpsService.execute_queued_run)
    assert "finish_porterchain_run" in exec_src
    assert "get_fleetbase_integration" not in exec_src
