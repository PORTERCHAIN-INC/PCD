"""Shared pytest fixtures for API tests."""

from __future__ import annotations

import os
from urllib.parse import urlsplit

import pytest

# --- Test infrastructure guard -------------------------------------------------
# Tests only ever talk to the throwaway containers from scripts/test-infra.sh.
# These defaults apply before any app module reads its settings, and the guard
# below refuses to run when anything points at the live dev stack.
TEST_DATABASE_URL = "postgresql+psycopg://porterchain:porterchain@127.0.0.1:55432/porterchain_test"
TEST_REDIS_URL = "redis://127.0.0.1:56379/0"
TEST_SPICEDB_ENDPOINT = "127.0.0.1:55051"
TEST_SPICEDB_KEY = "porterchain-spicedb-test-key"

os.environ.setdefault("DATABASE_URL", TEST_DATABASE_URL)
os.environ.setdefault("REDIS_URL", TEST_REDIS_URL)
os.environ.setdefault("SPICEDB_ENDPOINT", TEST_SPICEDB_ENDPOINT)
os.environ.setdefault("SPICEDB_PRESHARED_KEY", TEST_SPICEDB_KEY)

# Tests may ONLY use the throwaway test containers (scripts/test-infra.sh): anything else
# — live dev stack (5432/6379/50051), the local stack (~/pcd-local, pg 55632), a remote
# host — is refused, even when inherited from a sourced app.env.
_TEST_PORTS = {"DATABASE_URL": {55432}, "REDIS_URL": {56379}, "SPICEDB_ENDPOINT": {55051}}
_DEFAULT_PORTS = {"DATABASE_URL": 5432, "REDIS_URL": 6379, "SPICEDB_ENDPOINT": 50051}
_LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}


def _host_port(name: str, value: str) -> tuple[str, int | None]:
    parts = urlsplit(value if "://" in value else f"grpc://{value}")
    return (parts.hostname or ""), parts.port


def live_service_violations(env: dict[str, str] | None = None) -> list[str]:
    """Return a message per setting that is not a local test-container endpoint."""
    env = os.environ if env is None else env
    bad: list[str] = []
    for name, ok_ports in _TEST_PORTS.items():
        value = env.get(name, "")
        if not value or value.startswith("sqlite"):
            continue
        host, port = _host_port(name, value)
        if (port or _DEFAULT_PORTS[name]) not in ok_ports or host not in _LOCAL_HOSTS:
            bad.append(f"{name}={value!r} is not a test container (allowed: localhost:{sorted(ok_ports)[0]})")
    return bad


def pytest_configure(config):
    bad = live_service_violations()
    if bad:
        raise pytest.UsageError(
            "Refusing to run tests outside the test containers:\n  "
            + "\n  ".join(bad)
            + "\nStart throwaway containers with `bash scripts/test-infra.sh up` and unset these vars."
        )


from porterchain_api.db import SessionLocal, init_db


@pytest.fixture(scope="session")
def db_url() -> str:
    url = os.environ.get("DATABASE_URL", TEST_DATABASE_URL)
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
        stripe_secret="",  # never call real Stripe from tests, even with a local .env key
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


@pytest.fixture(autouse=True)
def _reset_public_form_rate_limits():
    """Public form limits are per IP; every TestClient shares one IP.

    Clear the marketing buckets before each test so unrelated tests don't
    trip each other's 3-per-minute window. Tests of the limiter itself
    monkeypatch ``check_fixed_window`` directly.
    """
    try:
        from porterchain_shared.redis_client import get_redis_client

        client = get_redis_client()
        for key in client.scan_iter("porterchain:ratelimit:marketing_public:*", count=500):
            client.delete(key)
    except Exception:  # noqa: BLE001 — Redis optional for unit tests
        pass
    yield


@pytest.fixture
def quiet_pool(db_url: str):
    """Day-plan tests see only their own drivers/orders: park leftovers from earlier runs."""
    from porterchain_api.admin_models import Driver
    from porterchain_api.booking_models import Order

    init_db()
    s = SessionLocal()
    try:
        s.query(Driver).filter(Driver.is_online.is_(True)).update({Driver.is_online: False}, synchronize_session=False)
        s.query(Order).filter(Order.assigned_driver_id.is_(None), Order.state == "DISPATCH_READY").update(
            {Order.state: "CANCELLED"}, synchronize_session=False)
        s.commit()
    finally:
        s.close()


@pytest.fixture
def gst_registered(db_url: str):
    """Register a GST/HST number from 2000-01-01 for tests that expect tax to be charged.

    Without a registration the system charges and shows no GST/HST anywhere
    (docs/compliance/INVOICE_ADJUSTMENTS_CANADA.md §10).
    """
    from datetime import date

    from porterchain_api.admin_models import TaxRegistration
    from porterchain_api.platform import tax_registration as reg

    init_db()
    s = SessionLocal()
    s.query(TaxRegistration).delete()
    reg.record_registration(
        s, gst_hst_number="123456789RT0001", legal_name="PorterChain Inc.", effective_from=date(2000, 1, 1), actor_id=None
    )
    s.commit()
    s.close()
    reg.clear_cache(None)
    yield "123456789 RT0001"
    s = SessionLocal()
    s.query(TaxRegistration).delete()
    s.commit()
    s.close()
    reg.clear_cache(None)
