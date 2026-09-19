"""Batch 6 — mocked paths for high-miss *_service.py modules."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from porterchain_api.admin_engine.clerk_directory_service import ClerkDirectoryService
from porterchain_api.admin_engine.finance_service import AdminFinanceService
from porterchain_api.auth.claims import ClerkClaims
from porterchain_api.auth.invitation_service import InvitationService
from porterchain_api.auth.user_sync_service import UserSyncService
from porterchain_api.billing_engine.driver_finance_service import DriverFinanceService
from porterchain_api.fleetbase_engine.booking_sync_service import BookingSyncService
from porterchain_api.merchant_engine.billing_service import MerchantBillingService
from porterchain_api.merchant_engine.webhook_delivery_service import deliver_merchant_fanout


@patch("porterchain_api.admin_engine.clerk_directory_service.clerk_client_for_kind")
@patch("porterchain_api.admin_engine.clerk_directory_service.is_clerk_secret_configured", return_value=True)
def test_clerk_directory_create_user(mock_cfg, mock_client, db, admin_ctx, settings) -> None:
    clerk_id = f"user_new_clerk_{datetime.now(UTC).timestamp()}"
    mock_client.return_value.create_user.return_value = {"id": clerk_id}
    svc = ClerkDirectoryService()
    email = f"driver-new-{datetime.now(UTC).timestamp()}@svc.test"
    result = svc.create_user(
        db,
        admin_ctx,
        settings,
        user_type="driver",
        email=email,
        name="New Driver",
        send_invite=False,
    )
    assert result["email"] == email


@patch("porterchain_api.auth.invitation_service.clerk_client_for_kind")
def test_invite_driver(mock_clerk, db, admin_ctx, settings, driver) -> None:
    clerk_id = f"user_driver_inv_{datetime.now(UTC).timestamp()}"
    mock_clerk.return_value.invite_user.return_value = SimpleNamespace(
        clerk_user_id=clerk_id,
        clerk_invitation_id=f"inv_drv_{datetime.now(UTC).timestamp()}",
        action="invited",
    )
    inv = InvitationService().invite_driver(db, admin_ctx, settings, driver)
    assert inv.email == driver.email


def test_user_sync_full(db) -> None:
    claims = ClerkClaims(
        clerk_user_id=f"clerk_full_{datetime.now(UTC).timestamp()}",
        email=f"full-{datetime.now(UTC).timestamp()}@test.porterchain.com",
    )
    snapshot = {"role": "customer", "status": "active", "profile": {}, "phone": None}
    with patch.object(UserSyncService, "_platform_snapshot", return_value=snapshot):
        user = UserSyncService().sync(db, claims)
        assert user.clerk_user_id == claims.clerk_user_id


def test_merchant_billing_invoices(db, merchant_ctx) -> None:
    svc = MerchantBillingService()
    assert isinstance(svc.list_invoices(db, merchant_ctx), list)
    assert isinstance(svc.list_invoices_enriched(db, merchant_ctx), list)


def test_driver_finance_period_earnings(db, driver) -> None:
    fin = DriverFinanceService()
    assert fin.period_earnings_cents(db, driver.id, "today") >= 0


@patch.object(BookingSyncService, "__init__", lambda self: None)
def test_booking_sync_cancellation(db, settings, dispatch_order) -> None:
    settings.fleetbase_dispatch_bridge = True
    dispatch_order.fleetbase_order_id = "fb-123"
    svc = BookingSyncService()
    svc._bridge = MagicMock()
    svc.sync_cancellation(db, settings, dispatch_order)
    svc._bridge.cancel_order.assert_not_called()
    from porterchain_api.fleetbase_models import FleetbaseSyncJob

    job = (
        db.query(FleetbaseSyncJob)
        .filter(FleetbaseSyncJob.idempotency_key == f"cancellation:{dispatch_order.id}")
        .first()
    )
    assert job is not None
    assert job.kind == "cancellation"


@patch("porterchain_api.merchant_engine.webhook_delivery_service.SessionLocal")
def test_webhook_fanout_no_hooks(mock_session) -> None:
    mock_db = MagicMock()
    mock_session.return_value.__enter__.return_value = mock_db
    mock_db.query.return_value.filter.return_value.all.return_value = []
    deliver_merchant_fanout({"merchant_id": "m1", "event_type": "order.created", "payload": {}})


def test_finance_record_credit_note(db, admin_ctx, dispatch_order) -> None:
    entry = AdminFinanceService().record_credit_note(
        db,
        admin_ctx,
        order_id=dispatch_order.id,
        amount_cents=500,
        reason="coverage test",
    )
    assert entry.amount_cents == 500
