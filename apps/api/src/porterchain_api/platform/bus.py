"""Event bus bridge — publishes to centralized EventBus + DB audit log."""

import logging

from porterchain_event_bus import build_envelope, get_event_bus
from porterchain_event_bus.handlers import register_default_handlers

logger = logging.getLogger(__name__)

_handlers_registered = False


def ensure_handlers_registered() -> None:
    global _handlers_registered
    if not _handlers_registered:
        register_default_handlers()
        _handlers_registered = True


def publish_domain_event(
    *,
    event_type: str,
    aggregate_type: str,
    aggregate_id: str,
    correlation_id: str | None = None,
    actor_type: str = "system",
    actor_id: str | None = None,
    payload: dict | None = None,
    event_id: str | None = None,
) -> None:
    ensure_handlers_registered()
    envelope = build_envelope(
        event_type=event_type,
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        correlation_id=correlation_id,
        actor_type=actor_type,
        actor_id=actor_id,
        payload=payload,
        event_id=event_id,
    )
    bus = get_event_bus()
    bus.publish(envelope, dispatch_sync=bus._redis_client is None)
