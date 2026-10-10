"""Auth identity links — Clerk subject ↔ internal user (not an ACL table).

``user_type`` is a display/compat hint; authorization Checks use SpiceDB.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func, text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.schema import Index

from porterchain_api.db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class IdentityLink(Base):
    """Maps IdP subject → Porterchain user."""

    __tablename__ = "identity_links"
    __table_args__ = (
        Index(
            "uq_identity_links_provider_issuer_subject",
            "provider",
            "issuer",
            "subject",
            unique=True,
            postgresql_where=text("subject IS NOT NULL"),
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    clerk_user_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    # Phase 2 auth_identities fields (nullable until dual-write / backfill)
    provider: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    issuer: Mapped[str | None] = mapped_column(String(512), nullable=True, index=True)
    subject: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    is_current: Mapped[bool] = mapped_column(Boolean, default=True)
    is_legacy: Mapped[bool] = mapped_column(Boolean, default=False)
    linked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deactivated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True, index=True)
    # Legacy exclusive class hint — do not use for multi-role authz
    user_type: Mapped[str] = mapped_column(String(32), index=True)
    platform_user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("porterchain_users.id"), index=True
    )
    platform_org_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
