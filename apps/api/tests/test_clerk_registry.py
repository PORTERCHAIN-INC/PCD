"""Clerk per-portal registry (§0.5)."""

from porterchain_api.auth.clerk_registry import (
    ALL_CLERK_APP_KINDS,
    clerk_app_configs,
    clerk_configuration_mode,
    clerk_jwks_urls,
    is_enterprise_clerk_configured,
)
from porterchain_api.config import Settings


def test_legacy_clerk_expands_to_all_portals() -> None:
    settings = Settings(
        clerk_secret_key="sk_test_legacy",
        clerk_jwks_url="https://legacy.clerk.accounts.dev/.well-known/jwks.json",
        clerk_publishable_key="pk_test_legacy",
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
        clerk_customer_secret_key="sk_cust",
        clerk_customer_jwks_url="https://cust.clerk.accounts.dev/.well-known/jwks.json",
        clerk_merchant_secret_key="sk_merch",
        clerk_merchant_jwks_url="https://merch.clerk.accounts.dev/.well-known/jwks.json",
        clerk_admin_secret_key="sk_admin",
        clerk_admin_jwks_url="https://admin.clerk.accounts.dev/.well-known/jwks.json",
        clerk_driver_secret_key="sk_driver",
        clerk_driver_jwks_url="https://driver.clerk.accounts.dev/.well-known/jwks.json",
    )
    assert clerk_configuration_mode(settings) == "enterprise"
    assert is_enterprise_clerk_configured(settings)
    urls = clerk_jwks_urls(settings)
    assert len(urls) == 4
    assert {kind for kind, _ in urls} == set(ALL_CLERK_APP_KINDS)


def test_production_boot_requires_clerk() -> None:
    try:
        Settings(app_env="production", clerk_dev_bypass=False, jwt_secret="a" * 32)
    except ValueError as exc:
        assert "Clerk" in str(exc)
    else:
        raise AssertionError("expected ValueError for missing Clerk in production")
