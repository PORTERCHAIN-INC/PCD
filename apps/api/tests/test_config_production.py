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
    "clerk_unified_mode": False,
    "clerk_driver_secret_key": "sk_live_driver_clerk_test_fixture",
    "clerk_driver_jwks_url": "https://clerk-driver.example.com/.well-known/jwks.json",
    "clerk_driver_publishable_key": "pk_live_driver_clerk_test_fixture",
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




