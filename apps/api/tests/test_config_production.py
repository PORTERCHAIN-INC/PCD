"""Production config guards (DD-12)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from porterchain_api.config import Settings

_LEGACY_IDP_PROD = {
    "_env_file": None,
    "keycloak_url": "https://auth.porterchain.test",
    "idp_secret_key": "sk_live_production_idp_test_fixture",
    "idp_publishable_key": "pk_live_production_idp_test_fixture",
    "idp_jwks_url": "https://keycloak.example.com/.well-known/jwks.json",
    "idp_unified_mode": False,
    "idp_driver_secret_key": "sk_live_driver_idp_test_fixture",
    "idp_driver_jwks_url": "https://keycloak-driver.example.com/.well-known/jwks.json",
    "idp_driver_publishable_key": "pk_live_driver_idp_test_fixture",
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
    settings = Settings(app_env="production", jwt_secret=secret, **_LEGACY_IDP_PROD)
    assert settings.jwt_secret == secret




