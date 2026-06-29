"""Persistence for the Fleetbase sync engine — retry + error (dead-letter) queues.

Per masterrule.md these are Porterchain-owned integration records; the bridge
to Fleetbase always flows through the adapter. SyncJob captures every outbound
or inbound sync attempt so failures are retried and never silently lost.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from porterchain_api.db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class FleetbaseSyncJob(Base):
    """A single Fleetbase sync unit of work with retry + dead-letter tracking."""

    __tablename__ = "fleetbase_sync_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    direction: Mapped[str] = mapped_column(String(16), index=True)  # outbound | inbound
    kind: Mapped[str] = mapped_column(String(32), index=True)  # order|tracking|pod|driver|cancellation|return|damage|claim
    order_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    fleetbase_order_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)

    status: Mapped[str] = mapped_column(String(16), default="pending", index=True)  # pending|retrying|done|dead
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=5)
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class FleetbaseSyncAudit(Base):
    """Immutable audit trail of every sync step (outbound + inbound)."""

    __tablename__ = "fleetbase_sync_audit"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    direction: Mapped[str] = mapped_column(String(16), index=True)
    kind: Mapped[str] = mapped_column(String(32), index=True)
    order_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    fleetbase_order_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(16))  # ok | error | skipped
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
