"""Redis connectivity checks — production requires a live Redis instance."""

from __future__ import annotations

import logging

from porterchain_shared.config.settings import get_platform_settings

logger = logging.getLogger(__name__)

_LOCAL_ENVS = frozenset({"local", "development", "dev", "test"})


def is_local_env(app_env: str | None = None) -> bool:
    env = (app_env or get_platform_settings().app_env).lower()
    return env in _LOCAL_ENVS


def ping_redis(redis_url: str | None = None) -> bool:
    try:
        if redis_url is not None and redis_url != get_platform_settings().redis_url:
            import redis

            client = redis.from_url(redis_url, decode_responses=True)
            client.ping()
            return True
        from porterchain_shared.redis_client import get_redis_client

        get_redis_client().ping()
        return True
    except Exception as exc:
        logger.debug("redis ping failed: %s", exc)
        return False


def require_redis_for_production() -> None:
    """Fail fast when Redis is required but unavailable (masterrule §12)."""
    settings = get_platform_settings()
    if is_local_env(settings.app_env):
        if not ping_redis(settings.redis_url):
            logger.warning(
                "Redis unavailable at %s — using in-memory event bus / queues (local dev only)",
                settings.redis_url,
            )
        return
    if not ping_redis(settings.redis_url):
        raise RuntimeError(
            f"Redis is required when APP_ENV={settings.app_env!r} but unavailable at {settings.redis_url}"
        )
