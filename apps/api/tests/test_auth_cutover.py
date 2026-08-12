"""Auth cutover guards — platform_driver, staff IdP, seats, retail self-signup."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from porterchain_api.admin_engine.platform_user_authorize import authorize_platform_user
from porterchain_api.admin_engine.rbac import MODULE_PERMISSIONS, permissions_catalog
from porterchain_api.auth.admin import get_admin_context
from porterchain_api.auth.clerk_config_audit import audit_clerk_settings, resolve_clerk_runtime_mode
from porterchain_api.auth.staff_session import (
    STAFF_BEARER_PREFIX,
    bearer_token_for_session,
    session_id_from_authorization,
)
from porterchain_api.config import Settings
from porterchain_api.domain.admin_states import AdminRole
from porterchain_api.merchant_engine.rbac import permissions_catalog as merchant_permissions_catalog


def test_admin_permissions_catalog_covers_all_roles() -> None:
    catalog = permissions_catalog()
    role_values = {r["role"] for r in catalog["roles"]}
    assert role_values == {r.value for r in AdminRole}
    assert len(catalog["modules"]) == len(MODULE_PERMISSIONS)
    super_admin = next(r for r in catalog["roles"] if r["role"] == "super_admin")
    assert "settings" in super_admin["modules"]
    read_only = next(r for r in catalog["roles"] if r["role"] == "read_only")
    assert "settings" not in read_only["modules"]


def test_merchant_permissions_catalog_has_five_product_roles() -> None:
    catalog = merchant_permissions_catalog()
    roles = {r["role"] for r in catalog["roles"]}
    assert roles >= {
        "merchant_owner",
        "merchant_admin",
        "merchant_ops",
        "merchant_finance",
        "merchant_readonly",
    }


def test_authorize_customer_raises_self_signup_only() -> None:
    with pytest.raises(ValueError, match="customer_self_signup_only"):
        authorize_platform_user(
            MagicMock(),
            MagicMock(),
            MagicMock(),
            "customer",
            email="c@example.com",
        )


def test_get_customer_context_deleted() -> None:
    import porterchain_api.auth.customer as customer_mod

    assert not hasattr(customer_mod, "get_customer_context")
    assert not hasattr(customer_mod, "CustomerContext")
    assert hasattr(customer_mod, "require_customer")


def test_staff_bearer_helpers() -> None:
    assert session_id_from_authorization("Bearer staff_sess_abc123") == "abc123"
    assert session_id_from_authorization("Bearer eyJhbGciOi...") is None
    assert bearer_token_for_session("xyz") == f"{STAFF_BEARER_PREFIX}xyz"


def test_get_admin_context_rejects_clerk_jwt() -> None:
    async def _run() -> None:
        request = MagicMock()
        request.cookies = {}
        with pytest.raises(HTTPException) as exc:
            await get_admin_context(
                request,
                authorization="Bearer eyJhbGciOiJSUzI1NiJ9.fake.sig",
                db=MagicMock(),
                settings=Settings(app_env="local", clerk_dev_bypass=False),
                x_admin_role=None,
            )
        assert exc.value.status_code == 401
        assert exc.value.detail == "admin_clerk_retired_use_staff_idp"

    asyncio.run(_run())


def test_notification_principal_accepts_staff_session() -> None:
    from porterchain_api.admin_models import AdminUser
    from porterchain_api.auth.staff_session import StaffSession
    from porterchain_api.notification_engine.principal import (
        _resolve_staff_notification_user,
        get_notification_user,
        resolve_notification_ws_user,
    )

    admin = AdminUser(
        id="admin-n1",
        email="ops@porterchain.com",
        name="Ops",
        role=AdminRole.SUPER_ADMIN.value,
        is_active=True,
    )
    session = StaffSession(
        session_id="notif-sid",
        admin_user_id="admin-n1",
        email="ops@porterchain.com",
        role="super_admin",
        created_at=0,
        expires_at=9e9,
    )
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = admin

    with patch(
        "porterchain_api.notification_engine.principal.get_session",
        return_value=session,
    ):
        resolved = _resolve_staff_notification_user(db, "staff_sess_notif-sid")
        assert resolved is not None
        assert resolved.user_role == "admin"
        assert resolved.user_id == "admin-n1"

        async def _http() -> None:
            creds = MagicMock()
            creds.credentials = "staff_sess_notif-sid"
            user = await get_notification_user(
                db=db,
                settings=Settings(app_env="local", clerk_dev_bypass=False),
                credentials=creds,
                x_merchant_org_id=None,
            )
            assert user.user_role == "admin"
            assert user.user_id == "admin-n1"

        asyncio.run(_http())

        async def _ws() -> None:
            with patch("porterchain_api.db.SessionLocal", return_value=db):
                user = await resolve_notification_ws_user("staff_sess_notif-sid")
                assert user is not None
                assert user.user_role == "admin"
                assert user.user_id == "admin-n1"

        asyncio.run(_ws())


def test_get_admin_context_accepts_staff_session() -> None:
    from porterchain_api.auth.staff_session import StaffSession
    from porterchain_api.admin_models import AdminUser

    async def _run() -> None:
        request = MagicMock()
        request.cookies = {}
        admin = AdminUser(
            id="admin-1",
            email="ops@porterchain.com",
            name="Ops",
            role=AdminRole.ADMIN.value,
            is_active=True,
        )
        session = StaffSession(
            session_id="sid1",
            admin_user_id="admin-1",
            email="ops@porterchain.com",
            role="admin",
            created_at=0,
            expires_at=9e9,
        )
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = admin
        settings = Settings(app_env="local", clerk_dev_bypass=False, spicedb_enabled=False)

        with (
            patch("porterchain_api.auth.admin.get_session", return_value=session),
            patch("porterchain_api.auth.admin._finish_admin_context") as finish,
        ):
            finish.return_value = MagicMock()
            await get_admin_context(
                request,
                authorization="Bearer staff_sess_sid1",
                db=db,
                settings=settings,
                x_admin_role=None,
            )
            finish.assert_called_once()

    asyncio.run(_run())


def test_clerk_audit_platform_driver_secret_matrix() -> None:
    settings = Settings(
        app_env="local",
        clerk_unified_mode=False,
        clerk_publishable_key="pk_test_platform",
        clerk_secret_key="sk_test_platform",
        clerk_jwks_url="https://platform.clerk.accounts.dev/.well-known/jwks.json",
        clerk_customer_publishable_key="pk_test_platform",
        clerk_customer_secret_key="sk_test_platform",
        clerk_customer_jwks_url="https://platform.clerk.accounts.dev/.well-known/jwks.json",
        clerk_merchant_publishable_key="pk_test_platform",
        clerk_merchant_secret_key="sk_test_platform",
        clerk_merchant_jwks_url="https://platform.clerk.accounts.dev/.well-known/jwks.json",
        clerk_admin_publishable_key="pk_test_platform",
        clerk_admin_secret_key="sk_test_platform",
        clerk_admin_jwks_url="https://platform.clerk.accounts.dev/.well-known/jwks.json",
        clerk_driver_publishable_key="pk_test_driver",
        clerk_driver_secret_key="sk_test_driver",
        clerk_driver_jwks_url="https://driver.clerk.accounts.dev/.well-known/jwks.json",
    )
    assert resolve_clerk_runtime_mode(settings) == "platform_driver"
    findings = {f.name: f for f in audit_clerk_settings(settings)}
    assert findings["CLERK_CONFIGURATION_MODE"].detail == "platform_driver"
    assert findings["SECRET_ACCESS_MATRIX"].status == "info"
    assert "staff IdP" in findings["SECRET_ACCESS_MATRIX"].detail
    assert "CLERK_MODE_RETIRED" not in findings


def test_invite_admin_staff_and_merchant_invite_deleted() -> None:
    from porterchain_api.auth.invitation_service import InvitationService

    assert not hasattr(InvitationService, "invite_admin_staff")
    assert not hasattr(InvitationService, "invite_merchant_owner")
    assert not hasattr(InvitationService, "invite_merchant_member")


def test_ensure_staff_identity_prefers_existing_staff_subject(db) -> None:
    """Dev bypass / rebind must not UniqueViolation when staff:{id} already exists."""
    from uuid import uuid4

    from porterchain_api.admin_engine.staff_idp_service import ensure_staff_identity
    from porterchain_api.admin_models import AdminUser
    from porterchain_api.user_models import PorterchainUser

    suffix = uuid4().hex[:8]
    admin = AdminUser(
        email=f"dev-ops-{suffix}@porterchain.com",
        name="Dev Ops",
        role="admin",
        is_active=True,
        clerk_user_id=f"dev_clerk_user_{suffix}",
    )
    db.add(admin)
    db.flush()

    staff_pc = PorterchainUser(
        clerk_user_id=f"staff:{admin.id}",
        email=admin.email,
        role="admin",
        status="active",
        default_workspace="admin",
    )
    legacy_pc = PorterchainUser(
        clerk_user_id=f"legacy_clerk_{suffix}",
        email=admin.email,
        role="unprovisioned",
        status="active",
    )
    db.add_all([staff_pc, legacy_pc])
    db.flush()
    admin.porterchain_user_id = legacy_pc.id
    db.commit()

    bound = ensure_staff_identity(db, admin)
    db.refresh(admin)
    assert bound == staff_pc.id
    assert admin.porterchain_user_id == staff_pc.id
    assert admin.clerk_user_id == f"staff:{admin.id}"
