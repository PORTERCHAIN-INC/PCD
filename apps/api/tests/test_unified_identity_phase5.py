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
    """Platform slots share issuer; Driver distinct — platform_driver layout."""
    sk = "sk_platform"
    jwks = "https://platform.clerk.accounts.dev/.well-known/jwks.json"
    pk = "pk_platform"
    params: dict[str, object] = {
        "clerk_unified_mode": False,
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
        "clerk_driver_secret_key": "sk_driver",
        "clerk_driver_publishable_key": "pk_driver",
        "clerk_driver_jwks_url": "https://driver.clerk.accounts.dev/.well-known/jwks.json",
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


def test_unified_flag_rejected_by_settings() -> None:
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError, match="CLERK_UNIFIED_MODE"):
        _settings(clerk_unified_mode=True)


def test_is_unified_when_all_slots_share_secrets() -> None:
    """Local DEV collapse (Driver == Platform) still reports shared issuer."""
    sk = "sk_platform"
    jwks = "https://platform.clerk.accounts.dev/.well-known/jwks.json"
    pk = "pk_platform"
    assert (
        is_unified_clerk_app(
            _settings(
                clerk_customer_secret_key=sk,
                clerk_customer_jwks_url=jwks,
                clerk_customer_publishable_key=pk,
                clerk_merchant_secret_key=sk,
                clerk_merchant_jwks_url=jwks,
                clerk_merchant_publishable_key=pk,
                clerk_admin_secret_key=sk,
                clerk_admin_jwks_url=jwks,
                clerk_admin_publishable_key=pk,
                clerk_driver_secret_key=sk,
                clerk_driver_jwks_url=jwks,
                clerk_driver_publishable_key=pk,
            )
        )
        is True
    )


def test_platform_driver_is_not_single_issuer() -> None:
    assert is_unified_clerk_app(_unified_settings()) is False


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
