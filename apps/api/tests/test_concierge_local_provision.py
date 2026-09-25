"""Super Admin concierge — local provision without Clerk; merchant seats without Clerk."""

from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest

from porterchain_api.admin_engine.clerk_directory_service import ClerkDirectoryService
from porterchain_api.admin_engine.rbac import AdminContext
from porterchain_api.admin_models import Driver
from porterchain_api.domain.admin_states import AdminRole, DriverStatus
from porterchain_api.domain.merchant_states import MerchantStatus
from porterchain_api.merchant_engine.lookups import get_merchant_user_by_email
from porterchain_api.merchant_engine.provision import create_onboarding_merchant


def _ctx(db) -> AdminContext:
    from porterchain_api.admin_engine.staff_lookups import ensure_local_super_admin

    user = ensure_local_super_admin(db)
    return AdminContext(user=user, role=AdminRole.SUPER_ADMIN)


def _email(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}@example.com"


def test_create_driver_local_pending_when_clerk_down(db, settings) -> None:
    svc = ClerkDirectoryService()
    email = _email("local-driver")
    with patch(
        "porterchain_api.admin_engine.clerk_directory_service.is_clerk_secret_configured",
        return_value=False,
    ):
        out = svc.create_user(
            db,
            _ctx(db),
            settings,
            "driver",
            email=email,
            name="Local Driver",
            send_invite=True,
        )
    assert out["clerk_action"] == "local_pending"
    assert out["clerk_user_id"] is None
    driver = db.get(Driver, out["platform_user_id"])
    assert driver is not None
    assert driver.status == DriverStatus.PENDING.value
    assert str(driver.clerk_user_id).startswith("pending:")


def test_create_driver_skip_invite_is_local(db, settings) -> None:
    svc = ClerkDirectoryService()
    email = _email("ops-driver")
    out = svc.create_user(
        db,
        _ctx(db),
        settings,
        "driver",
        email=email,
        name="Ops Driver",
        send_invite=False,
    )
    assert out["clerk_action"] == "local_pending"
    driver = db.get(Driver, out["platform_user_id"])
    assert driver is not None
    assert str(driver.clerk_user_id).startswith("pending:")


def test_merchant_seat_without_clerk_secret(db, settings) -> None:
    owner = _email("owner")
    seat_email = _email("ops")
    merchant = create_onboarding_merchant(
        db,
        company_name="Seat Co",
        email=owner,
        status=MerchantStatus.ACTIVE.value,
    )
    db.commit()
    svc = ClerkDirectoryService()
    with patch(
        "porterchain_api.admin_engine.clerk_directory_service.is_clerk_secret_configured",
        return_value=False,
    ):
        out = svc.create_user(
            db,
            _ctx(db),
            settings,
            "merchant",
            email=seat_email,
            merchant_id=merchant.id,
            role="merchant_ops",
            send_invite=False,
        )
    assert out["clerk_action"] == "seat_reserved"
    seat = get_merchant_user_by_email(db, seat_email, merchant_id=merchant.id)
    assert seat is not None


def test_invite_user_rejects_merchant(db, settings) -> None:
    svc = ClerkDirectoryService()
    with pytest.raises(ValueError, match="merchant_seats_bind"):
        svc.invite_user(db, _ctx(db), settings, "merchant", platform_user_id="x")
