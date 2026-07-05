"""Shared Redis connection pool — one client per process (DD-06)."""

from __future__ import annotations

from functools import lru_cache

import redis

from porterchain_shared.config.settings import get_platform_settings


@lru_cache
def get_redis_client() -> redis.Redis:
    settings = get_platform_settings()
    return redis.from_url(
        settings.redis_url,
        decode_responses=True,
        max_connections=20,
    )
