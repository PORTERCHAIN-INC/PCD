"""Batch 8 — cross 60% *_service.py coverage floor."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from porterchain_api.admin_engine.clerk_directory_service import ClerkDirectoryService
from porterchain_api.admin_engine.control_tower_service import (
    ControlTowerService,
    _column_for_state,
    _has_coords,
    _transition_path,
)
from porterchain_api.domain.states import OrderState
from porterchain_api.merchant_engine.integrations_service import MerchantIntegrationsService
from porterchain_api.merchant_engine.tracking_service import MerchantTrackingService, _normalize_pod


def test_control_tower_helpers() -> None:
    assert _column_for_state("DISPATCH_READY") == "waiting_dispatch"
    assert _column_for_state("UNKNOWN") is None
    assert _has_coords({"lat": 43.65, "lng": -79.38}) is True
    assert _has_coords({}) is False
    path = _transition_path(OrderState.DISPATCH_READY, OrderState.DRIVER_ASSIGNED)
    assert path is not None
    assert path[-1] == OrderState.DRIVER_ASSIGNED


def test_control_tower_extended(db, admin_ctx, dispatch_order, driver) -> None:
    tower = ControlTowerService()
    dispatch_order.assigned_driver_id = driver.id
    db.commit()

    assert isinstance(tower.active_orders(db), list)
    assert isinstance(tower.queue(db), list)
    assert isinstance(tower.dispatch_pool(db), list)
    assert isinstance(tower.assignable_drivers(db), list)
    assert isinstance(tower.exceptions(db), list)
    assert isinstance(tower.sla_monitor(db), dict)
    assert isinstance(tower.live_activity(db), list)
    assert isinstance(tower.ai_ops(db), dict)

    with pytest.raises(ValueError, match="execution_moves_run_in_fleetbase"):
        tower.move_board_order(db, admin_ctx, dispatch_order.id, "assigned")

    with pytest.raises(ValueError, match="exception_reason_required"):
        tower.move_board_order(db, admin_ctx, dispatch_order.id, "failed")

    card = tower.move_board_order(
        db, admin_ctx, dispatch_order.id, "failed", reason="Customer unavailable"
    )
    assert card["state"] == OrderState.FAILED.value


def test_normalize_pod_variants() -> None:
    pod = _normalize_pod(
        [
            {"type": "photo", "url": "https://example.com/p.jpg"},
            {"type": "signature", "signature": "Jane"},
            {"type": "otp", "code": "1234"},
            {"type": "other", "notes": "left at door"},
        ]
    )
    assert len(pod["photos"]) == 1
    assert len(pod["signatures"]) == 1
    assert len(pod["otp"]) == 1
    assert pod["complete"] is True


def test_merchant_integrations_catalog(db, merchant_ctx) -> None:
    svc = MerchantIntegrationsService()
    assert isinstance(svc.sandbox_status(merchant_ctx), dict)
    toggled = svc.set_sandbox_mode(db, merchant_ctx, enabled=True)
    assert toggled["sandbox_mode"] is True
    assert isinstance(svc.usage(db, merchant_ctx, days=14), dict)
    assert isinstance(svc.rate_limits(db, merchant_ctx), dict)
    assert isinstance(svc.documentation(api_base_url="http://localhost:8001"), dict)
    assert isinstance(svc.event_catalog(), dict)
    assert isinstance(svc.erp_readiness(), dict)
    assert isinstance(svc.oauth_readiness(enabled=True), dict)
    assert isinstance(svc.csv_templates(), dict)
    assert isinstance(svc.csv_template_download("bulk_orders"), str)


@patch.object(MerchantTrackingService, "_fetch_live", return_value={})
@patch.object(MerchantTrackingService, "_translate_live", return_value={"location": {"lat": 43.65, "lng": -79.38}})
@patch.object(MerchantTrackingService, "_osrm_eta", return_value={"minutes": 12})
def test_merchant_tracking_dashboard_mocked(
    mock_eta, mock_translate, mock_live, db, settings, merchant_ctx, dispatch_order
) -> None:
    dispatch_order.state = OrderState.IN_TRANSIT.value
    db.commit()
    dash = MerchantTrackingService().dashboard(db, settings, merchant_ctx)
    assert dash["active_count"] >= 1
    assert dash["orders"][0]["eta"] == {"minutes": 12}


@patch("porterchain_api.admin_engine.clerk_directory_service.clerk_client_for_kind")
@patch("porterchain_api.admin_engine.clerk_directory_service.is_clerk_secret_configured", return_value=True)
def test_clerk_directory_create_driver_password(mock_cfg, mock_client, db, admin_ctx, settings) -> None:
    clerk_id = f"user_drv_clerk_{datetime.now(UTC).timestamp()}"
    mock_client.return_value.create_user.return_value = {"id": clerk_id}
    svc = ClerkDirectoryService()
    email = f"driver-pw-{datetime.now(UTC).timestamp()}@svc.test"
    result = svc.create_user(
        db,
        admin_ctx,
        settings,
        user_type="driver",
        email=email,
        name="Password Driver",
        password="SecurePass123!",
        send_invite=False,
    )
    assert result["email"] == email
    assert result["clerk_action"] == "created_with_password"
