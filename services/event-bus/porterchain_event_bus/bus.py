"""Centralized Porterchain event bus."""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from typing import Any

from porterchain_event_bus.dlq import (
    DeadLetterQueue,
    InMemoryDeadLetterQueue,
    RedisDeadLetterQueue,
)
from porterchain_event_bus.idempotency import (
    IdempotencyStore,
    InMemoryIdempotencyStore,
    RedisIdempotencyStore,
)
from porterchain_event_bus.registry import EventHandler, HandlerRegistry, get_handler_registry
from porterchain_event_bus.retry import RetryPolicy
from porterchain_event_bus.versioning import schema_version_for

logger = logging.getLogger(__name__)

STREAM_KEY = "porterchain:events"
CONSUMER_GROUP = "porterchain-workers"


class EventBus:
    """
    Publish domain events to Redis Streams (or in-memory).
    Subscribe handlers via HandlerRegistry — modules never call each other directly.
    """

    def __init__(
        self,
        *,
        registry: HandlerRegistry | None = None,
        idempotency: IdempotencyStore | None = None,
        dlq: DeadLetterQueue | None = None,
        retry_policy: RetryPolicy | None = None,
        redis_url: str | None = None,
        use_redis: bool = True,
        strict_redis: bool = False,
    ) -> None:
        self.registry = registry or get_handler_registry()
        self.retry_policy = retry_policy or RetryPolicy()
        self._redis_url = redis_url
        self._redis_client = None
        self._memory_events: list[dict[str, Any]] = []

        if use_redis and redis_url:
            try:
                import redis

                self._redis_client = redis.from_url(redis_url, decode_responses=True)
                self._redis_client.ping()
                self.idempotency = idempotency or RedisIdempotencyStore(redis_url)
                self.dlq = dlq or RedisDeadLetterQueue(redis_url)
                self._ensure_consumer_group()
                logger.info("EventBus using Redis Streams at %s", STREAM_KEY)
            except Exception as exc:
                if strict_redis:
                    raise RuntimeError(f"Redis required but unavailable: {exc}") from exc
                logger.warning("Redis unavailable for EventBus (%s); using in-memory", exc)
                self._redis_client = None
                self.idempotency = idempotency or InMemoryIdempotencyStore()
                self.dlq = dlq or InMemoryDeadLetterQueue()
        else:
            self.idempotency = idempotency or InMemoryIdempotencyStore()
            self.dlq = dlq or InMemoryDeadLetterQueue()

    def _ensure_consumer_group(self) -> None:
        if not self._redis_client:
            return
        try:
            self._redis_client.xgroup_create(STREAM_KEY, CONSUMER_GROUP, id="0", mkstream=True)
        except Exception as exc:
            if "BUSYGROUP" not in str(exc):
                logger.debug("consumer group setup: %s", exc)

    def publish(self, envelope: dict[str, Any], *, dispatch_sync: bool = False) -> str:
        """Publish event envelope. Returns event_id."""
        event_id = envelope["event_id"]
        event_type = envelope["event_type"]
        envelope.setdefault("version", schema_version_for(event_type))

        if self._redis_client:
            fields = {k: (json.dumps(v) if isinstance(v, (dict, list)) else str(v)) for k, v in envelope.items()}
            self._redis_client.xadd(STREAM_KEY, fields, maxlen=100_000, approximate=True)
            logger.info("event published: %s (%s)", event_id, event_type)
        else:
            self._memory_events.append(envelope)
            logger.info("event published (memory): %s (%s)", event_id, event_type)
            if dispatch_sync:
                self._dispatch_to_handlers(envelope)

        return event_id

    def subscribe(self, event_pattern: str, handler: EventHandler) -> None:
        self.registry.subscribe(event_pattern, handler)

    def dispatch(self, envelope: dict[str, Any]) -> None:
        """Dispatch envelope to registered handlers (with idempotency + retry)."""
        event_id = envelope["event_id"]
        if self.idempotency.is_processed(event_id):
            logger.debug("skipping duplicate event %s", event_id)
            return
        self._dispatch_to_handlers(envelope)
        self.idempotency.mark_processed(event_id)

    def _dispatch_to_handlers(self, envelope: dict[str, Any]) -> None:
        event_type = envelope["event_type"]
        handlers = self.registry.handlers_for(event_type)
        if not handlers:
            logger.debug("no handlers for %s", event_type)
            return

        last_error: Exception | None = None
        for attempt in range(1, self.retry_policy.max_attempts + 1):
            try:
                for handler in handlers:
                    handler(envelope)
                return
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "handler failed for %s attempt %s/%s: %s",
                    event_type,
                    attempt,
                    self.retry_policy.max_attempts,
                    exc,
                )
                if not self.retry_policy.should_retry(attempt):
                    break
                import time

                time.sleep(self.retry_policy.delay_for_attempt(attempt))

        self.dlq.send(
            event_id=envelope["event_id"],
            event_type=event_type,
            payload=envelope.get("payload", {}),
            error=str(last_error) if last_error else "unknown",
            attempts=self.retry_policy.max_attempts,
        )

    def consume_once(self, *, consumer_name: str = "worker-1", block_ms: int = 2000) -> int:
        """Consume one batch from Redis stream. Returns processed count."""
        if not self._redis_client:
            processed = 0
            while self._memory_events:
                envelope = self._memory_events.pop(0)
                self.dispatch(envelope)
                processed += 1
            return processed

        try:
            messages = self._redis_client.xreadgroup(
                CONSUMER_GROUP,
                consumer_name,
                {STREAM_KEY: ">"},
                count=10,
                block=block_ms,
            )
        except Exception as exc:
            # Idle block timeouts and transient socket errors must not crash the worker.
            exc_name = type(exc).__name__
            if exc_name in ("TimeoutError", "ConnectionError", "ConnectionResetError"):
                logger.warning("redis stream read interrupted (%s) — will retry", exc_name)
                return 0
            try:
                import redis

                if isinstance(exc, (redis.TimeoutError, redis.ConnectionError)):
                    logger.warning("redis stream read interrupted (%s) — will retry", exc_name)
                    return 0
            except ImportError:
                pass
            raise

        processed = 0
        for _stream, entries in messages or []:
            for message_id, fields in entries:
                envelope = self._parse_stream_fields(fields)
                try:
                    self.dispatch(envelope)
                    self._redis_client.xack(STREAM_KEY, CONSUMER_GROUP, message_id)
                    processed += 1
                except Exception as exc:
                    logger.error("failed to process stream message %s: %s", message_id, exc)
        return processed

    @staticmethod
    def _parse_stream_fields(fields: dict[str, str]) -> dict[str, Any]:
        envelope: dict[str, Any] = {}
        for key, value in fields.items():
            if key == "payload":
                try:
                    envelope[key] = json.loads(value)
                except json.JSONDecodeError:
                    envelope[key] = {}
            elif key == "version":
                envelope[key] = int(value)
            elif key in ("occurred_at",):
                envelope[key] = value
            elif key in ("correlation_id", "actor_id") and value == "":
                envelope[key] = None
            else:
                envelope[key] = value
        if "actor" not in envelope:
            envelope["actor"] = {"type": fields.get("actor_type", "system"), "id": fields.get("actor_id") or None}
        return envelope

    def recent_memory_events(self, limit: int = 100) -> list[dict[str, Any]]:
        return self._memory_events[-limit:]


@lru_cache
def get_event_bus() -> EventBus:
    from porterchain_shared.config.settings import get_platform_settings

    settings = get_platform_settings()
    return EventBus(
        redis_url=settings.redis_url,
        use_redis=True,
        strict_redis=not settings.is_local,
    )
