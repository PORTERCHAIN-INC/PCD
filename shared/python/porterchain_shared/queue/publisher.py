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

    def dequeue(self, queue: QueueName) -> QueueMessage | None:
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


@lru_cache
def get_queue_publisher() -> QueuePublisher:
    settings = get_platform_settings()
    try:
        import redis

        client = redis.from_url(settings.redis_url, decode_responses=True)
        client.ping()
        return RedisQueuePublisher(settings.redis_url)
    except Exception:
        logger.warning("Redis unavailable; using in-memory queue publisher")
        return InMemoryQueuePublisher()
