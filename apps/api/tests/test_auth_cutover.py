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


def test_architecture_census_staff_not_clerk() -> None:
    from pathlib import Path

    text = Path(__file__).resolve().parents[3].joinpath("ARCHITECTURE.md").read_text()
    assert "Keycloak `pc-admin`" in text
    assert "| Staff | `/v1/admin` | Clerk staff |" not in text


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

    from porterchain_api.admin_engine.staff_accounts import ensure_staff_identity
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


def test_auth_sli_prometheus_lines() -> None:
    from porterchain_api.auth.sli_metrics import (
        auth_events_snapshot,
        note_auth_event,
        prometheus_auth_lines,
        reset_auth_events_for_tests,
    )

    reset_auth_events_for_tests()
    note_auth_event("staff_login_passkey", "ok")
    note_auth_event("staff_step_up_check", "required")
    text = "\n".join(prometheus_auth_lines())
    assert "porterchain_auth_events_total" in text
    assert 'kind="staff_login_passkey"' in text
    assert 'result="ok"' in text
    snap = auth_events_snapshot()
    assert snap["staff_login_passkey"]["ok"] == 1
    assert snap["staff_step_up_check"]["required"] == 1
    reset_auth_events_for_tests()


def test_enforce_staff_step_up_dev_bypass() -> None:
    from unittest.mock import MagicMock

    from porterchain_api.auth.staff_step_up import enforce_staff_step_up

    req = MagicMock()
    req.cookies = {}
    settings = Settings(app_env="local", clerk_dev_bypass=True)
    # Should not raise for Bearer dev
    enforce_staff_step_up(req, "Bearer dev", settings)
