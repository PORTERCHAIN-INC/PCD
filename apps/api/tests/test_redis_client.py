"""Shared Redis client pool tests."""

from unittest.mock import MagicMock, patch

from porterchain_shared.redis_client import get_redis_client


def test_get_redis_client_is_singleton() -> None:
    get_redis_client.cache_clear()
    mock_client = MagicMock()
    with patch("redis.BlockingConnectionPool.from_url", return_value=MagicMock()) as from_url, patch(
        "redis.Redis", return_value=mock_client
    ):
        first = get_redis_client()
        second = get_redis_client()
    assert first is second
    from_url.assert_called_once()
    assert from_url.call_args.kwargs["max_connections"] >= 64
    get_redis_client.cache_clear()
