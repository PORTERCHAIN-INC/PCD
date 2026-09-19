"""Queue publisher — enqueue async jobs for worker processes."""

import json
import logging
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import UTC, datetime
from functools import lru_cache
from threading import Lock
from typing import Any
from uuid import uuid4

from porterchain_shared.config.settings import get_platform_settings
from porterchain_shared.queue.names import QueueName

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class QueueMessage:
    message_id: str
    queue: QueueName
    payload: dict[str, Any]
    enqueued_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    retry_count: int = 0


class QueuePublisher(ABC):
    @abstractmethod
    def enqueue(self, queue: QueueName, payload: dict[str, Any]) -> QueueMessage:
        """Enqueue a job for async processing."""

    def dequeue(self, queue: QueueName, *, timeout_seconds: int = 1) -> QueueMessage | None:
        """Dequeue a job — optional; Redis/in-memory implementations override."""
        return None


class InMemoryQueuePublisher(QueuePublisher):
    def __init__(self) -> None:
        self._queues: dict[QueueName, deque[QueueMessage]] = defaultdict(deque)
        self._lock = Lock()

    def enqueue(self, queue: QueueName, payload: dict[str, Any]) -> QueueMessage:
        msg = QueueMessage(message_id=str(uuid4()), queue=queue, payload=payload)
        with self._lock:
            self._queues[queue].append(msg)
        logger.debug("enqueued %s -> %s", queue.value, msg.message_id)
        return msg

    def dequeue(self, queue: QueueName, *, timeout_seconds: int = 1) -> QueueMessage | None:
        with self._lock:
            if self._queues[queue]:
                return self._queues[queue].popleft()
        return None


class RedisQueuePublisher(QueuePublisher):
    def __init__(self, redis_url: str) -> None:
        import redis

        self._client = redis.from_url(redis_url, decode_responses=True)

    def enqueue(self, queue: QueueName, payload: dict[str, Any]) -> QueueMessage:
        msg = QueueMessage(message_id=str(uuid4()), queue=queue, payload=payload)
        self._client.lpush(
            queue.redis_key,
            json.dumps(
                {
                    "message_id": msg.message_id,
                    "payload": msg.payload,
                    "enqueued_at": msg.enqueued_at.isoformat(),
                    "retry_count": msg.retry_count,
                }
            ),
        )
        logger.info("enqueued %s -> %s", queue.value, msg.message_id)
        return msg

    def dequeue(self, queue: QueueName, *, timeout_seconds: int = 1) -> QueueMessage | None:
        try:
            # Redis BRPOP timeout=0 blocks forever — use LPOP for non-blocking polls.
            if timeout_seconds <= 0:
                raw = self._client.lpop(queue.redis_key)
                result = (queue.redis_key, raw) if raw else None
            else:
                result = self._client.brpop(queue.redis_key, timeout=timeout_seconds)
        except Exception as exc:
            exc_name = type(exc).__name__
            if exc_name in ("TimeoutError", "ConnectionError", "ConnectionResetError"):
                logger.warning("redis queue read interrupted (%s) on %s", exc_name, queue.value)
                return None
            try:
                import redis

                if isinstance(exc, (redis.TimeoutError, redis.ConnectionError)):
                    logger.warning("redis queue read interrupted (%s) on %s", exc_name, queue.value)
                    return None
            except ImportError:
                pass
            raise
        if not result:
            return None
        _, raw = result
        data = json.loads(raw)
        return QueueMessage(
            message_id=data["message_id"],
            queue=queue,
            payload=data["payload"],
            enqueued_at=datetime.fromisoformat(data["enqueued_at"]),
            retry_count=data.get("retry_count", 0),
        )


@lru_cache
def get_queue_publisher() -> QueuePublisher:
    settings = get_platform_settings()
    try:
        import redis

        client = redis.from_url(settings.redis_url, decode_responses=True)
        client.ping()
        return RedisQueuePublisher(settings.redis_url)
    except Exception as exc:
        if not settings.is_local:
            raise RuntimeError(f"Redis required for queues but unavailable: {exc}") from exc
        logger.warning("Redis unavailable; using in-memory queue publisher")
        return InMemoryQueuePublisher()


def queue_depths(publisher: QueuePublisher | None = None) -> dict[str, int]:
    """Return approximate depth per queue — Redis LLEN or in-memory deque length."""
    pub = publisher or get_queue_publisher()
    depths: dict[str, int] = {}
    if isinstance(pub, RedisQueuePublisher):
        import redis

        client = redis.from_url(get_platform_settings().redis_url, decode_responses=True)
        for queue in QueueName:
            depths[queue.value] = int(client.llen(queue.redis_key))
        return depths
    if isinstance(pub, InMemoryQueuePublisher):
        for queue in QueueName:
            depths[queue.value] = len(pub._queues[queue])  # noqa: SLF001
    return depths
