"""Phase 5 — unified Clerk app mode: multi-role, portal visit ≠ role."""

from __future__ import annotations

import os
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from porterchain_api.auth.claims import ClerkClaims
from porterchain_api.auth.portal_guard import (
    assert_clerk_id_exclusive,
    is_unified_clerk_app,
    require_clerk_app_for_portal,
)
from porterchain_api.config import Settings

_CLERK_ENV_PREFIXES = ("CLERK_", "NEXT_PUBLIC_CLERK_")


@pytest.fixture(autouse=True)
def _clear_clerk_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in list(os.environ):
        if key.startswith(_CLERK_ENV_PREFIXES):
            monkeypatch.delenv(key, raising=False)


def _settings(**overrides: object) -> Settings:
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
        "clerk_unified_mode": False,
    }
    base.update(overrides)
    return Settings(_env_file=None, **base)  # type: ignore[arg-type]


def _unified_settings(**overrides: object) -> Settings:
    """Same sk/jwks across portal slots — mirrors pnpm clerk:sync CLERK_MODE=unified."""
    sk = "sk_platform"
    jwks = "https://platform.clerk.accounts.dev/.well-known/jwks.json"
    pk = "pk_platform"
    params: dict[str, object] = {
        "clerk_unified_mode": True,
        "clerk_secret_key": sk,
        "clerk_publishable_key": pk,
        "clerk_jwks_url": jwks,
        "clerk_customer_secret_key": sk,
        "clerk_customer_publishable_key": pk,
        "clerk_customer_jwks_url": jwks,
        "clerk_merchant_secret_key": sk,
        "clerk_merchant_publishable_key": pk,
        "clerk_merchant_jwks_url": jwks,
        "clerk_admin_secret_key": sk,
        "clerk_admin_publishable_key": pk,
        "clerk_admin_jwks_url": jwks,
        "clerk_driver_secret_key": sk,
        "clerk_driver_publishable_key": pk,
        "clerk_driver_jwks_url": jwks,
    }
    params.update(overrides)
    return _settings(**params)


def _db_membership(*, admin=False, merchant=False, driver=False, customer=False) -> MagicMock:
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


def test_is_unified_when_flag_set() -> None:
    assert is_unified_clerk_app(_settings(clerk_unified_mode=True)) is True


def test_is_unified_when_shared_portal_secrets() -> None:
    assert is_unified_clerk_app(_unified_settings(clerk_unified_mode=False)) is True


def test_require_clerk_app_is_noop_platform_only() -> None:
    """Phase D3: always no-op even if claims.clerk_app would have mismatched."""
    require_clerk_app_for_portal(
        ClerkClaims(clerk_user_id="user_abc", clerk_app="customer"),
        _unified_settings(),
        "admin",
    )
    require_clerk_app_for_portal(
        ClerkClaims(clerk_user_id="user_abc", clerk_app="customer"),
        _settings(),
        "merchant",
    )


def test_unified_allows_multi_role_same_subject_on_customer() -> None:
    """Admin + customer membership OK under unified — visit still needs provisioning elsewhere."""
    db = _db_membership(admin=True, customer=True)
    claims = ClerkClaims(clerk_user_id="user_multi")
    assert_clerk_id_exclusive(db, claims, portal="customer", settings=_unified_settings())


def test_unified_allows_multi_role_on_admin_when_provisioned() -> None:
    db = _db_membership(admin=True, customer=True)
    claims = ClerkClaims(clerk_user_id="user_multi")
    assert_clerk_id_exclusive(db, claims, portal="admin", settings=_unified_settings())


def test_unified_still_requires_admin_provisioning() -> None:
    db = _db_membership(customer=True)
    claims = ClerkClaims(clerk_user_id="user_customer_only")
    with pytest.raises(HTTPException) as exc:
        assert_clerk_id_exclusive(db, claims, portal="admin", settings=_unified_settings())
    assert exc.value.status_code == 403
    assert "admin_user_not_provisioned" in str(exc.value.detail)


def test_unified_still_requires_merchant_provisioning() -> None:
    db = _db_membership(admin=True)
    claims = ClerkClaims(clerk_user_id="user_admin")
    with pytest.raises(HTTPException) as exc:
        assert_clerk_id_exclusive(db, claims, portal="merchant", settings=_unified_settings())
    assert exc.value.status_code == 403
    assert "merchant_user_not_provisioned" in str(exc.value.detail)
