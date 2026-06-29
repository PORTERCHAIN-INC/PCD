"""Cross-platform identity links — Clerk is the sole IdP."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from porterchain_api.db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class IdentityLink(Base):
    """Maps Clerk user → Porterchain platform record → Fleetbase user (no duplicate passwords)."""

    __tablename__ = "identity_links"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    clerk_user_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True, index=True)
    user_type: Mapped[str] = mapped_column(String(32), index=True)
    platform_user_id: Mapped[str] = mapped_column(String(36), index=True)
    platform_org_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    fleetbase_user_uuid: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    fleetbase_roles: Mapped[list | None] = mapped_column(JSON, nullable=True)
    fleetbase_permissions: Mapped[list | None] = mapped_column(JSON, nullable=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
