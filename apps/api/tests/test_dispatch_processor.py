"""Dispatch worker processor tests (DD-05a)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def dispatch_module():
    import sys
    from pathlib import Path

    worker_root = Path(__file__).resolve().parents[2] / "worker"
    if str(worker_root) not in sys.path:
        sys.path.insert(0, str(worker_root))
    from processors import dispatch

    return dispatch


def test_process_dispatch_does_not_push_the_order(dispatch_module) -> None:
    with patch("porterchain_api.db.SessionLocal") as session_local:
        dispatch_module.process_dispatch({"order_id": "ord_123", "action": "dispatch_ready"})
    session_local.assert_not_called()


def test_process_dispatch_does_not_push_assignment(dispatch_module) -> None:
    with patch("porterchain_api.db.SessionLocal") as session_local:
        dispatch_module.process_dispatch(
            {"order_id": "ord_456", "action": "assign", "driver_id": "drv_1"}
        )
    session_local.assert_not_called()


def test_process_dispatch_optimize_run(dispatch_module) -> None:
    mock_db = MagicMock()
    mock_session = MagicMock()
    mock_session.__enter__ = MagicMock(return_value=mock_db)
    mock_session.__exit__ = MagicMock(return_value=False)
    mock_orch = MagicMock()
    mock_orch.execute_queued_run.return_value = {"status": "ready", "assignments": []}

    with (
        patch("porterchain_api.db.SessionLocal", return_value=mock_session),
        patch(
            "porterchain_api.admin_engine.orchestrator_ops_service.OrchestratorOpsService",
            return_value=mock_orch,
        ),
    ):
        dispatch_module.process_dispatch({"action": "optimize_run", "run_id": "run-1"})

    mock_orch.execute_queued_run.assert_called_once_with(mock_db, "run-1")


def test_process_dispatch_porterchain_run_does_not_call_fleetbase(dispatch_module) -> None:
    mock_db = MagicMock()
    mock_session = MagicMock()
    mock_session.__enter__ = MagicMock(return_value=mock_db)
    mock_session.__exit__ = MagicMock(return_value=False)
    mock_orch = MagicMock()
    mock_orch.get_run.return_value = {"engine": "porterchain", "phase": "accept", "points": []}

    with (
        patch("porterchain_api.db.SessionLocal", return_value=mock_session),
        patch(
            "porterchain_api.admin_engine.orchestrator_ops_service.OrchestratorOpsService",
            return_value=mock_orch,
        ),
        patch(
            "porterchain_api.dispatch_engine.day_plan.finish_porterchain_run",
            return_value={"status": "ready", "assignments": []},
        ) as finish,
    ):
        dispatch_module.process_dispatch({"action": "optimize_run", "run_id": "run-pc"})

    finish.assert_called_once()
    mock_orch.execute_queued_run.assert_not_called()


def test_process_dispatch_optimize_run_missing_id(dispatch_module) -> None:
    with patch("porterchain_api.db.SessionLocal") as session_local:
        dispatch_module.process_dispatch({"action": "optimize_run"})
    session_local.assert_not_called()


def test_process_dispatch_optimize_import(dispatch_module) -> None:
    with patch.object(dispatch_module, "_optimize_import") as opt:
        dispatch_module.process_dispatch({"action": "optimize_import", "job_id": "job-2"})
    opt.assert_called_once_with("job-2")


def test_process_dispatch_missing_order_id(dispatch_module) -> None:
    with patch("porterchain_api.db.SessionLocal") as session_local:
        dispatch_module.process_dispatch({"action": "dispatch_ready"})
    session_local.assert_not_called()
