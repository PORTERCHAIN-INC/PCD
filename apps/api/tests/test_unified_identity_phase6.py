"""Phase 6 — Doppler secret matrix helpers, startup validation, config-audit."""

from __future__ import annotations

import json
import os

import pytest
from pydantic import ValidationError

from porterchain_api.auth.clerk_config_audit import (
    audit_clerk_settings,
    audit_report_dict,
    issuer_from_jwks_url,
    production_clerk_errors,
    resolve_clerk_runtime_mode,
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
        "clerk_authorized_issuers": "",
        "clerk_authorized_parties": "",
        "clerk_audience": "",
        "clerk_webhook_signing_secret": "",
    }
    base.update(overrides)
    return Settings(_env_file=None, **base)  # type: ignore[arg-type]


def _enterprise_live(**overrides: object) -> Settings:
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


def _unified_live(**overrides: object) -> Settings:
    sk = "sk_live_platform"
    pk = "pk_live_platform"
    jwks = "https://platform.clerk.accounts.dev/.well-known/jwks.json"
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


def test_issuer_from_jwks_url() -> None:
    assert (
        issuer_from_jwks_url("https://foo.clerk.accounts.dev/.well-known/jwks.json")
        == "https://foo.clerk.accounts.dev"
    )


def test_resolve_mode_enterprise_vs_unified() -> None:
    assert resolve_clerk_runtime_mode(_enterprise_live()) == "enterprise"
    assert resolve_clerk_runtime_mode(_unified_live()) == "unified"
    assert resolve_clerk_runtime_mode(_unified_live(clerk_unified_mode=False)) == "unified"


def test_audit_never_includes_secret_values() -> None:
    marker = "NEVER_LEAK_THIS_SECRET_VALUE_9f3a"
    settings = _unified_live(clerk_secret_key=f"sk_live_{marker}")
    blob = json.dumps(audit_report_dict(settings))
    assert marker not in blob
    for f in audit_clerk_settings(settings):
        assert marker not in f.name
        assert marker not in f.detail


def test_production_rejects_incomplete() -> None:
    with pytest.raises((ValueError, ValidationError)) as exc:
        _settings(app_env="production")
    assert "Clerk" in str(exc.value) or "incomplete" in str(exc.value).lower()


def test_production_rejects_test_keys() -> None:
    with pytest.raises((ValueError, ValidationError)) as exc:
        _enterprise_live(
            app_env="production",
            clerk_customer_secret_key="sk_test_cust",
            clerk_customer_publishable_key="pk_test_cust",
        )
    msg = str(exc.value)
    assert "test" in msg.lower()


def test_production_rejects_pk_sk_env_mismatch() -> None:
    with pytest.raises((ValueError, ValidationError)) as exc:
        _enterprise_live(
            app_env="production",
            clerk_admin_publishable_key="pk_live_admin",
            clerk_admin_secret_key="sk_test_admin",
        )
    assert "mismatch" in str(exc.value).lower() or "test" in str(exc.value).lower()


def test_production_accepts_enterprise_live() -> None:
    s = _enterprise_live(app_env="production")
    assert production_clerk_errors(s) == []


def test_production_accepts_unified_live() -> None:
    s = _unified_live(app_env="production")
    assert resolve_clerk_runtime_mode(s) == "unified"
    assert production_clerk_errors(s) == []


def test_production_rejects_dev_bypass() -> None:
    with pytest.raises((ValueError, ValidationError)) as exc:
        _enterprise_live(app_env="production", clerk_dev_bypass=True)
    assert "CLERK_DEV_BYPASS" in str(exc.value)


def test_issuer_allowlist_mismatch() -> None:
    with pytest.raises((ValueError, ValidationError)) as exc:
        _unified_live(
            app_env="production",
            clerk_authorized_issuers="https://other.clerk.accounts.dev",
        )
    assert "CLERK_AUTHORIZED_ISSUERS" in str(exc.value) or "mismatch" in str(exc.value).lower()
