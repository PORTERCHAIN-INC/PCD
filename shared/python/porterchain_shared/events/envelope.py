"""Immutable domain event envelope."""

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from porterchain_shared.events.catalog import DomainEventType


class EventActor(BaseModel):
    type: str
    id: str | None = None


class EventEnvelope(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    event_type: DomainEventType | str
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    aggregate_type: str
    aggregate_id: str
    correlation_id: str | None = None
    actor: EventActor = Field(default_factory=lambda: EventActor(type="system"))
    payload: dict[str, Any] = Field(default_factory=dict)
    version: int = 1

    def to_stream_fields(self) -> dict[str, str]:
        """Redis Streams field mapping."""
        return {
            "event_id": self.event_id,
            "event_type": str(self.event_type),
            "occurred_at": self.occurred_at.isoformat(),
            "aggregate_type": self.aggregate_type,
            "aggregate_id": self.aggregate_id,
            "correlation_id": self.correlation_id or "",
            "actor_type": self.actor.type,
            "actor_id": self.actor.id or "",
            "payload": self.model_dump_json(include={"payload"}),
            "version": str(self.version),
        }
