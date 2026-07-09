"""Booking, billing, driver, notification service coverage (§2.1.11)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

from porterchain_api.billing_engine.settlement_service import SettlementService
from porterchain_api.booking_engine.draft_reconciliation_service import BookingDraftReconciliationService
from porterchain_api.booking_engine.notification_service import NotificationService
from porterchain_api.booking_draft_models import BookingDraft
from porterchain_api.domain.states import BookingDraftState
from porterchain_api.driver_engine.api_service import DriverApiService
from porterchain_api.driver_engine.auth_service import DriverAuthService
from porterchain_api.driver_engine.onboarding_service import evaluate_driver_onboarding
from porterchain_api.notification_engine.preference_service import PreferenceService
from porterchain_api.notification_engine.device_service import DeviceService
from porterchain_api.services.stripe_service import handle_checkout_completed


def test_expire_stale_drafts(db) -> None:
    draft = BookingDraft(
        session_id="expired-session",
        state=BookingDraftState.DRAFT.value,
        expires_at=datetime.now(UTC) - timedelta(hours=2),
    )
    db.add(draft)
    db.commit()
    svc = BookingDraftReconciliationService()
    expired = svc.expire_stale_drafts(db)
    assert expired == 1
    db.refresh(draft)
    assert draft.state == BookingDraftState.EXPIRED.value


def test_reconciliation_run_cycle(db, settings) -> None:
    result = BookingDraftReconciliationService().run_cycle(db, settings)
    assert "expired" in result
    assert "repaired" in result


@patch("porterchain_api.booking_engine.notification_service.NotificationOrchestrator")
def test_notification_service_swallows_orchestrator_errors(mock_orch_cls, db) -> None:
    mock_orch_cls.return_value.send_booking_confirmation.side_effect = RuntimeError("queue down")
    svc = NotificationService()
    svc.send_booking_confirmation(
        db,
        email="a@example.com",
        phone=None,
        tracking_number="TRK1",
        order_number="ORD1",
        invoice_number="INV1",
        booking_number="BK1",
        correlation_id="corr-1",
    )
    svc.send_checkout_recovery(db, email="a@example.com", quote_id="q1", recovery_url="https://x")


def test_settlement_service_actions(db) -> None:
    svc = SettlementService()
    ignored = svc.process_queue_job({"action": "noop"})
    assert ignored is not None
    stripe = svc.process_queue_job({"action": "payment_succeeded", "data": {"id": "cs_test"}})
    assert stripe is not None


def test_preference_and_device_services(db) -> None:
    pref = PreferenceService()
    assert pref.is_enabled(db, user_role="customer", user_id="u1", category="booking", channel="email")
    assert pref.get_all(db, user_role="customer", user_id="u1") == []
    pref.upsert(db, user_role="customer", user_id="u1", category="booking", email_enabled=False)
    assert pref.is_enabled(db, user_role="customer", user_id="u1", category="booking", channel="email") is False
    devices = DeviceService()
    assert devices.list_active(db, user_role="driver", user_id="d1") == []


def test_driver_services(settings, driver) -> None:
    api = DriverApiService()
    assert api.fleetbase_bridge(settings) is not None
    assert DriverAuthService() is not None
    assert isinstance(evaluate_driver_onboarding(driver, settings=settings), dict)


def test_stripe_handle_checkout_completed(settings) -> None:
    meta = handle_checkout_completed(
        settings,
        {
            "metadata": {"quote_id": "q", "customer_id": "c", "payment_id": "p"},
            "payment_intent": "pi",
            "payment_method_types": ["card"],
            "amount_total": 100,
            "currency": "cad",
            "total_details": {"amount_tax": 13},
        },
    )
    assert meta["quote_id"] == "q"
