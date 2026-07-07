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


def test_process_dispatch_push_order(dispatch_module) -> None:
    mock_order = MagicMock(id="ord_123")
    mock_sync = MagicMock()
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = mock_order
    mock_session = MagicMock()
    mock_session.__enter__ = MagicMock(return_value=mock_db)
    mock_session.__exit__ = MagicMock(return_value=False)

    with (
        patch("porterchain_api.db.SessionLocal", return_value=mock_session),
        patch(
            "porterchain_api.fleetbase_engine.booking_sync_service.BookingSyncService",
            return_value=mock_sync,
        ),
    ):
        dispatch_module.process_dispatch({"order_id": "ord_123", "action": "dispatch_ready"})

    mock_sync.push_order.assert_called_once()
    mock_db.commit.assert_called_once()


def test_process_dispatch_assign_driver(dispatch_module) -> None:
    mock_order = MagicMock(id="ord_456", fleetbase_order_id="fb_1")
    mock_driver = MagicMock(id="drv_1", fleetbase_driver_id="fb_drv_1")
    mock_sync = MagicMock()
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.side_effect = [mock_order, mock_driver]
    mock_session = MagicMock()
    mock_session.__enter__ = MagicMock(return_value=mock_db)
    mock_session.__exit__ = MagicMock(return_value=False)

    with (
        patch("porterchain_api.db.SessionLocal", return_value=mock_session),
        patch(
            "porterchain_api.fleetbase_engine.booking_sync_service.BookingSyncService",
            return_value=mock_sync,
        ),
    ):
        dispatch_module.process_dispatch(
            {"order_id": "ord_456", "action": "assign", "driver_id": "drv_1"}
        )

    mock_sync.push_driver_assignment.assert_called_once()
    mock_db.commit.assert_called_once()


def test_process_dispatch_missing_order_id(dispatch_module) -> None:
    with patch("porterchain_api.db.SessionLocal") as session_local:
        dispatch_module.process_dispatch({"action": "dispatch_ready"})
    session_local.assert_not_called()
