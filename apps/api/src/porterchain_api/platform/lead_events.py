"""Lead domain events — collaboration may emit without importing booking_engine."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

LEAD_CREATED = "lead.created"
LEAD_MERGED = "lead.merged"
LEAD_ENGAGEMENT = "lead.engagement"
LEAD_WHATSAPP_BLOCKED = "lead.whatsapp_blocked"


def emit_lead_event(
    db: Session,
    *,
    event_type: str,
    lead_id: str,
    payload: dict[str, Any],
    correlation_id: str | None = None,
    actor_type: str = "system",
    actor_id: str | None = None,
    publish: bool = True,
) -> None:
    """Persist booking-domain lead event via the shared emit_event core."""
    from porterchain_api.booking_engine._core import emit_event

    emit_event(
        db,
        event_type=event_type,
        aggregate_type="crm_lead",
        aggregate_id=lead_id,
        correlation_id=correlation_id,
        actor_type=actor_type,
        actor_id=actor_id,
        payload=payload,
        publish=publish,
    )


__all__ = [
    "LEAD_CREATED",
    "LEAD_ENGAGEMENT",
    "LEAD_MERGED",
    "LEAD_WHATSAPP_BLOCKED",
    "emit_lead_event",
]
