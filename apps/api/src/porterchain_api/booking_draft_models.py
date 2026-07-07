"""Persistent booking draft — server-side checkout lifecycle."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from porterchain_api.db import Base
from porterchain_api.domain.states import BookingDraftState


def _uuid() -> str:
    return str(uuid.uuid4())


class BookingDraft(Base):
    __tablename__ = "booking_drafts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(String(64), index=True)
    customer_id: Mapped[str | None] = mapped_column(ForeignKey("customers.id"), nullable=True, index=True)
    quote_id: Mapped[str | None] = mapped_column(ForeignKey("quotes.id"), nullable=True, unique=True, index=True)
    state: Mapped[str] = mapped_column(
        String(32), default=BookingDraftState.DRAFT.value, index=True
    )
    current_step: Mapped[str] = mapped_column(String(32), default="details")

    pickup: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    dropoff: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    additional_stops: Mapped[list | None] = mapped_column(JSON, nullable=True)
    vehicle_class: Mapped[str | None] = mapped_column(String(32), nullable=True)
    package_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    weight_kg: Mapped[float | None] = mapped_column(nullable=True)
    dimensions: Mapped[str | None] = mapped_column(String(128), nullable=True)
    declared_value_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    special_instructions: Mapped[str | None] = mapped_column(Text, nullable=True)

    pricing_breakdown: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    taxes_cents: Mapped[int] = mapped_column(Integer, default=0)
    discounts_cents: Mapped[int] = mapped_column(Integer, default=0)
    promo_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    amount_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    currency: Mapped[str] = mapped_column(String(8), default="cad")
    distance_meters: Mapped[int | None] = mapped_column(Integer, nullable=True)

    estimated_pickup: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    estimated_delivery: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    schedule_mode: Mapped[str] = mapped_column(String(16), default="now")

    stripe_checkout_session_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    booking_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    order_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)

    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    audits: Mapped[list["BookingDraftAudit"]] = relationship(
        back_populates="booking_draft", order_by="BookingDraftAudit.occurred_at"
    )


class BookingDraftAudit(Base):
    __tablename__ = "booking_draft_audits"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    booking_draft_id: Mapped[str] = mapped_column(ForeignKey("booking_drafts.id"), index=True)
    from_state: Mapped[str | None] = mapped_column(String(32), nullable=True)
    to_state: Mapped[str] = mapped_column(String(32))
    event_label: Mapped[str] = mapped_column(String(64))
    actor_type: Mapped[str] = mapped_column(String(32), default="system")
    actor_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    booking_draft: Mapped[BookingDraft] = relationship(back_populates="audits")
