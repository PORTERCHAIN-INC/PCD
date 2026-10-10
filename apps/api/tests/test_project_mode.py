"""Project mode / runtime posture — boot-time APP_ENV SoT."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from porterchain_api.auth.dev import allow_auth_dev_bypass
from porterchain_api.config import Settings
from porterchain_api.routers.admin.settings import settings_project_mode_change
from porterchain_shared.config.project_mode import (
    ProjectMode,
    normalize_app_env,
    project_mode_for_app_env,
    runtime_posture,
)


def _settings(**overrides: object) -> Settings:
    base: dict[str, object] = {
        "app_env": "local",
        "clerk_dev_bypass": False,
        "jwt_secret": "b" * 48,
        "database_url": "postgresql+psycopg://u:p@h/d",
        "stripe_mock": True,
        "stripe_secret": "",
        "clerk_unified_mode": False,
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


def _live(**overrides: object) -> Settings:
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


def test_normalize_app_env_aliases() -> None:
    assert normalize_app_env("dev") == "local"
    assert normalize_app_env("development") == "local"
    assert normalize_app_env("local") == "local"
    assert normalize_app_env("test") == "test"
    assert normalize_app_env("production") == "production"
    assert normalize_app_env("prod") == "production"
    assert normalize_app_env("staging") == "staging"
    assert normalize_app_env("") == "production"


def test_settings_normalizes_development_alias() -> None:
    s = _settings(app_env="development")
    assert s.app_env == "local"
    assert s.runtime_posture["mode"] == "development"


def test_project_modes() -> None:
    assert project_mode_for_app_env("local") is ProjectMode.DEVELOPMENT
    assert project_mode_for_app_env("test") is ProjectMode.TESTING
    assert project_mode_for_app_env("staging") is ProjectMode.PRODUCTION
    assert project_mode_for_app_env("production") is ProjectMode.PRODUCTION


def test_bypass_only_in_development_mode() -> None:
    assert allow_auth_dev_bypass(_settings(app_env="local", clerk_dev_bypass=True))
    assert allow_auth_dev_bypass(_settings(app_env="dev", clerk_dev_bypass=True))
    assert not allow_auth_dev_bypass(_settings(app_env="test", clerk_dev_bypass=True))
    assert not allow_auth_dev_bypass(_live(app_env="production", clerk_dev_bypass=False))


def test_stripe_mock_only_in_development() -> None:
    assert _settings(app_env="local", stripe_mock=True).allow_stripe_mock is True
    assert _settings(app_env="test", stripe_mock=True).allow_stripe_mock is False
    posture = runtime_posture(app_env="production", stripe_mock=True, stripe_secret="")
    assert posture.stripe_mock_allowed is False
    assert _live(app_env="production", stripe_mock=True).allow_stripe_mock is False


def test_runtime_posture_payload_shape() -> None:
    p = _settings(app_env="local", clerk_dev_bypass=True).runtime_posture
    assert p["mode"] == "development"
    assert p["app_env"] == "local"
    assert p["auth_bypass_allowed"] is True
    assert p["restart_required_to_change"] is True
    assert "change_control" in p


def test_project_mode_change_endpoint_immutable() -> None:
    from unittest.mock import patch

    ctx = MagicMock()
    settings = _settings(app_env="local")
    with patch("porterchain_api.routers.admin.settings.require_module"):
        with pytest.raises(HTTPException) as exc:
            settings_project_mode_change(ctx, settings)
    assert exc.value.status_code == 403
    detail = exc.value.detail
    assert isinstance(detail, dict)
    assert detail["code"] == "project_mode_immutable"


def test_project_mode_change_immutable_in_production() -> None:
    from unittest.mock import patch

    ctx = MagicMock()
    settings = _live(app_env="production")
    with patch("porterchain_api.routers.admin.settings.require_module"):
        with pytest.raises(HTTPException) as exc:
            settings_project_mode_change(ctx, settings)
    assert exc.value.status_code == 403
    assert exc.value.detail["code"] == "project_mode_immutable"
