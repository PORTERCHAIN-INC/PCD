"""Envelope helpers for the event bus."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from porterchain_event_bus.versioning import schema_version_for


def build_envelope(
    *,
    event_type: str,
    aggregate_type: str,
    aggregate_id: str,
    payload: dict[str, Any] | None = None,
    correlation_id: str | None = None,
    actor_type: str = "system",
    actor_id: str | None = None,
    event_id: str | None = None,
    version: int | None = None,
) -> dict[str, Any]:
    return {
        "event_id": event_id or str(uuid4()),
        "event_type": event_type,
        "occurred_at": datetime.now(UTC).isoformat(),
        "aggregate_type": aggregate_type,
        "aggregate_id": aggregate_id,
        "correlation_id": correlation_id,
        "actor_type": actor_type,
        "actor_id": actor_id or "",
        "actor": {"type": actor_type, "id": actor_id},
        "payload": payload or {},
        "version": version if version is not None else schema_version_for(event_type),
    }
