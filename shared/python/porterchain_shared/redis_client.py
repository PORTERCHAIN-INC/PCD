"""Shared Redis connection pool — one client per process (DD-06)."""

from __future__ import annotations

from functools import lru_cache

import redis

from porterchain_shared.config.settings import get_platform_settings


@lru_cache
def get_redis_client() -> redis.Redis:
    settings = get_platform_settings()
    # Blocking pool: when every connection is busy a caller waits (up to 5 s) instead of
    # failing with MaxConnectionsError. The old non-blocking pool of 20 was smaller than
    # the 40-thread FastAPI threadpool, so bursts turned valid staff sessions into
    # 401 staff_session_invalid (get_session swallows the error and returns None).
    pool = redis.BlockingConnectionPool.from_url(
        settings.redis_url,
        decode_responses=True,
        max_connections=64,
        timeout=5,
    )
    return redis.Redis(connection_pool=pool)
