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


def test_create_customer_rejects_linked_email() -> None:
    linked = SimpleNamespace(
        id="cust-1",
        email="c@example.com",
        clerk_user_id="user_abc",
        full_name="C",
        phone=None,
    )
    db = MagicMock()
    db.query.return_value.filter.return_value.order_by.return_value.first.return_value = linked
    ctx = MagicMock()
    settings = MagicMock()
    with pytest.raises(ValueError, match="customer_email_exists"):
        CustomerAdminService().create_customer(
            db, ctx, settings, email="c@example.com", send_invite=False
        )


def test_create_customer_mints_orphan_row() -> None:
    orphan = SimpleNamespace(
        id="cust-new",
        email="new@example.com",
        clerk_user_id="pending:new@example.com",
        full_name="New User",
        phone=None,
        customer_reference="PC-1",
        stripe_customer_id=None,
        privacy_status=None,
        privacy_hold_reference=None,
        privacy_hold_at=None,
        created_at=None,
    )
    db = MagicMock()
    db.query.return_value.filter.return_value.order_by.return_value.first.return_value = None
    db.get.return_value = orphan
    ctx = MagicMock()
    settings = MagicMock()

    with (
        patch(
            "porterchain_api.admin_engine.customer_admin_mutations.ensure_retail_customer",
            return_value=orphan,
        ),
        patch(
            "porterchain_api.admin_engine.customer_admin_mutations.is_clerk_secret_configured",
            return_value=False,
        ),
        patch("porterchain_api.admin_engine.customer_admin_mutations.log_admin_audit"),
        patch.object(
            CustomerAdminService,
            "detail",
            return_value={
                "id": orphan.id,
                "email": orphan.email,
                "display_name": "New User",
                "clerk_linked": False,
                "identity_status": "orphan",
            },
        ),
    ):
        row = CustomerAdminService().create_customer(
            db,
            ctx,
            settings,
            email="new@example.com",
            full_name="New User",
            send_invite=False,
        )

    assert row["id"] == "cust-new"
    assert row["created"] is True
    assert row["clerk_action"] == "created"
    db.commit.assert_called_once()


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


def test_approve_driver_does_not_push_fleetbase() -> None:
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
    settings = MagicMock()
    ctx = SimpleNamespace(user=SimpleNamespace(id="admin-1"))

    with patch(
        "porterchain_api.admin_engine.driver_service.emit_event",
    ), patch(
        "porterchain_api.auth.authz_sync.sync_authz_after_persona_mutation",
    ):
        out, _warning = svc.approve_driver(db, ctx, "d1", settings)

    assert out.status == DriverStatus.APPROVED.value
    assert not hasattr(svc, "_fleetbase") or not getattr(svc, "_fleetbase", None)


def test_approve_driver_works_without_settings() -> None:
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
    ctx = SimpleNamespace(user=SimpleNamespace(id="admin-1"))

    with patch(
        "porterchain_api.admin_engine.driver_service.emit_event",
    ), patch(
        "porterchain_api.auth.authz_sync.sync_authz_after_persona_mutation",
    ):
        out, _warning = svc.approve_driver(db, ctx, "d1", None)

    assert out.status == DriverStatus.APPROVED.value
