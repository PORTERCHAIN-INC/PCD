"""P0 driver jobs — assigned-order, accept/reject, scan/COD, offline executor."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from porterchain_api.driver_engine.api_service import DriverApiService
from porterchain_api.driver_engine.offline_executor import DriverOfflineExecutor
from porterchain_api.main import app
from porterchain_api.merchant_engine.scan_gate_service import ScanGateService
from porterchain_driver.availability import AvailabilityService


@pytest.mark.driver_p0
def test_api_d_02_require_assigned_order_matrix() -> None:
    """API-D-02 — assigned / unassigned / foreign driver."""
    db = MagicMock()

    db.get = MagicMock(return_value=SimpleNamespace(id="o1", assigned_driver_id="d1"))
    assert DriverApiService.require_assigned_order(db, driver_id="d1", order_id="o1").id == "o1"

    db.get = MagicMock(return_value=SimpleNamespace(id="o2", assigned_driver_id=None))
    assert DriverApiService.require_assigned_order(db, driver_id="d1", order_id="o2").id == "o2"

    db.get = MagicMock(return_value=SimpleNamespace(id="o3", assigned_driver_id="other"))
    with pytest.raises(PermissionError, match="not_assigned_driver"):
        DriverApiService.require_assigned_order(db, driver_id="d1", order_id="o3")


@pytest.mark.driver_p0
def test_api_d_02_accept_reject_missing_order() -> None:
    """API-D-02 — accept/reject raise when assignment row missing."""
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    driver = SimpleNamespace(id="d1")
    svc = AvailabilityService()

    with pytest.raises(LookupError, match="order_not_found"):
        svc.accept_assignment(db, driver, "missing-order")
    with pytest.raises(LookupError, match="order_not_found"):
        svc.reject_assignment(db, driver, "missing-order")


@pytest.mark.driver_p0
def test_api_d_02_accept_reject_only_while_assigned() -> None:
    """In-progress jobs must not be accepted or declined again."""
    db = MagicMock()
    order = SimpleNamespace(id="ord-1", state="PICKED_UP", assigned_driver_id="d1")
    db.query.return_value.filter.return_value.first.return_value = order
    driver = SimpleNamespace(id="d1")
    svc = AvailabilityService()

    with pytest.raises(ValueError, match="job_not_awaiting_response"):
        svc.accept_assignment(db, driver, "ord-1")
    with pytest.raises(ValueError, match="job_not_awaiting_response"):
        svc.reject_assignment(db, driver, "ord-1")


@pytest.mark.driver_p0
def test_api_d_02_jobs_lifecycle_openapi_routes() -> None:
    paths = set(app.openapi().get("paths", {}))
    required = {
        "/driver-api/v1/orders/{order_id}/accept",
        "/driver-api/v1/orders/{order_id}/reject",
        "/driver-api/v1/routes/{route_id}/stops/{stop_id}/arrive",
        "/driver-api/v1/routes/{route_id}/stops/{stop_id}/deliver",
    }
    missing = sorted(p for p in required if p not in paths)
    assert not missing, f"missing jobs lifecycle OpenAPI paths: {missing}"


@pytest.mark.driver_p0
def test_api_d_02_accept_reject_request_schema() -> None:
    """Lock-screen Decline posts AcceptRejectRequest.reason; Accept may omit body."""
    from porterchain_api.schemas_driver import AcceptRejectRequest

    assert AcceptRejectRequest().reason is None
    assert AcceptRejectRequest(reason="unavailable").reason == "unavailable"


@pytest.mark.driver_p0
def test_api_d_04_package_scan_phase_validation() -> None:
    """API-D-04 — scan_qr_from_body rejects invalid phase before package work."""
    order = SimpleNamespace(id="ord-scan")
    db = MagicMock()
    with pytest.raises(ValueError, match="phase_must_be_pickup_or_delivery"):
        ScanGateService().scan_qr_from_body(db, order, {"qr_payload": "x", "phase": "warehouse"})


@pytest.mark.driver_p0
def test_api_d_04_cod_checkout_and_scan_openapi() -> None:
    paths = set(app.openapi().get("paths", {}))
    assert "/driver-api/v1/orders/{order_id}/packages/scan" in paths
    assert "/driver-api/v1/orders/{order_id}/cod-checkout" in paths
    from porterchain_api.billing_engine.stripe_cod_service import StripeCodService

    assert hasattr(StripeCodService, "issue_cod_checkout_for_order")


@pytest.mark.driver_p0
def test_api_d_07_offline_executor_dispatches_arrive() -> None:
    """API-D-07 — offline executor routes arrive_stop to StopsService."""
    platform = MagicMock()
    executor = DriverOfflineExecutor(platform=platform)
    db = MagicMock()
    driver = SimpleNamespace(id="d1")
    executor.execute(
        db,
        driver,
        "arrive_stop",
        {"stop_id": "stop-1"},
    )
    platform.stops.arrive_stop.assert_called_once_with(db, driver, "stop-1")


@pytest.mark.driver_p0
def test_api_d_07_offline_executor_dispatches_deliver() -> None:
    """API-D-07 — deliver_stop replays through StopsService (sync meter path)."""
    platform = MagicMock()
    executor = DriverOfflineExecutor(platform=platform)
    db = MagicMock()
    driver = SimpleNamespace(id="d1")
    executor.execute(
        db,
        driver,
        "deliver_stop",
        {"stop_id": "stop-2"},
    )
    platform.stops.deliver_stop.assert_called_once_with(db, driver, "stop-2")


@pytest.mark.driver_p0
def test_api_d_07_offline_executor_unknown_action() -> None:
    """API-D-07 — unknown offline actions raise (never silently drop)."""
    executor = DriverOfflineExecutor(platform=MagicMock())
    with pytest.raises(ValueError, match="unsupported_offline_action"):
        executor.execute(MagicMock(), SimpleNamespace(id="d1"), "totally_unknown_action_xyz", {})
