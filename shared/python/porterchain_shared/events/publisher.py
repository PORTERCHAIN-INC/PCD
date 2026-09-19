"""Event publisher — Redis Streams in production, in-memory for local dev."""

import json
import logging
from abc import ABC, abstractmethod
from collections import deque
from functools import lru_cache
from threading import Lock

from porterchain_shared.config.settings import get_platform_settings
from porterchain_shared.events.envelope import EventEnvelope

logger = logging.getLogger(__name__)

STREAM_KEY = "porterchain:events"


class EventPublisher(ABC):
    @abstractmethod
    def publish(self, event: EventEnvelope) -> str:
        """Publish event; returns event_id."""


class InMemoryEventPublisher(EventPublisher):
    """Local dev fallback — bounded ring buffer for inspection."""

    def __init__(self, max_size: int = 10_000) -> None:
        self._events: deque[EventEnvelope] = deque(maxlen=max_size)
        self._lock = Lock()

    def publish(self, event: EventEnvelope) -> str:
        with self._lock:
            self._events.append(event)
        logger.debug("event published (memory): %s", event.event_type)
        return event.event_id

    def recent(self, limit: int = 100) -> list[EventEnvelope]:
        with self._lock:
            return list(self._events)[-limit:]


class RedisEventPublisher(EventPublisher):
    """Redis Streams publisher for production event backbone."""

    def __init__(self, redis_url: str) -> None:
        import redis

        self._client = redis.from_url(redis_url, decode_responses=True)

    def publish(self, event: EventEnvelope) -> str:
        fields = event.to_stream_fields()
        fields["payload"] = json.dumps(event.payload)
        self._client.xadd(STREAM_KEY, fields, maxlen=100_000, approximate=True)
        logger.info("event published (redis): %s", event.event_type)
        return event.event_id


@lru_cache
def get_event_publisher() -> EventPublisher:
    settings = get_platform_settings()
    try:
        import redis

        client = redis.from_url(settings.redis_url, decode_responses=True)
        client.ping()
        return RedisEventPublisher(settings.redis_url)
    except Exception:
        logger.warning("Redis unavailable; using in-memory event publisher")
        return InMemoryEventPublisher()
