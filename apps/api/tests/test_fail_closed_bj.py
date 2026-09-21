"""BJ — production with missing Clerk keys fails closed; the dev bypass never ships."""

from __future__ import annotations

import asyncio
import os

import pytest
from fastapi import HTTPException

from porterchain_api.auth.clerk import get_clerk_claims
from porterchain_api.auth.clerk_config_audit import production_clerk_errors
from porterchain_api.auth.clerk_identity_provider import verify_clerk_token
from porterchain_api.auth.dev import allow_auth_dev_bypass
from porterchain_api.config import Settings

_CLERK_ENV_PREFIXES = ("CLERK_", "NEXT_PUBLIC_CLERK_")

# Every environment name a deploy might carry. Only "local" is a developer laptop.
SERVER_ENVS = ("production", "staging", "development", "dev", "test", "prod", "")


@pytest.fixture(autouse=True)
def _clear_clerk_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """The local .env has test Clerk keys; they must not leak into these cases."""
    for key in list(os.environ):
        if key.startswith(_CLERK_ENV_PREFIXES):
            monkeypatch.delenv(key, raising=False)


def _settings(**overrides: object) -> Settings:
    base: dict[str, object] = {
        "app_env": "local",
        "clerk_dev_bypass": False,
        "jwt_secret": "b" * 48,
        "database_url": "postgresql+psycopg://u:p@h/d",
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
        "clerk_authorized_issuers": "",
        "clerk_authorized_parties": "",
        "clerk_audience": "",
        "clerk_webhook_signing_secret": "",
    }
    base.update(overrides)
    return Settings(_env_file=None, **base)  # type: ignore[arg-type]


def _live(**overrides: object) -> Settings:
    """A complete, live Clerk config — what a correct production deploy looks like."""
    params: dict[str, object] = {
        "clerk_customer_secret_key": "sk_live_cust",
        "clerk_customer_publishable_key": "pk_live_cust",
        "clerk_customer_jwks_url": "https://cust.clerk.accounts.dev/.well-known/jwks.json",
        "clerk_merchant_secret_key": "sk_live_merch",
        "clerk_merchant_publishable_key": "pk_live_merch",
        "clerk_merchant_jwks_url": "https://merch.clerk.accounts.dev/.well-known/jwks.json",
        "clerk_admin_secret_key": "sk_live_admin",
        "clerk_admin_publishable_key": "pk_live_admin",
        "clerk_admin_jwks_url": "https://admin.clerk.accounts.dev/.well-known/jwks.json",
        "clerk_driver_secret_key": "sk_live_driver",
        "clerk_driver_publishable_key": "pk_live_driver",
        "clerk_driver_jwks_url": "https://driver.clerk.accounts.dev/.well-known/jwks.json",
    }
    params.update(overrides)
    return _settings(**params)


# --- Dev bypass never ships ---


def test_bypass_needs_development_project_mode() -> None:
    """Aliases (dev/development) normalize to local → development mode can unlock bypass.
    testing (APP_ENV=test) must not.
    """
    assert allow_auth_dev_bypass(_settings(app_env="local", clerk_dev_bypass=True))
    assert allow_auth_dev_bypass(_settings(app_env="development", clerk_dev_bypass=True))
    assert allow_auth_dev_bypass(_settings(app_env="dev", clerk_dev_bypass=True))
    assert not allow_auth_dev_bypass(_settings(app_env="test", clerk_dev_bypass=True))


def test_bypass_is_off_locally_unless_asked_for() -> None:
    assert not allow_auth_dev_bypass(_settings(app_env="local", clerk_dev_bypass=False))


def test_production_refuses_to_boot_with_the_bypass_on() -> None:
    """A leaked CLERK_DEV_BYPASS is a boot failure, not a warning served to users."""
    for env in ("production", "staging", "prod"):
        with pytest.raises(Exception) as exc:
            _live(app_env=env, clerk_dev_bypass=True)
        # The message must name the variable, or nobody can fix the deploy.
        assert "CLERK_DEV_BYPASS must be false" in str(exc.value), env


def test_bearer_dev_is_refused_when_the_bypass_is_off() -> None:
    settings = _settings(app_env="local", clerk_dev_bypass=False)

    async def _run() -> None:
        from starlette.requests import Request

        scope = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": "/v1/health",
            "raw_path": b"/v1/health",
            "query_string": b"",
            "headers": [],
            "client": ("127.0.0.1", 123),
            "server": ("test", 80),
        }
        with pytest.raises(HTTPException) as exc:
            await get_clerk_claims(
                request=Request(scope),
                authorization="Bearer dev",
                settings=settings,
                db=None,
            )
        assert exc.value.status_code == 401
        assert exc.value.detail == "dev_bypass_disabled"

    asyncio.run(_run())


# --- Missing Clerk keys fail closed ---


def test_production_refuses_to_boot_without_clerk() -> None:
    for env in ("production", "staging"):
        with pytest.raises(Exception) as exc:
            _settings(app_env=env)
        assert "Clerk incomplete" in str(exc.value), env


def test_a_complete_live_config_boots() -> None:
    """The guard must not block a correctly configured production deploy."""
    assert production_clerk_errors(_live(app_env="production")) == []


def test_test_keys_are_refused_in_production() -> None:
    with pytest.raises(Exception) as exc:
        _live(
            app_env="production",
            clerk_merchant_secret_key="sk_test_merch",
            clerk_merchant_publishable_key="pk_test_merch",
        )
    assert "test key" in str(exc.value).lower()


def test_a_token_cannot_be_verified_without_clerk_keys() -> None:
    """No JWKS means 503 — never a trusted claim set, never a pass-through."""
    settings = _settings(app_env="development", clerk_dev_bypass=True)

    async def _run() -> None:
        with pytest.raises(HTTPException) as exc:
            await verify_clerk_token("eyJhbGciOiJSUzI1NiJ9.e30.sig", settings)
        assert exc.value.status_code == 503
        assert exc.value.detail == "clerk_not_configured"

    asyncio.run(_run())


def test_missing_bearer_is_refused_not_waved_through() -> None:
    settings = _live(app_env="production")

    async def _run() -> None:
        from starlette.requests import Request

        scope = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": "/v1/health",
            "raw_path": b"/v1/health",
            "query_string": b"",
            "headers": [],
            "client": ("127.0.0.1", 123),
            "server": ("test", 80),
        }
        with pytest.raises(HTTPException) as exc:
            await get_clerk_claims(
                request=Request(scope),
                authorization=None,
                settings=settings,
                db=None,
            )
        assert exc.value.status_code == 401
        assert exc.value.detail == "missing_bearer_token"

    asyncio.run(_run())


def test_stripe_mock_never_opens_outside_development() -> None:
    """Same shape of guard: a mock payment door must not exist outside development mode."""
    assert _settings(app_env="local", stripe_mock=True).allow_stripe_mock is True
    assert _live(app_env="production", stripe_mock=True).allow_stripe_mock is False
    assert _settings(app_env="test", stripe_mock=True).allow_stripe_mock is False
