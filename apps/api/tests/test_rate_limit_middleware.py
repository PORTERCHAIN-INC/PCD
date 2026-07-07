"""Rate limit middleware — fail-closed when Redis unavailable (DD-06)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from porterchain_api.platform.rate_limit_middleware import _check_rate


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
