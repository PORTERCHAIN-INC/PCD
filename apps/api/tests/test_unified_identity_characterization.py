"""Characterization tests for Phase 1 Keycloak consolidation audit (Phase D3 updated).

Locks Platform / unified behavior. Enterprise 4-app exclusivity and app-mismatch
guards are retired — see docs/runbooks/keycloak-consolidation.md.

Settings helpers clear Keycloak-related process env and skip ``.env`` so local
``apps/api/.env`` does not pollute registry mode assertions.
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from porterchain_api.auth.claims import IdentityClaims
from porterchain_api.auth.identity_directory import (
    ALL_USER_KINDS,
    identity_configuration_mode,
)
from porterchain_api.auth.dev import allow_auth_dev_bypass
from porterchain_api.auth.invitation_service import InvitationService, OPEN_SIGNUP_USER_TYPES
from porterchain_api.auth.portal_guard import (
    assert_portal_provisioned,
)
from porterchain_api.config import Settings
from porterchain_api.domain.admin_states import AdminRole
from porterchain_api.domain.merchant_states import MerchantRole

_IDP_ENV_PREFIXES = ("IDP_", "NEXT_PUBLIC_IDP_")


@pytest.fixture(autouse=True)
def _clear_idp_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in list(os.environ):
        if key.startswith(_IDP_ENV_PREFIXES):
            monkeypatch.delenv(key, raising=False)


def _settings(**overrides: object) -> Settings:
    """Build Settings without reading apps/api/.env."""
    base: dict[str, object] = {
        "app_env": "local",
        "auth_dev_bypass": False,
        "jwt_secret": "a" * 32,
        "idp_secret_key": "",
        "idp_publishable_key": "",
        "idp_jwks_url": "",
        "idp_customer_secret_key": "",
        "idp_customer_publishable_key": "",
        "idp_customer_jwks_url": "",
        "idp_merchant_secret_key": "",
        "idp_merchant_publishable_key": "",
        "idp_merchant_jwks_url": "",
        "idp_admin_secret_key": "",
        "idp_admin_publishable_key": "",
        "idp_admin_jwks_url": "",
        "idp_driver_secret_key": "",
        "idp_driver_publishable_key": "",
        "idp_driver_jwks_url": "",
    }
    base.update(overrides)
    return Settings(_env_file=None, **base)  # type: ignore[arg-type]


def _unified_settings(**overrides: object) -> Settings:
    """Platform + Driver layout (name kept for call-site compat)."""
    sk = "sk_platform"
    jwks = "https://platform.keycloak.accounts.dev/.well-known/jwks.json"
    pk = "pk_platform"
    dsk = "sk_driver"
    djwks = "https://driver.keycloak.accounts.dev/.well-known/jwks.json"
    return _settings(
        idp_unified_mode=False,
        idp_secret_key=sk,
        idp_publishable_key=pk,
        idp_jwks_url=jwks,
        idp_customer_secret_key=sk,
        idp_customer_jwks_url=jwks,
        idp_customer_publishable_key=pk,
        idp_merchant_secret_key=sk,
        idp_merchant_jwks_url=jwks,
        idp_merchant_publishable_key=pk,
        idp_admin_secret_key=sk,
        idp_admin_jwks_url=jwks,
        idp_admin_publishable_key=pk,
        idp_driver_secret_key=dsk,
        idp_driver_jwks_url=djwks,
        idp_driver_publishable_key="pk_driver",
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


def test_four_idp_app_kinds_are_customer_merchant_admin_driver() -> None:
    assert ALL_USER_KINDS == ("customer", "merchant", "admin", "driver")


def test_idp_staff_invite_retired() -> None:
    """A6 — staff provision is IdP enroll only; InvitationService has no admin invite."""
    assert not hasattr(InvitationService, "invite_admin_staff")
    assert hasattr(InvitationService, "invite_driver")


# --- Dev bypass ---


def test_dev_bypass_requires_local_and_flag() -> None:
    assert allow_auth_dev_bypass(_settings(app_env="local", auth_dev_bypass=True))
    assert not allow_auth_dev_bypass(_settings(app_env="local", auth_dev_bypass=False))
    # Phase 6: Settings rejects AUTH_DEV_BYPASS outside local (startup fail-fast).
    with pytest.raises(Exception) as exc:
        _settings(app_env="production", auth_dev_bypass=True)
    assert "AUTH_DEV_BYPASS" in str(exc.value)


# --- Claims metadata (invite hint only; not authz SoT) ---


def test_metadata_role_reads_public_metadata_role_or_porterchain_role() -> None:
    assert IdentityClaims("u1", public_metadata={"role": "dispatcher"}).metadata_role == "dispatcher"
    assert IdentityClaims("u1", public_metadata={"porterchain_role": "admin"}).metadata_role == "admin"
    assert IdentityClaims("u1", public_metadata={}).metadata_role is None
    assert IdentityClaims("u1").metadata_role is None


# --- Identity (unified multi-role; provisioning still required) ---


def test_assert_allows_admin_identity_on_customer_portal() -> None:
    """Multi-role OK — customer auto-provision path does not conflict with staff."""
    db = _db_membership(admin=True)
    claims = IdentityClaims(auth_subject="user_staff")
    assert_portal_provisioned(db, claims, portal="customer", settings=_unified_settings())


def test_assert_requires_provisioned_admin() -> None:
    db = _db_membership()
    claims = IdentityClaims(auth_subject="user_unknown")
    with pytest.raises(HTTPException) as exc:
        assert_portal_provisioned(db, claims, portal="admin", settings=_unified_settings())
    assert exc.value.status_code == 403
    assert "admin_user_not_provisioned" in str(exc.value.detail)


def test_assert_allows_provisioned_admin_with_customer_membership() -> None:
    db = _db_membership(admin=True, customer=True)
    claims = IdentityClaims(auth_subject="user_admin")
    assert_portal_provisioned(db, claims, portal="admin", settings=_unified_settings())


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
