"""Characterization tests for Phase 1 Clerk consolidation audit (Phase D3 updated).

Locks Platform / unified behavior. Enterprise 4-app exclusivity and app-mismatch
guards are retired — see docs/runbooks/clerk-consolidation.md.

Settings helpers clear Clerk-related process env and skip ``.env`` so local
``apps/api/.env`` does not pollute registry mode assertions.
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from porterchain_api.auth.claims import ClerkClaims
from porterchain_api.auth.clerk_registry import (
    ALL_CLERK_APP_KINDS,
    clerk_app_configs,
    clerk_configuration_mode,
)
from porterchain_api.auth.dev import allow_auth_dev_bypass
from porterchain_api.auth.invitation_service import InvitationService, OPEN_SIGNUP_USER_TYPES
from porterchain_api.auth.portal_guard import (
    assert_clerk_id_exclusive,
    is_legacy_shared_clerk_app,
    is_unified_clerk_app,
)
from porterchain_api.config import Settings
from porterchain_api.domain.admin_states import AdminRole
from porterchain_api.domain.merchant_states import MerchantRole

_CLERK_ENV_PREFIXES = ("CLERK_", "NEXT_PUBLIC_CLERK_")


@pytest.fixture(autouse=True)
def _clear_clerk_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in list(os.environ):
        if key.startswith(_CLERK_ENV_PREFIXES):
            monkeypatch.delenv(key, raising=False)


def _settings(**overrides: object) -> Settings:
    """Build Settings without reading apps/api/.env."""
    base: dict[str, object] = {
        "app_env": "local",
        "clerk_dev_bypass": False,
        "jwt_secret": "a" * 32,
        "clerk_secret_key": "",
        "clerk_publishable_key": "",
        "clerk_jwks_url": "",
        "clerk_customer_secret_key": "",
        "clerk_customer_publishable_key": "",
        "clerk_customer_jwks_url": "",
        "clerk_merchant_secret_key": "",
        "clerk_merchant_publishable_key": "",
        "clerk_merchant_jwks_url": "",
        "clerk_admin_secret_key": "",
        "clerk_admin_publishable_key": "",
        "clerk_admin_jwks_url": "",
        "clerk_driver_secret_key": "",
        "clerk_driver_publishable_key": "",
        "clerk_driver_jwks_url": "",
    }
    base.update(overrides)
    return Settings(_env_file=None, **base)  # type: ignore[arg-type]


def _unified_settings(**overrides: object) -> Settings:
    """Platform + Driver layout (name kept for call-site compat)."""
    sk = "sk_platform"
    jwks = "https://platform.clerk.accounts.dev/.well-known/jwks.json"
    pk = "pk_platform"
    dsk = "sk_driver"
    djwks = "https://driver.clerk.accounts.dev/.well-known/jwks.json"
    return _settings(
        clerk_unified_mode=False,
        clerk_secret_key=sk,
        clerk_publishable_key=pk,
        clerk_jwks_url=jwks,
        clerk_customer_secret_key=sk,
        clerk_customer_jwks_url=jwks,
        clerk_customer_publishable_key=pk,
        clerk_merchant_secret_key=sk,
        clerk_merchant_jwks_url=jwks,
        clerk_merchant_publishable_key=pk,
        clerk_admin_secret_key=sk,
        clerk_admin_jwks_url=jwks,
        clerk_admin_publishable_key=pk,
        clerk_driver_secret_key=dsk,
        clerk_driver_jwks_url=djwks,
        clerk_driver_publishable_key="pk_driver",
        **overrides,
    )


def _db_membership(*, admin=False, merchant=False, driver=False, customer=False) -> MagicMock:
    """Session mock: AdminUser / MerchantUser / Driver / Customer queries in call order."""

    def _first_for(flag: bool):
        return MagicMock() if flag else None

    results = [
        _first_for(admin),
        _first_for(merchant),
        _first_for(driver),
        _first_for(customer),
    ]
    db = MagicMock()
    chain = db.query.return_value.filter.return_value
    chain.first.side_effect = results
    return db


# --- Registry / env topology ---


def test_four_clerk_app_kinds_are_customer_merchant_admin_driver() -> None:
    assert ALL_CLERK_APP_KINDS == ("customer", "merchant", "admin", "driver")


def test_clerk_staff_invite_retired() -> None:
    """A6 — staff provision is IdP enroll only; InvitationService has no admin invite."""
    assert not hasattr(InvitationService, "invite_admin_staff")
    assert hasattr(InvitationService, "invite_driver")


def test_platform_driver_mode_keeps_distinct_driver() -> None:
    settings = _unified_settings()
    assert clerk_configuration_mode(settings) == "platform_driver"
    assert not is_unified_clerk_app(settings)
    apps = clerk_app_configs(settings)
    assert len(apps) == 4
    assert len({a.secret_key for a in apps}) == 2


def test_legacy_shared_secret_marks_legacy_shared_clerk_app() -> None:
    settings = _settings(
        clerk_secret_key="sk_shared",
        clerk_jwks_url="https://shared.clerk.accounts.dev/.well-known/jwks.json",
        clerk_publishable_key="pk_shared",
    )
    assert clerk_configuration_mode(settings) == "legacy"
    assert is_legacy_shared_clerk_app(settings)


# --- Dev bypass ---


def test_dev_bypass_requires_local_and_flag() -> None:
    assert allow_auth_dev_bypass(_settings(app_env="local", clerk_dev_bypass=True))
    assert not allow_auth_dev_bypass(_settings(app_env="local", clerk_dev_bypass=False))
    # Phase 6: Settings rejects CLERK_DEV_BYPASS outside local (startup fail-fast).
    with pytest.raises(Exception) as exc:
        _settings(app_env="production", clerk_dev_bypass=True)
    assert "CLERK_DEV_BYPASS" in str(exc.value)


# --- Claims metadata (invite hint only; not authz SoT) ---


def test_metadata_role_reads_public_metadata_role_or_porterchain_role() -> None:
    assert ClerkClaims("u1", public_metadata={"role": "dispatcher"}).metadata_role == "dispatcher"
    assert ClerkClaims("u1", public_metadata={"porterchain_role": "admin"}).metadata_role == "admin"
    assert ClerkClaims("u1", public_metadata={}).metadata_role is None
    assert ClerkClaims("u1").metadata_role is None


# --- Identity (unified multi-role; provisioning still required) ---


def test_assert_allows_admin_identity_on_customer_portal() -> None:
    """Multi-role OK — customer auto-provision path does not conflict with staff."""
    db = _db_membership(admin=True)
    claims = ClerkClaims(clerk_user_id="user_staff")
    assert_clerk_id_exclusive(db, claims, portal="customer", settings=_unified_settings())


def test_assert_requires_provisioned_admin() -> None:
    db = _db_membership()
    claims = ClerkClaims(clerk_user_id="user_unknown")
    with pytest.raises(HTTPException) as exc:
        assert_clerk_id_exclusive(db, claims, portal="admin", settings=_unified_settings())
    assert exc.value.status_code == 403
    assert "admin_user_not_provisioned" in str(exc.value.detail)


def test_assert_allows_provisioned_admin_with_customer_membership() -> None:
    db = _db_membership(admin=True, customer=True)
    claims = ClerkClaims(clerk_user_id="user_admin")
    assert_clerk_id_exclusive(db, claims, portal="admin", settings=_unified_settings())


def test_open_signup_is_customer_only() -> None:
    assert OPEN_SIGNUP_USER_TYPES == frozenset({"customer", "merchant"})
    assert "admin" not in OPEN_SIGNUP_USER_TYPES
    assert "driver" not in OPEN_SIGNUP_USER_TYPES


# --- Role enums present today (SoT for authz matrices) ---


def test_admin_role_enum_values_locked() -> None:
    assert {r.value for r in AdminRole} == {
        "super_admin",
        "admin",
        "dispatcher",
        "support",
        "support_lead",
        "sales",
        "sales_manager",
        "finance",
        "compliance",
        "developer",
        "marketing",
        "read_only",
        "fleet_manager",
    }


def test_merchant_role_enum_values_locked() -> None:
    assert {r.value for r in MerchantRole} == {
        "merchant_owner",
        "merchant_admin",
        "merchant_ops",
        "merchant_finance",
        "merchant_readonly",
    }
