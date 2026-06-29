"""Shared booking engine utilities."""

from sqlalchemy.orm import Session

from porterchain_api.models import DomainEvent


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
) -> None:
    db.add(
        DomainEvent(
            event_type=event_type,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            correlation_id=correlation_id,
            actor_type=actor_type,
            actor_id=actor_id,
            payload=payload or {},
        )
    )
    try:
        from porterchain_api.platform.bus import publish_domain_event

        publish_domain_event(
            event_type=event_type,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            correlation_id=correlation_id,
            actor_type=actor_type,
            actor_id=actor_id,
            payload=payload,
        )
    except Exception as exc:
        import logging

        logging.getLogger(__name__).warning("event bus publish failed: %s", exc)
