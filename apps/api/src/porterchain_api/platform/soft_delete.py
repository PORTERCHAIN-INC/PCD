"""Soft delete: one mixin, one global filter, one batch table.

Rows carrying ``SoftDeleteMixin`` disappear from every ORM SELECT once ``deleted_at``
is set. Relationship loads are *not* filtered, so an invoice still shows its
(deleted) customer. Opt out per query with ``execution_options(include_deleted=True)``
or per session with ``session.info["include_deleted"] = True``.
"""

from __future__ import annotations

import uuid
from contextlib import contextmanager
from datetime import datetime
from typing import Iterator

from sqlalchemy import JSON, DateTime, String, event, func
from sqlalchemy.orm import Mapped, ORMExecuteState, Session, declared_attr, mapped_column, with_loader_criteria

from porterchain_api.db import Base


class SoftDeleteMixin:
    @declared_attr
    def deleted_at(cls) -> Mapped[datetime | None]:  # noqa: N805
        return mapped_column(DateTime(timezone=True), nullable=True, index=True)

    @declared_attr
    def deleted_by(cls) -> Mapped[str | None]:  # noqa: N805
        return mapped_column(String(64), nullable=True)

    @declared_attr
    def delete_reason(cls) -> Mapped[str | None]:  # noqa: N805
        return mapped_column(String(500), nullable=True)

    @declared_attr
    def delete_batch_id(cls) -> Mapped[str | None]:  # noqa: N805
        return mapped_column(String(36), nullable=True, index=True)

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None


class DeletedBatch(Base):
    """One row per admin delete action (root + cascaded children). Drives Settings > Deleted items."""

    __tablename__ = "deleted_batches"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    entity: Mapped[str] = mapped_column(String(48), index=True)
    root_id: Mapped[str] = mapped_column(String(36), index=True)
    label: Mapped[str] = mapped_column(String(255), default="")
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    deleted_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    deleted_by_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    deleted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    purge_after: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    # children: [{"entity": "...", "id": "..."}]; side_effects: e.g. revoked api keys to re-enable on restore
    children: Mapped[list] = mapped_column(JSON, default=list)
    side_effects: Mapped[dict] = mapped_column(JSON, default=dict)
    state: Mapped[str] = mapped_column(String(16), default="deleted", index=True)  # deleted|restored|purged
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    outcome: Mapped[dict] = mapped_column(JSON, default=dict)


@event.listens_for(Session, "do_orm_execute")
def _hide_deleted(state: ORMExecuteState) -> None:
    if (
        not state.is_select
        or state.is_column_load
        or state.is_relationship_load
        or state.execution_options.get("include_deleted", False)
        or state.session.info.get("include_deleted", False)
    ):
        return
    state.statement = state.statement.options(
        with_loader_criteria(SoftDeleteMixin, lambda cls: cls.deleted_at.is_(None), include_aliases=True)
    )


@contextmanager
def including_deleted(db: Session) -> Iterator[Session]:
    prev = db.info.get("include_deleted", False)
    db.info["include_deleted"] = True
    try:
        yield db
    finally:
        db.info["include_deleted"] = prev
