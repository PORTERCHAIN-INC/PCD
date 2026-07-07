"""Fail-fast startup config validation (Doppler-managed secrets)."""

from __future__ import annotations

import pytest

from porterchain_api.config import Settings
from porterchain_api.startup_checks import (
    MissingConfigError,
    collect_missing_required,
    validate_required_settings,
)

_PROD_CLERK = {
    "clerk_secret_key": "sk_test_ci",
    "clerk_jwks_url": "https://clerk.example.test/.well-known/jwks.json",
}


def _prod_settings(**overrides) -> Settings:
    base = dict(
        _env_file=None,
        app_env="production",
        jwt_secret="a" * 64,
        database_url="postgresql+psycopg://user:pass@db.internal:5432/porterchain",
        stripe_secret="sk_live_x",
        stripe_webhook_secret="whsec_x",
        **_PROD_CLERK,
    )
    base.update(overrides)
    return Settings(**base)


def test_local_env_is_noop() -> None:
    settings = Settings(_env_file=None, app_env="local")
    assert collect_missing_required(settings) == []
    validate_required_settings(settings)  # must not raise


def test_fully_configured_production_passes() -> None:
    settings = _prod_settings()
    assert collect_missing_required(settings) == []
    validate_required_settings(settings)  # must not raise


def test_missing_stripe_reported() -> None:
    settings = _prod_settings(stripe_secret="", stripe_webhook_secret="")
    missing = collect_missing_required(settings)
    assert "STRIPE_SECRET" in missing
    assert "STRIPE_WEBHOOK_SECRET" in missing
    with pytest.raises(MissingConfigError) as exc:
        validate_required_settings(settings)
    assert "STRIPE_SECRET" in str(exc.value)


def test_local_default_database_url_rejected_in_production() -> None:
    settings = _prod_settings(
        database_url="postgresql+psycopg://porterchain:porterchain@localhost:5432/porterchain"
    )
    assert "DATABASE_URL" in collect_missing_required(settings)


def test_error_message_aggregates_all_missing() -> None:
    settings = _prod_settings(stripe_secret="", stripe_webhook_secret="")
    with pytest.raises(MissingConfigError) as exc:
        validate_required_settings(settings)
    message = str(exc.value)
    # Aggregated, human-readable, and points to the Doppler audit doc.
    assert "production" in message
    assert "Doppler" in message
