"""Shared booking engine utilities."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.models import DomainEvent

logger = logging.getLogger(__name__)


def _event_fields(
    *,
    event_type: str,
    aggregate_type: str,
    aggregate_id: str,
    correlation_id: str | None = None,
    actor_type: str = "system",
    actor_id: str | None = None,
    payload: dict | None = None,
) -> dict[str, Any]:
    return {
        "event_type": event_type,
        "aggregate_type": aggregate_type,
        "aggregate_id": aggregate_id,
        "correlation_id": correlation_id,
        "actor_type": actor_type,
        "actor_id": actor_id,
        "payload": payload,
    }


def record_domain_event(db: Session, **fields: Any) -> None:
    """Persist a domain event row without publishing to the bus."""
    db.add(
        DomainEvent(
            event_type=fields["event_type"],
            aggregate_type=fields["aggregate_type"],
            aggregate_id=fields["aggregate_id"],
            correlation_id=fields.get("correlation_id"),
            actor_type=fields.get("actor_type", "system"),
            actor_id=fields.get("actor_id"),
            payload=fields.get("payload") or {},
        )
    )


def publish_recorded_event(**fields: Any) -> None:
    """Publish a domain event to the bus (call after db.commit())."""
    try:
        from porterchain_api.platform.bus import publish_domain_event

        publish_domain_event(
            event_type=fields["event_type"],
            aggregate_type=fields["aggregate_type"],
            aggregate_id=fields["aggregate_id"],
            correlation_id=fields.get("correlation_id"),
            actor_type=fields.get("actor_type", "system"),
            actor_id=fields.get("actor_id"),
            payload=fields.get("payload"),
        )
    except Exception as exc:
        logger.warning("event bus publish failed: %s", exc)


def emit_event(
    db: Session,
    *,
    event_type: str,
    aggregate_type: str,
    aggregate_id: str,
    correlation_id: str | None = None,
    actor_type: str = "system",
    actor_id: str | None = None,
    payload: dict | None = None,
    publish: bool = True,
) -> None:
    """Record a domain event and optionally publish it to the bus."""
    fields = _event_fields(
        event_type=event_type,
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        correlation_id=correlation_id,
        actor_type=actor_type,
        actor_id=actor_id,
        payload=payload,
    )
    record_domain_event(db, **fields)
    if publish:
        publish_recorded_event(**fields)
