"""Dead letter queue for events that exceed retry limits."""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from collections import deque
from datetime import UTC, datetime
from threading import Lock

logger = logging.getLogger(__name__)

DLQ_STREAM_KEY = "porterchain:events:dlq"


class DeadLetterQueue(ABC):
    @abstractmethod
    def send(self, *, event_id: str, event_type: str, payload: dict, error: str, attempts: int) -> None: ...


class InMemoryDeadLetterQueue(DeadLetterQueue):
    def __init__(self, max_size: int = 1_000) -> None:
        self._items: deque[dict] = deque(maxlen=max_size)
        self._lock = Lock()

    def send(self, *, event_id: str, event_type: str, payload: dict, error: str, attempts: int) -> None:
        entry = {
            "event_id": event_id,
            "event_type": event_type,
            "payload": payload,
            "error": error,
            "attempts": attempts,
            "dead_lettered_at": datetime.now(UTC).isoformat(),
        }
        with self._lock:
            self._items.append(entry)
        logger.error("event dead-lettered: %s (%s) after %s attempts", event_id, event_type, attempts)

    def items(self) -> list[dict]:
        with self._lock:
            return list(self._items)


class RedisDeadLetterQueue(DeadLetterQueue):
    def __init__(self, redis_url: str) -> None:
        import redis

        self._client = redis.from_url(redis_url, decode_responses=True)

    def send(self, *, event_id: str, event_type: str, payload: dict, error: str, attempts: int) -> None:
        self._client.xadd(
            DLQ_STREAM_KEY,
            {
                "event_id": event_id,
                "event_type": event_type,
                "payload": json.dumps(payload),
                "error": error[:2000],
                "attempts": str(attempts),
                "dead_lettered_at": datetime.now(UTC).isoformat(),
            },
            maxlen=50_000,
            approximate=True,
        )
        logger.error("event dead-lettered (redis): %s (%s)", event_id, event_type)
