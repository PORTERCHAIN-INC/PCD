"""Merchant API gateway — Redis rate limit + OAuth coverage."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from porterchain_api.gateway_engine import merchant_api as gateway
from porterchain_api.gateway_engine.merchant_api import check_rate_limit_redis
from porterchain_api.platform.rate_limit import (
    TRAFFIC_MERCHANT_API,
    TRAFFIC_MERCHANT_API_OAUTH,
    TRAFFIC_MERCHANT_API_SANDBOX,
)


def test_check_rate_limit_redis_allows() -> None:
    client = MagicMock()
    client.incr.return_value = 2
    with patch("porterchain_shared.redis_client.get_redis_client", return_value=client):
        allowed, current, error = check_rate_limit_redis(
            traffic_class=TRAFFIC_MERCHANT_API,
            identity="key-abc",
            limit=60,
        )
    assert allowed is True
    assert current == 2
    assert error is None
    assert client.incr.call_args[0][0].startswith("porterchain:ratelimit:merchant_api:key-abc:")


def test_check_rate_limit_redis_oauth_class() -> None:
    client = MagicMock()
    client.incr.return_value = 61
    with patch("porterchain_shared.redis_client.get_redis_client", return_value=client):
        allowed, current, error = check_rate_limit_redis(
            traffic_class=TRAFFIC_MERCHANT_API_OAUTH,
            identity="merchant-1",
            limit=60,
        )
    assert allowed is False
    assert current == 61
    assert error is None
    assert "merchant_api_oauth:merchant-1" in client.incr.call_args[0][0]


def test_check_rate_limit_redis_sandbox_class_isolated() -> None:
    client = MagicMock()
    client.incr.return_value = 1
    with patch("porterchain_shared.redis_client.get_redis_client", return_value=client):
        allowed, current, error = check_rate_limit_redis(
            traffic_class=TRAFFIC_MERCHANT_API_SANDBOX,
            identity="key-sand",
            limit=60,
        )
    assert allowed is True
    assert current == 1
    assert error is None
    assert "merchant_api_sandbox:key-sand" in client.incr.call_args[0][0]


def test_check_rate_limit_peeks_redis_for_ui() -> None:
    api_key = SimpleNamespace(id="k1", rate_limit_per_minute=60, environment="production")
    with patch(
        "porterchain_api.platform.rate_limit.peek_fixed_window",
        return_value=(12, None),
    ) as peek:
        allowed, current, limit = gateway.check_rate_limit(MagicMock(), api_key)  # type: ignore[arg-type]
    assert allowed is True
    assert current == 12
    assert limit == 60
    peek.assert_called_once()
    assert peek.call_args[0][0] == "porterchain:ratelimit:merchant_api:k1"


def test_check_rate_limit_peeks_sandbox_bucket() -> None:
    api_key = SimpleNamespace(id="k2", rate_limit_per_minute=60, environment="sandbox")
    with patch(
        "porterchain_api.platform.rate_limit.peek_fixed_window",
        return_value=(3, None),
    ) as peek:
        allowed, current, limit = gateway.check_rate_limit(MagicMock(), api_key)  # type: ignore[arg-type]
    assert allowed is True
    assert current == 3
    assert limit == 60
    assert peek.call_args[0][0] == "porterchain:ratelimit:merchant_api_sandbox:k2"
