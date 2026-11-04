"""Organisation tables (doc 70 §3). ``organisations.id`` equals ``merchants.id`` for migrated merchants."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from porterchain_api.db import Base


class Organisation(Base):
    __tablename__ = "organisations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    public_id: Mapped[str] = mapped_column(String(16), unique=True)
    legal_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    display_name: Mapped[str] = mapped_column(String(255))
    business_type: Mapped[str] = mapped_column(String(32), index=True)
    subtype: Mapped[str | None] = mapped_column(String(32), nullable=True)
    role_flags: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(16), default="lead", index=True)
    locale: Mapped[str] = mapped_column(String(8), default="en")
    gst_hst_number: Mapped[str | None] = mapped_column(String(32), nullable=True)
    parent_org_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    merchant_id: Mapped[str | None] = mapped_column(String(36), nullable=True, unique=True)
    needs_review: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class OrgCapability(Base):
    __tablename__ = "org_capabilities"

    org_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    capability: Mapped[str] = mapped_column(String(48), primary_key=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    params: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    source: Mapped[str] = mapped_column(String(16), default="default")  # default|ravi|contract


class OperatingProfile(Base):
    __tablename__ = "org_operating_profiles"
    __table_args__ = (UniqueConstraint("org_id", "version", name="uq_org_operating_profile_version"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    org_id: Mapped[str] = mapped_column(String(36), index=True)
    version: Mapped[int] = mapped_column(Integer)
    pickup_mode: Mapped[str] = mapped_column(String(24))
    pickup_params: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    tracking_mode: Mapped[str] = mapped_column(String(8))
    label_mode: Mapped[str] = mapped_column(String(8))
    relabel_rule: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    barcode_formats: Mapped[list | None] = mapped_column(JSON, nullable=True)
    ref_schema: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ExternalRef(Base):
    __tablename__ = "org_external_refs"
    __table_args__ = (UniqueConstraint("org_id", "ref_type", "ref_value", name="uq_org_external_ref"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    org_id: Mapped[str] = mapped_column(String(36), index=True)
    ref_type: Mapped[str] = mapped_column(String(16))
    ref_value: Mapped[str] = mapped_column(String(255))
    entity_type: Mapped[str] = mapped_column(String(32))
    entity_id: Mapped[str] = mapped_column(String(64), index=True)
    source: Mapped[str] = mapped_column(String(16), default="api")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
