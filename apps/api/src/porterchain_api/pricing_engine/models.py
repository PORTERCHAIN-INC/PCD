"""Pricing admin tables (doc 72 §9.5): versioned rate cards, org pricing mode, audit."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from porterchain_api.db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class PricingRateCard(Base):
    __tablename__ = "pricing_rate_cards"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    code: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(160))
    kind: Mapped[str] = mapped_column(String(16), default="standard")  # standard|business_type|custom
    org_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    contract_document_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PricingRateCardVersion(Base):
    __tablename__ = "pricing_rate_card_versions"
    __table_args__ = (UniqueConstraint("rate_card_id", "version", name="uq_pricing_rate_card_version"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    rate_card_id: Mapped[str] = mapped_column(
        ForeignKey("pricing_rate_cards.id", ondelete="CASCADE"), index=True
    )
    version: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(16), default="draft", index=True)  # draft|published|retired
    effective_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    lines: Mapped[dict] = mapped_column(JSON)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    published_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PricingOrgPricing(Base):
    __tablename__ = "pricing_org_pricing"

    org_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    mode: Mapped[str] = mapped_column(String(16), default="standard")  # standard|custom
    preset_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    preset_per_stop_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    flat_parcel_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    band_overrides: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    rate_card_id: Mapped[str | None] = mapped_column(
        ForeignKey("pricing_rate_cards.id", ondelete="SET NULL"), nullable=True
    )
    contract_document_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    red_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    effective_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class PricingAudit(Base):
    __tablename__ = "pricing_audit"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    entity: Mapped[str] = mapped_column(String(32), index=True)
    entity_id: Mapped[str] = mapped_column(String(64), index=True)
    action: Mapped[str] = mapped_column(String(32))
    diff: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    actor_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


class PricingSentQuote(Base):
    """A priced quote emailed to a lead / org (doc 72 §9.3). Valid 72 h, then expires."""

    __tablename__ = "pricing_sent_quotes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    token: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    org_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    lead_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    email: Mapped[str] = mapped_column(String(320))
    audience: Mapped[str] = mapped_column(String(16), default="b2b")
    card_version: Mapped[int] = mapped_column(Integer, default=1)
    payload: Mapped[dict] = mapped_column(JSON)
    total_cents: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(16), default="sent", index=True)  # sent|accepted|expired|void
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PricingOrderAdjustment(Base):
    """Per-order price adjustment with role limits and a reason (doc 72 §9.4)."""

    __tablename__ = "pricing_order_adjustments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    order_id: Mapped[str] = mapped_column(String(36), index=True)
    cents: Mapped[int] = mapped_column(Integer)
    category: Mapped[str] = mapped_column(String(32))
    reason: Mapped[str] = mapped_column(Text)
    actor_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    actor_role: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
