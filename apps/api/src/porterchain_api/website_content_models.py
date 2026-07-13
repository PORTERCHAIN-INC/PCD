"""Website-managed content — blog posts (admin CRUD, public read)."""

import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from porterchain_api.db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class BlogPost(Base):
    __tablename__ = "blog_posts"
    __table_args__ = (UniqueConstraint("locale", "slug", name="uq_blog_posts_locale_slug"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    slug: Mapped[str] = mapped_column(String(160), index=True)
    locale: Mapped[str] = mapped_column(String(8), index=True)
    title: Mapped[str] = mapped_column(String(512))
    description: Mapped[str] = mapped_column(Text, default="")
    body_md: Mapped[str] = mapped_column(Text, default="")
    category: Mapped[str] = mapped_column(String(64), default="logistics", index=True)
    author_id: Mapped[str] = mapped_column(String(64), default="porterchain")
    status: Mapped[str] = mapped_column(String(32), default="draft", index=True)
    featured: Mapped[bool] = mapped_column(Boolean, default=False)
    trending: Mapped[bool] = mapped_column(Boolean, default=False)
    case_study: Mapped[bool] = mapped_column(Boolean, default=False)
    on_time_percent: Mapped[str | None] = mapped_column(String(32), nullable=True)
    cost_delta_percent: Mapped[str | None] = mapped_column(String(32), nullable=True)
    volume_metric: Mapped[str | None] = mapped_column(String(128), nullable=True)
    tags: Mapped[list] = mapped_column(JSON, default=list)
    cover_image_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    published_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
