"""Production config guards (DD-12)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from porterchain_api.config import Settings

_LEGACY_CLERK_PROD = {
    "_env_file": None,
    "clerk_secret_key": "sk_live_production_clerk_test_fixture",
    "clerk_publishable_key": "pk_live_production_clerk_test_fixture",
    "clerk_jwks_url": "https://clerk.example.com/.well-known/jwks.json",
    "clerk_unified_mode": True,
}


def test_jwt_secret_default_allowed_in_local() -> None:
    settings = Settings(app_env="local", jwt_secret="dev-sso-secret-change-in-production")
    assert settings.jwt_secret == "dev-sso-secret-change-in-production"


def test_jwt_secret_default_rejected_in_production() -> None:
    with pytest.raises(ValidationError, match="JWT_SECRET"):
        Settings(app_env="production", jwt_secret="dev-sso-secret-change-in-production")


def test_jwt_secret_empty_rejected_in_production() -> None:
    with pytest.raises(ValidationError, match="JWT_SECRET"):
        Settings(app_env="production", jwt_secret="")


def test_jwt_secret_custom_allowed_in_production() -> None:
    secret = "a" * 64
    settings = Settings(app_env="production", jwt_secret=secret, **_LEGACY_CLERK_PROD)
    assert settings.jwt_secret == secret


def test_fleetbase_bridge_disabled_without_secrets_in_production() -> None:
    settings = Settings(
        app_env="production",
        jwt_secret="a" * 64,
        fleetbase_dispatch_bridge=False,
        **_LEGACY_CLERK_PROD,
    )
    assert settings.fleetbase_dispatch_bridge is False


def test_fleetbase_bridge_rejected_without_secrets_in_production() -> None:
    with pytest.raises(ValidationError, match="FLEETBASE_DISPATCH_BRIDGE"):
        Settings(
            _env_file=None,
            app_env="production",
            jwt_secret="a" * 64,
            fleetbase_dispatch_bridge=True,
            fleetbase_api_key="",
            fleetbase_webhook_secret="",
            fleetbase_default_company_uuid="",
        )


def test_fleetbase_bridge_allowed_with_secrets_in_production() -> None:
    settings = Settings(
        _env_file=None,
        app_env="production",
        jwt_secret="a" * 64,
        fleetbase_dispatch_bridge=True,
        fleetbase_api_key="fb-key",
        fleetbase_webhook_secret="wh-secret",
        fleetbase_default_company_uuid="company-uuid-1",
        clerk_secret_key=_LEGACY_CLERK_PROD["clerk_secret_key"],
        clerk_jwks_url=_LEGACY_CLERK_PROD["clerk_jwks_url"],
    )
    assert settings.fleetbase_dispatch_bridge is True
