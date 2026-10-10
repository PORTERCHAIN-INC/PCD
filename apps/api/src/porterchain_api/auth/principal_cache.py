"""Optional Redis cache for CurrentPrincipal session payloads (Phase C).

Disabled when Redis is unavailable or PRINCIPAL_CACHE_TTL_SECONDS=0.
Never caches secrets — only the safe session_context() dict.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

logger = logging.getLogger("porterchain.security")

_CACHE_PREFIX = "pc:principal:v1:"


def principal_cache_ttl_seconds() -> int:
    raw = os.environ.get("PRINCIPAL_CACHE_TTL_SECONDS", "30")
    try:
        return max(0, int(raw))
    except ValueError:
        return 30


def _client():
    try:
        from porterchain_shared.redis_client import get_redis_client

        client = get_redis_client()
        client.ping()
        return client
    except Exception:  # noqa: BLE001
        return None


def cache_get(user_id: str) -> dict[str, Any] | None:
    ttl = principal_cache_ttl_seconds()
    if ttl <= 0 or not user_id:
        return None
    client = _client()
    if client is None:
        return None
    try:
        raw = client.get(f"{_CACHE_PREFIX}{user_id}")
        if not raw:
            return None
        data = json.loads(raw)
        return data if isinstance(data, dict) else None
    except Exception:
        logger.debug("principal_cache_get_failed", exc_info=True)
        return None


def cache_set(user_id: str, payload: dict[str, Any]) -> None:
    ttl = principal_cache_ttl_seconds()
    if ttl <= 0 or not user_id:
        return
    client = _client()
    if client is None:
        return
    try:
        client.setex(f"{_CACHE_PREFIX}{user_id}", ttl, json.dumps(payload, default=str))
    except Exception:
        logger.debug("principal_cache_set_failed", exc_info=True)


def cache_invalidate(user_id: str) -> None:
    if not user_id:
        return
    client = _client()
    if client is None:
        return
    try:
        client.delete(f"{_CACHE_PREFIX}{user_id}")
    except Exception:
        logger.debug("principal_cache_invalidate_failed", exc_info=True)
