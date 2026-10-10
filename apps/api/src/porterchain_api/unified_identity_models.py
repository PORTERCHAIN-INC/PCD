"""Unified identity tables — emails, access audit, migration bookkeeping.

Authorization lives in SpiceDB. These models are not an ACL Check source.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from porterchain_api.db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class UserEmail(Base):
    """Verified / candidate emails for matching — never used alone for authorization."""

    __tablename__ = "user_emails"
    __table_args__ = (
        UniqueConstraint("user_id", "normalized_email", name="uq_user_emails_user_email"),
        Index("ix_user_emails_normalized_email", "normalized_email"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("porterchain_users.id"), index=True)
    normalized_email: Mapped[str] = mapped_column(String(320))
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    source: Mapped[str] = mapped_column(String(64), default="clerk")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class AccessAuditLog(Base):
    """Identity / authorization audit (no tokens or secrets). Complements AdminAuditLog."""

    __tablename__ = "access_audit_logs"
    __table_args__ = (
        Index("ix_access_audit_logs_actor", "actor_user_id"),
        Index("ix_access_audit_logs_action", "action"),
        Index("ix_access_audit_logs_created", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    actor_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    action: Mapped[str] = mapped_column(String(128))
    resource_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    resource_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    outcome: Mapped[str] = mapped_column(String(32))  # allowed | denied | error
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class IdentityMigrationRun(Base):
    """Bookkeeping for Clerk consolidation import tooling."""

    __tablename__ = "identity_migration_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    label: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(32), default="planned", index=True)
    dry_run: Mapped[bool] = mapped_column(Boolean, default=True)
    source_summary: Mapped[dict] = mapped_column(JSON, default=dict)
    counts: Mapped[dict] = mapped_column(JSON, default=dict)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class IdentityMigrationRecord(Base):
    __tablename__ = "identity_migration_records"
    __table_args__ = (
        Index("ix_identity_migration_records_run", "run_id"),
        Index("ix_identity_migration_records_source", "source_app", "source_clerk_user_id"),
        Index("ix_identity_migration_records_internal", "internal_user_id"),
        UniqueConstraint(
            "run_id",
            "source_app",
            "source_clerk_user_id",
            name="uq_identity_migration_records_run_source",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    run_id: Mapped[str] = mapped_column(ForeignKey("identity_migration_runs.id"), index=True)
    source_app: Mapped[str] = mapped_column(String(32))
    source_issuer: Mapped[str | None] = mapped_column(String(512), nullable=True)
    source_clerk_user_id: Mapped[str] = mapped_column(String(128))
    internal_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    target_clerk_user_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    conflict_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    proposed_roles: Mapped[list] = mapped_column(JSON, default=list)
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
