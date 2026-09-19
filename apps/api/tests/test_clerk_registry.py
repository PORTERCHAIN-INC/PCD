"""Clerk per-portal registry (§0.5).

Isolates from local ``apps/api/.env`` and process ``CLERK_*`` env vars.
"""

from __future__ import annotations

import os

import pytest

from porterchain_api.auth.clerk_registry import (
    ALL_CLERK_APP_KINDS,
    clerk_app_configs,
    clerk_configuration_mode,
    clerk_jwks_urls,
    is_enterprise_clerk_configured,
)
from porterchain_api.config import Settings


@pytest.fixture(autouse=True)
def _clear_clerk_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in list(os.environ):
        if key.startswith("CLERK_"):
            monkeypatch.delenv(key, raising=False)


def test_legacy_clerk_expands_to_all_portals() -> None:
    settings = Settings(
        _env_file=None,
        clerk_secret_key="sk_test_legacy",
        clerk_jwks_url="https://legacy.clerk.accounts.dev/.well-known/jwks.json",
        clerk_publishable_key="pk_test_legacy",
        clerk_customer_secret_key="",
        clerk_customer_jwks_url="",
        clerk_merchant_secret_key="",
        clerk_merchant_jwks_url="",
        clerk_admin_secret_key="",
        clerk_admin_jwks_url="",
        clerk_driver_secret_key="",
        clerk_driver_jwks_url="",
        jwt_secret="a" * 32,
    )
    apps = clerk_app_configs(settings)
    assert len(apps) == len(ALL_CLERK_APP_KINDS)
    assert clerk_configuration_mode(settings) == "legacy"
    assert not is_enterprise_clerk_configured(settings)
    kinds, urls = zip(*clerk_jwks_urls(settings), strict=True)
    assert len(kinds) == 1
    assert len(set(urls)) == 1


def test_enterprise_clerk_per_portal() -> None:
    settings = Settings(
        _env_file=None,
        clerk_customer_secret_key="sk_cust",
        clerk_customer_jwks_url="https://cust.clerk.accounts.dev/.well-known/jwks.json",
        clerk_merchant_secret_key="sk_merch",
        clerk_merchant_jwks_url="https://merch.clerk.accounts.dev/.well-known/jwks.json",
        clerk_admin_secret_key="sk_admin",
        clerk_admin_jwks_url="https://admin.clerk.accounts.dev/.well-known/jwks.json",
        clerk_driver_secret_key="sk_driver",
        clerk_driver_jwks_url="https://driver.clerk.accounts.dev/.well-known/jwks.json",
        jwt_secret="a" * 32,
    )
    assert clerk_configuration_mode(settings) == "enterprise"
    assert is_enterprise_clerk_configured(settings)
    urls = clerk_jwks_urls(settings)
    assert len(urls) == 4
    assert {kind for kind, _ in urls} == set(ALL_CLERK_APP_KINDS)


def test_identical_four_slots_are_platform_driver_local_dev() -> None:
    shared_sk = "sk_test_platform"
    shared_jwks = "https://platform.clerk.accounts.dev/.well-known/jwks.json"
    shared_pk = "pk_test_platform"
    settings = Settings(
        _env_file=None,
        clerk_unified_mode=False,
        clerk_customer_secret_key=shared_sk,
        clerk_customer_jwks_url=shared_jwks,
        clerk_customer_publishable_key=shared_pk,
        clerk_merchant_secret_key=shared_sk,
        clerk_merchant_jwks_url=shared_jwks,
        clerk_merchant_publishable_key=shared_pk,
        clerk_admin_secret_key=shared_sk,
        clerk_admin_jwks_url=shared_jwks,
        clerk_admin_publishable_key=shared_pk,
        clerk_driver_secret_key=shared_sk,
        clerk_driver_jwks_url=shared_jwks,
        clerk_driver_publishable_key=shared_pk,
        jwt_secret="a" * 32,
    )
    assert is_enterprise_clerk_configured(settings)
    assert clerk_configuration_mode(settings) == "platform_driver"
    assert len(clerk_jwks_urls(settings)) == 1


def test_platform_driver_keeps_distinct_driver_issuer() -> None:
    sk = "sk_test_platform"
    jwks = "https://relaxing-warthog-11.clerk.accounts.dev/.well-known/jwks.json"
    pk = "pk_test_platform"
    settings = Settings(
        _env_file=None,
        clerk_unified_mode=False,
        clerk_secret_key=sk,
        clerk_jwks_url=jwks,
        clerk_publishable_key=pk,
        clerk_customer_secret_key=sk,
        clerk_customer_jwks_url=jwks,
        clerk_customer_publishable_key=pk,
        clerk_merchant_secret_key=sk,
        clerk_merchant_jwks_url=jwks,
        clerk_merchant_publishable_key=pk,
        clerk_admin_secret_key=sk,
        clerk_admin_jwks_url=jwks,
        clerk_admin_publishable_key=pk,
        clerk_driver_secret_key="sk_test_driver",
        clerk_driver_jwks_url="https://driver.clerk.accounts.dev/.well-known/jwks.json",
        clerk_driver_publishable_key="pk_test_driver",
        jwt_secret="a" * 32,
    )
    assert clerk_configuration_mode(settings) == "platform_driver"
    urls = clerk_jwks_urls(settings)
    assert len(urls) == 2
    apps = clerk_app_configs(settings)
    assert {a.secret_key for a in apps} == {sk, "sk_test_driver"}


def test_platform_triad_falls_back_to_admin_slots() -> None:
    from porterchain_api.auth.clerk_registry import resolve_platform_clerk_config

    settings = Settings(
        _env_file=None,
        clerk_unified_mode=False,
        clerk_secret_key="",
        clerk_jwks_url="",
        clerk_publishable_key="",
        clerk_admin_secret_key="sk_test_admin_platform",
        clerk_admin_jwks_url="https://relaxing-warthog-11.clerk.accounts.dev/.well-known/jwks.json",
        clerk_admin_publishable_key="pk_test_admin_platform",
        jwt_secret="a" * 32,
    )
    platform = resolve_platform_clerk_config(settings)
    assert platform is not None
    assert platform.secret_key == "sk_test_admin_platform"
    assert clerk_configuration_mode(settings) == "platform_driver"


def test_clerk_unified_mode_flag_rejected() -> None:
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError, match="CLERK_UNIFIED_MODE"):
        Settings(
            _env_file=None,
            clerk_unified_mode=True,
            clerk_secret_key="sk_test_platform",
            clerk_jwks_url="https://platform.clerk.accounts.dev/.well-known/jwks.json",
            jwt_secret="a" * 32,
        )


def test_production_boot_requires_clerk() -> None:
    try:
        Settings(
            _env_file=None,
            app_env="production",
            clerk_dev_bypass=False,
            jwt_secret="a" * 32,
            clerk_secret_key="",
            clerk_jwks_url="",
            clerk_customer_secret_key="",
            clerk_customer_jwks_url="",
            clerk_merchant_secret_key="",
            clerk_merchant_jwks_url="",
            clerk_admin_secret_key="",
            clerk_admin_jwks_url="",
            clerk_driver_secret_key="",
            clerk_driver_jwks_url="",
        )
    except ValueError as exc:
        assert "Clerk" in str(exc)
    else:
        raise AssertionError("expected ValueError for missing Clerk in production")
