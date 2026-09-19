"""Wave 2 customer admin + identity integrity tests."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from porterchain_api.admin_engine.customer_admin_service import CustomerAdminService
from porterchain_api.admin_engine.rbac import MODULE_PERMISSIONS
from porterchain_api.auth.email_identity import EMAIL_CLERK_MISMATCH
from porterchain_api.booking_engine.customer_service import CustomerService


def test_customers_modules_in_rbac() -> None:
    assert "customers" in MODULE_PERMISSIONS
    assert "customers_read" in MODULE_PERMISSIONS
    assert MODULE_PERMISSIONS["customers_read"] >= MODULE_PERMISSIONS["customers"]


def test_customer_admin_detail_missing() -> None:
    db = MagicMock()
    db.get.return_value = None
    with pytest.raises(LookupError, match="customer_not_found"):
        CustomerAdminService().detail(db, "missing")


def test_upsert_rejects_email_mismatch_on_bound_customer() -> None:
    existing = SimpleNamespace(
        id="c1",
        clerk_user_id="user_1",
        email="a@example.com",
        phone=None,
        visitor_session_id=None,
    )
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = existing
    with patch(
        "porterchain_api.auth.portal_guard.clerk_id_staff_portal",
        return_value=None,
    ), patch(
        "porterchain_api.auth.authz_sync.sync_authz_after_persona_mutation",
    ):
        with pytest.raises(ValueError, match=EMAIL_CLERK_MISMATCH):
            CustomerService().upsert(
                db,
                clerk_user_id="user_1",
                email="other@example.com",
                phone=None,
            )


def test_upsert_merges_orphan_by_email() -> None:
    orphan = SimpleNamespace(
        id="c-orphan",
        clerk_user_id="pending:old@example.com",
        email="old@example.com",
        phone=None,
        visitor_session_id=None,
        full_name=None,
    )
    db = MagicMock()
    # First query: by clerk_user_id → None; second: by email → orphan
    db.query.return_value.filter.return_value.first.side_effect = [None]
    db.query.return_value.filter.return_value.order_by.return_value.first.return_value = orphan

    with patch(
        "porterchain_api.auth.portal_guard.clerk_id_staff_portal",
        return_value=None,
    ), patch(
        "porterchain_api.auth.authz_sync.sync_authz_after_persona_mutation",
    ), patch(
        "porterchain_api.booking_engine.customer_service.emit_event",
    ):
        out = CustomerService().upsert(
            db,
            clerk_user_id="user_new",
            email="OLD@example.com",
            phone="+14165550100",
        )
    assert out is orphan
    assert orphan.clerk_user_id == "user_new"
    assert orphan.email == "old@example.com"
    assert orphan.phone == "+14165550100"


def test_approve_driver_pushes_fleetbase_when_settings_present() -> None:
    from porterchain_api.admin_engine.driver_service import AdminDriverService
    from porterchain_api.domain.admin_states import DriverStatus

    driver = SimpleNamespace(
        id="d1",
        status=DriverStatus.PENDING.value,
        clerk_user_id="user_d",
        vehicles=[],
        fleetbase_driver_id=None,
    )
    db = MagicMock()
    svc = AdminDriverService()
    svc._get_or_raise = MagicMock(return_value=driver)  # type: ignore[method-assign]
    svc._audit = MagicMock()  # type: ignore[method-assign]
    svc._fleetbase = MagicMock()
    settings = MagicMock()
    ctx = SimpleNamespace(user=SimpleNamespace(id="admin-1"))

    with patch(
        "porterchain_api.admin_engine.driver_service.emit_event",
    ), patch(
        "porterchain_api.auth.authz_sync.sync_authz_after_persona_mutation",
    ):
        out = svc.approve_driver(db, ctx, "d1", settings)

    assert out.status == DriverStatus.APPROVED.value
    svc._fleetbase.push_driver.assert_called_once_with(db, settings, driver)


def test_approve_driver_skips_fleetbase_without_settings() -> None:
    from porterchain_api.admin_engine.driver_service import AdminDriverService
    from porterchain_api.domain.admin_states import DriverStatus

    driver = SimpleNamespace(
        id="d1",
        status=DriverStatus.PENDING.value,
        clerk_user_id="user_d",
        vehicles=[],
        fleetbase_driver_id=None,
    )
    db = MagicMock()
    svc = AdminDriverService()
    svc._get_or_raise = MagicMock(return_value=driver)  # type: ignore[method-assign]
    svc._audit = MagicMock()  # type: ignore[method-assign]
    svc._fleetbase = MagicMock()
    ctx = SimpleNamespace(user=SimpleNamespace(id="admin-1"))

    with patch(
        "porterchain_api.admin_engine.driver_service.emit_event",
    ), patch(
        "porterchain_api.auth.authz_sync.sync_authz_after_persona_mutation",
    ):
        svc.approve_driver(db, ctx, "d1", None)

    svc._fleetbase.push_driver.assert_not_called()
