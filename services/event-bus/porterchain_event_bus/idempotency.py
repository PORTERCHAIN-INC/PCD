"""Idempotency store — prevent duplicate event processing."""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from threading import Lock

logger = logging.getLogger(__name__)

PROCESSED_KEY_PREFIX = "porterchain:events:processed:"
DEFAULT_TTL_SECONDS = 7 * 24 * 3600


class IdempotencyStore(ABC):
    @abstractmethod
    def is_processed(self, event_id: str) -> bool: ...

    @abstractmethod
    def mark_processed(self, event_id: str, *, ttl_seconds: int = DEFAULT_TTL_SECONDS) -> None: ...


class InMemoryIdempotencyStore(IdempotencyStore):
    def __init__(self) -> None:
        self._seen: dict[str, float] = {}
        self._lock = Lock()

    def is_processed(self, event_id: str) -> bool:
        with self._lock:
            expiry = self._seen.get(event_id)
            if expiry is None:
                return False
            if expiry < time.time():
                del self._seen[event_id]
                return False
            return True

    def mark_processed(self, event_id: str, *, ttl_seconds: int = DEFAULT_TTL_SECONDS) -> None:
        with self._lock:
            self._seen[event_id] = time.time() + ttl_seconds


class RedisIdempotencyStore(IdempotencyStore):
    def __init__(self, redis_url: str) -> None:
        import redis

        self._client = redis.from_url(redis_url, decode_responses=True)

    def is_processed(self, event_id: str) -> bool:
        return bool(self._client.exists(f"{PROCESSED_KEY_PREFIX}{event_id}"))

    def mark_processed(self, event_id: str, *, ttl_seconds: int = DEFAULT_TTL_SECONDS) -> None:
        self._client.setex(f"{PROCESSED_KEY_PREFIX}{event_id}", ttl_seconds, "1")
