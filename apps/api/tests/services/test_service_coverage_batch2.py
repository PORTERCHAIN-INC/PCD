"""High-yield *_service.py coverage batch (§2.1.11)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

from porterchain_api.admin_engine.settings_service import AdminSettingsService
from porterchain_api.auth.invitation_service import InvitationService, pending_clerk_id
from porterchain_api.auth.sso_service import SsoService
from porterchain_api.booking_engine.booking_draft_service import BookingDraftService
from porterchain_api.platform.retired_sync import BookingSyncService
from porterchain_api.merchant_engine.webhook_delivery_service import _hook_matches_event
from porterchain_api.schemas import AddressInput, CreateBookingDraftRequest


def test_settings_config_roundtrip(db, admin_ctx) -> None:
    svc = AdminSettingsService()
    svc.set_config(db, admin_ctx, "test.feature_flag", True, reason="unit test")
    assert svc.get_config_value(db, "test.feature_flag") is True


def test_booking_draft_create_and_find(db, settings) -> None:
    session_id = f"svc-draft-{datetime.now(UTC).timestamp()}"
    svc = BookingDraftService()
    body = CreateBookingDraftRequest(
        session_id=session_id,
        pickup=AddressInput(formatted="100 King St W, Toronto", lat=43.65, lng=-79.38),
        dropoff=AddressInput(formatted="200 Bay St, Toronto", lat=43.64, lng=-79.37),
        vehicle_class="cargo_van",
        package_type="looseParcel",
        estimated_pickup=datetime.now(UTC) + timedelta(hours=2),
        schedule_mode="scheduled",
    )
    draft = svc.create_or_update_draft(db, settings, body)
    assert draft.session_id == session_id
    found = svc.find_active_draft(db, session_id=session_id)
    assert found is not None
    assert found.id == draft.id


def test_booking_sync_retry_queue(db, settings) -> None:
    result = BookingSyncService().process_retry_queue(db, settings, limit=5)
    assert isinstance(result, dict)


def test_invitation_pending_clerk_id() -> None:
    assert pending_clerk_id("user@example.com").startswith("pending:")


def test_sso_session_payload() -> None:
    from porterchain_api.domain.admin_states import AdminRole

    principal = MagicMock()
    principal.subject = "sub_1"
    principal.email = "a@example.com"
    principal.roles = [AdminRole.SUPER_ADMIN]
    principal.permissions.return_value = []
    principal.org_id = "org_1"
    payload = SsoService().session_payload(principal)
    assert payload["email"] == "a@example.com"


def test_webhook_event_matching() -> None:
    assert _hook_matches_event(["order.created"], "order.created") is True
    assert _hook_matches_event(["order.*"], "order.delivered") is True
    assert _hook_matches_event(["invoice.paid"], "order.created") is False


def test_invitation_mark_accepted(db) -> None:
    InvitationService().mark_accepted(
        db, email="never-invited@example.com", clerk_user_id="clerk_new"
    )
