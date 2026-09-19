"""Shared Redis rate limiter + portal re-export (DD-06)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from porterchain_api.platform.rate_limit import (
    TRAFFIC_MERCHANT_API,
    TRAFFIC_MERCHANT_API_OAUTH,
    _check_rate,
    bucket_key,
    check_fixed_window,
    peek_fixed_window,
)


def test_check_rate_allows_under_limit() -> None:
    client = MagicMock()
    client.incr.return_value = 3
    with patch("porterchain_shared.redis_client.get_redis_client", return_value=client):
        allowed, current, error = _check_rate("test:key", 100, 10)
    assert allowed is True
    assert current == 3
    assert error is None
    client.expire.assert_not_called()


def test_check_rate_sets_expiry_on_first_hit() -> None:
    client = MagicMock()
    client.incr.return_value = 1
    with patch("porterchain_shared.redis_client.get_redis_client", return_value=client):
        allowed, current, error = _check_rate("test:key", 100, 10)
    assert allowed is True
    assert current == 1
    assert error is None
    client.expire.assert_called_once_with("test:key:100", 70)


def test_check_rate_rejects_over_limit() -> None:
    client = MagicMock()
    client.incr.return_value = 11
    with patch("porterchain_shared.redis_client.get_redis_client", return_value=client):
        allowed, current, error = _check_rate("test:key", 100, 10)
    assert allowed is False
    assert current == 11
    assert error is None


def test_check_rate_fails_closed_on_redis_error() -> None:
    with patch(
        "porterchain_shared.redis_client.get_redis_client",
        side_effect=ConnectionError("redis down"),
    ):
        allowed, current, error = _check_rate("test:key", 100, 10)
    assert allowed is False
    assert current == 0
    assert error == "redis down"


def test_check_fixed_window_uses_minute_bucket() -> None:
    client = MagicMock()
    client.incr.return_value = 1
    with patch("porterchain_shared.redis_client.get_redis_client", return_value=client):
        with patch("porterchain_api.platform.rate_limit.time.time", return_value=600):
            allowed, current, error = check_fixed_window("porterchain:ratelimit:portal:ip:1", 10)
    assert allowed is True
    assert current == 1
    assert error is None
    client.incr.assert_called_once_with("porterchain:ratelimit:portal:ip:1:10")


def test_bucket_key_traffic_classes() -> None:
    assert bucket_key(TRAFFIC_MERCHANT_API, "key-1") == "porterchain:ratelimit:merchant_api:key-1"
    assert (
        bucket_key(TRAFFIC_MERCHANT_API_OAUTH, "m-1")
        == "porterchain:ratelimit:merchant_api_oauth:m-1"
    )


def test_peek_fixed_window_reads_without_incr() -> None:
    client = MagicMock()
    client.get.return_value = b"7"
    with patch("porterchain_shared.redis_client.get_redis_client", return_value=client):
        count, error = peek_fixed_window("porterchain:ratelimit:merchant_api:k", window=5)
    assert count == 7
    assert error is None
    client.incr.assert_not_called()
    client.get.assert_called_once_with("porterchain:ratelimit:merchant_api:k:5")
