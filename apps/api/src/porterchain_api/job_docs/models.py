"""Pickup document checklist captures + per-order/per-parcel instructions (with edit log and acks)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from porterchain_api.db import Base


class PickupDocument(Base):
    __tablename__ = "pickup_documents"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    order_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    route_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    doc_type: Mapped[str] = mapped_column(String(32))
    #: captured | missing (exception raised)
    status: Mapped[str] = mapped_column(String(16), default="captured")
    media_key: Mapped[str | None] = mapped_column(String(256), nullable=True)
    scan_code: Mapped[str | None] = mapped_column(String(128), nullable=True)
    seal_no: Mapped[str | None] = mapped_column(String(64), nullable=True)
    shipper_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    shipper_signature_key: Mapped[str | None] = mapped_column(String(256), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    captured_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class JobInstruction(Base):
    __tablename__ = "job_instructions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    order_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    route_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    parcel_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    author_role: Mapped[str] = mapped_column(String(16))  # admin | merchant | customer | partner
    author_id: Mapped[str] = mapped_column(String(64))
    text: Mapped[str] = mapped_column(Text)
    photo_key: Mapped[str | None] = mapped_column(String(256), nullable=True)
    priority: Mapped[str] = mapped_column(String(16), default="normal")  # normal | high | must_read
    visibility: Mapped[list] = mapped_column(JSON, default=list)
    steps: Mapped[list] = mapped_column(JSON, default=list)  # pickup | scan | delivery
    #: Business data (prices, PO terms, margins) — never shown to drivers (privacy rule).
    business: Mapped[bool] = mapped_column(Boolean, default=False)
    deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class InstructionEdit(Base):
    __tablename__ = "job_instruction_edits"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    instruction_id: Mapped[str] = mapped_column(String(36), index=True)
    author_role: Mapped[str] = mapped_column(String(16))
    author_id: Mapped[str] = mapped_column(String(64))
    action: Mapped[str] = mapped_column(String(16))  # create | edit | delete
    before: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    after: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class InstructionAck(Base):
    __tablename__ = "job_instruction_acks"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    instruction_id: Mapped[str] = mapped_column(String(36), index=True)
    version: Mapped[int] = mapped_column(Integer)
    driver_id: Mapped[str] = mapped_column(String(36), index=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
