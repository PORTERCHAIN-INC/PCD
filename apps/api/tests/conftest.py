"""Shared pytest fixtures for API tests."""

from __future__ import annotations

import os

import pytest

from porterchain_api.db import SessionLocal, init_db


@pytest.fixture(scope="session")
def db_url() -> str:
    url = os.environ.get(
        "DATABASE_URL",
        "postgresql+psycopg://porterchain:porterchain@localhost:5432/porterchain",
    )
    if url.startswith("sqlite"):
        pytest.skip("SQLite is not supported for integration tests")
    return url


@pytest.fixture
def db(db_url: str):
    init_db()
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def settings():
    from porterchain_api.config import Settings

    return Settings(
        app_env="local",
        stripe_mock=True,
        jwt_secret="test-jwt-secret-local",
        spicedb_enabled=False,
        spicedb_use_memory=True,
        spicedb_required=False,
    )


@pytest.fixture(autouse=True)
def _reset_authz_client():
    from porterchain_api.authz.client import reset_authz_client

    reset_authz_client()
    yield
    reset_authz_client()


@pytest.fixture(autouse=True)
def _no_live_shopify_token_calls(monkeypatch):
    """Never reach Shopify's token endpoint from tests.

    Shops seeded with a legacy token would otherwise try the one-time migration
    exchange. A network-style failure keeps the stored token (renewal deferred).
    Token tests patch ``shopify_tokens._token_request`` themselves.
    """
    from porterchain_api.merchant_engine import shopify_tokens

    def _offline(shop: str, data: dict[str, str]):
        raise shopify_tokens.ShopifyTokenError(None, "tests_offline")

    monkeypatch.setattr(shopify_tokens, "_token_request", _offline)
