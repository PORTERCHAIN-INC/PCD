"""A burst bigger than the threadpool must not fail Redis calls (false 401s)."""

from concurrent.futures import ThreadPoolExecutor

import pytest
import redis

from porterchain_shared.redis_client import get_redis_client


def test_pool_is_blocking_and_sized_for_threadpool() -> None:
    pool = get_redis_client().connection_pool
    assert isinstance(pool, redis.BlockingConnectionPool)
    assert pool.max_connections >= 40


def test_burst_of_80_parallel_calls_all_succeed() -> None:
    c = get_redis_client()
    try:
        c.ping()
    except redis.exceptions.ConnectionError:
        pytest.skip("redis not running")

    def one(_: int) -> bool:
        return bool(c.ping())

    with ThreadPoolExecutor(80) as ex:
        assert all(ex.map(one, range(800)))
