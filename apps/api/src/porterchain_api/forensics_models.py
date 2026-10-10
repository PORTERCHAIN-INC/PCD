"""Tamper-evident (hash-chained, append-only) security audit trail + signed checkpoints."""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from porterchain_api.db import Base


class ForensicAuditEntry(Base):
    __tablename__ = "forensic_audit_chain"

    seq: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=False)
    at: Mapped[str] = mapped_column(String(40))  # ISO-8601 UTC, part of the hash
    category: Mapped[str] = mapped_column(String(32), index=True)
    action: Mapped[str] = mapped_column(String(128), index=True)
    actor: Mapped[str | None] = mapped_column(String(128), nullable=True)
    target_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    target_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    outcome: Mapped[str] = mapped_column(String(16), default="ok")
    source: Mapped[str] = mapped_column(String(48))  # admin_audit_logs:<id> | event
    detail: Mapped[dict] = mapped_column(JSON, default=dict)  # masked, no secrets
    prev_hash: Mapped[str] = mapped_column(String(64))
    hash: Mapped[str] = mapped_column(String(64), unique=True)


class ForensicCheckpoint(Base):
    __tablename__ = "forensic_checkpoints"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    seq: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"))
    head_hash: Mapped[str] = mapped_column(String(64))
    key_id: Mapped[str] = mapped_column(String(32))
    algorithm: Mapped[str] = mapped_column(String(16))  # ed25519
    signature: Mapped[str] = mapped_column(Text)
