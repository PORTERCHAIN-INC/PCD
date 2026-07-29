"""Canonical Porterchain user registry — internal UUID is the business identity.

Phase 2: additive onboarding / workspace columns. ``clerk_user_id`` and exclusive
``role`` remain for compatibility until Phase 3+ multi-role cutover.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from porterchain_api.db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class PorterchainUser(Base):
    """
    Internal user record. Clerk owns credentials; Porterchain owns status + RBAC.

    Prefer ``id`` (UUID) for business FKs. ``clerk_user_id`` is a legacy link column
    retained for rollback; prefer ``identity_links`` issuer/subject (Phase 2+).
    """

    __tablename__ = "porterchain_users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    clerk_user_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    # Display hint only — never used for SpiceDB Check
    role: Mapped[str] = mapped_column(String(64), default="unprovisioned", index=True)
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    onboarding_status: Mapped[str] = mapped_column(String(32), default="not_started", index=True)
    default_workspace: Mapped[str | None] = mapped_column(String(64), nullable=True)
    profile: Mapped[dict] = mapped_column(JSON, default=dict)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
