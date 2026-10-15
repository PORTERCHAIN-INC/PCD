"""Booking attachments: files a merchant or customer attaches to a stop.

Bytes live in Postgres (private, never public-URL'd); downloads go only through
authenticated endpoints with ``Cache-Control: no-store``.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, LargeBinary, String, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from porterchain_api.db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class BookingAttachment(Base):
    __tablename__ = "booking_attachments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    # Null order_id = reusable location template (e.g. "Milton warehouse pickup authorization").
    order_id: Mapped[str | None] = mapped_column(ForeignKey("orders.id"), nullable=True, index=True)
    merchant_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    customer_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    stop: Mapped[str] = mapped_column(String(16), default="pickup")  # pickup | dropoff
    kind: Mapped[str] = mapped_column(String(32))
    filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(64))
    size_bytes: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64))
    content: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    required_at_stop: Mapped[bool] = mapped_column(Boolean, default=False)
    location_key: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    is_location_template: Mapped[bool] = mapped_column(Boolean, default=False)
    source_template_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    uploaded_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    first_viewed_by_driver_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    shown_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    shown_by_driver_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    proof_content: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    proof_content_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # One-time short-lived link (5 min) so the phone's built-in viewer can open a PDF full-screen.
    link_token_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    link_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    purged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class BookingAttachmentEvent(Base):
    """Append-only audit trail: upload, view, download, shown, delete, purge."""

    __tablename__ = "booking_attachment_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    attachment_id: Mapped[str] = mapped_column(String(36), index=True)
    order_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    actor_type: Mapped[str] = mapped_column(String(16))  # merchant | customer | driver | staff | system
    actor_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    action: Mapped[str] = mapped_column(String(32))
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
