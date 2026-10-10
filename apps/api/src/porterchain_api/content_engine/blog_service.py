"""Blog post CRUD. One writer for website content."""

from __future__ import annotations

import re
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from porterchain_api.content_engine.blog_author_service import (
    BLOG_AUTHOR_ID_MAX,
    BlogAuthorMixin,
)
from porterchain_api.website_content_models import BlogPost

BLOG_STATUSES = frozenset({"draft", "published", "archived"})
BLOG_LOCALES = frozenset({"en", "fr"})
BLOG_CATEGORIES = frozenset(
    {
        "logistics",
        "technology",
        "business",
        "route-optimization",
        "supply-chain",
        "same-day-delivery",
        "wholesale",
        "construction",
        "medical",
        "retail",
        "coffee",
    }
)
BLOG_BODY_MAX = 100_000
BLOG_TAG_MAX_COUNT = 32
BLOG_TAG_MAX_LEN = 40
_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_AUTHOR_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_SLUG_CONSTRAINT = "uq_blog_posts_locale_slug"
_WORDS_PER_MINUTE = 200


def reading_minutes_for(body_md: str) -> int:
    words = len((body_md or "").split())
    return max(1, (words + _WORDS_PER_MINUTE - 1) // _WORDS_PER_MINUTE)


class BlogService(BlogAuthorMixin):
    def list_posts(
        self,
        db: Session,
        *,
        locale: str | None = None,
        status: str | None = None,
        category: str | None = None,
        search: str | None = None,
        published_only: bool = False,
        featured: bool | None = None,
        trending: bool | None = None,
        case_study: bool | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[BlogPost]:
        q = db.query(BlogPost)
        if published_only:
            q = q.filter(BlogPost.status == "published")
        elif status:
            q = q.filter(BlogPost.status == status)
        if locale:
            q = q.filter(BlogPost.locale == locale)
        if category:
            q = q.filter(BlogPost.category == category)
        if search:
            term = f"%{search.strip()}%"
            q = q.filter(
                (BlogPost.title.ilike(term))
                | (BlogPost.slug.ilike(term))
                | (BlogPost.description.ilike(term))
            )
        if featured is not None:
            q = q.filter(BlogPost.featured.is_(featured))
        if trending is not None:
            q = q.filter(BlogPost.trending.is_(trending))
        if case_study is not None:
            q = q.filter(BlogPost.case_study.is_(case_study))
        start = max(0, int(offset))
        return (
            q.order_by(BlogPost.published_at.desc().nullslast(), BlogPost.updated_at.desc())
            .offset(start)
            .limit(max(1, limit))
            .all()
        )

    def get_post(self, db: Session, post_id: str) -> BlogPost | None:
        return db.query(BlogPost).filter(BlogPost.id == post_id).first()

    def get_by_locale_slug(self, db: Session, *, locale: str, slug: str) -> BlogPost | None:
        loc, sl = locale.strip().lower(), slug.strip().lower()
        return (
            db.query(BlogPost)
            .filter(BlogPost.locale == loc, BlogPost.slug == sl)
            .first()
        )

    def get_published_by_slug(self, db: Session, *, locale: str, slug: str) -> BlogPost | None:
        loc, sl = locale.strip().lower(), slug.strip().lower()
        return (
            db.query(BlogPost)
            .filter(
                BlogPost.locale == loc,
                BlogPost.slug == sl,
                BlogPost.status == "published",
            )
            .first()
        )

    def _validate_slug(self, slug: str) -> str:
        normalized = slug.strip().lower()
        if not normalized or not _SLUG_RE.match(normalized):
            raise ValueError("blog_invalid_slug")
        return normalized

    def _validate_locale(self, locale: str) -> str:
        normalized = locale.strip().lower()
        if normalized not in BLOG_LOCALES:
            raise ValueError("blog_invalid_locale")
        return normalized

    def _validate_status(self, status: str) -> str:
        normalized = status.strip().lower()
        if normalized not in BLOG_STATUSES:
            raise ValueError("blog_invalid_status")
        return normalized

    def _validate_category(self, category: str) -> str:
        normalized = category.strip().lower()
        if normalized not in BLOG_CATEGORIES:
            raise ValueError("blog_invalid_category")
        return normalized

    def _validate_body(self, body: str) -> str:
        if len(body) > BLOG_BODY_MAX:
            raise ValueError("blog_body_too_long")
        return body

    def _validate_tags(self, tags: list[str]) -> list[str]:
        if len(tags) > BLOG_TAG_MAX_COUNT:
            raise ValueError("blog_tags_invalid")
        out: list[str] = []
        for tag in tags:
            text = str(tag).strip()
            if not text or len(text) > BLOG_TAG_MAX_LEN:
                raise ValueError("blog_tags_invalid")
            out.append(text)
        return out

    def _ensure_unique_slug(
        self, db: Session, *, locale: str, slug: str, exclude_id: str | None = None
    ) -> None:
        q = db.query(BlogPost).filter(BlogPost.locale == locale, BlogPost.slug == slug)
        if exclude_id:
            q = q.filter(BlogPost.id != exclude_id)
        if q.first():
            raise ValueError("blog_slug_exists")

    def _validate_author_id(self, author_id: str) -> str:
        normalized = author_id.strip().lower()
        if (
            not normalized
            or len(normalized) > BLOG_AUTHOR_ID_MAX
            or not _AUTHOR_ID_RE.match(normalized)
        ):
            raise ValueError("blog_invalid_author_id")
        return normalized

    def _normalize_schedule(
        self, when: datetime | None, *, status: str
    ) -> datetime | None:
        """Schedule only applies to drafts; strip tz-naive → UTC."""
        if when is None or status == "published":
            return None
        if when.tzinfo is None:
            return when.replace(tzinfo=timezone.utc)
        return when.astimezone(timezone.utc)

    def _commit(self, db: Session) -> None:
        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            if _SLUG_CONSTRAINT in str(getattr(exc, "orig", exc)):
                raise ValueError("blog_slug_exists") from exc
            raise

    def create_post(
        self,
        db: Session,
        *,
        slug: str,
        locale: str,
        title: str,
        description: str,
        body_md: str,
        category: str,
        author_id: str,
        status: str,
        featured: bool,
        trending: bool,
        case_study: bool,
        on_time_percent: str | None,
        cost_delta_percent: str | None,
        volume_metric: str | None,
        tags: list[str],
        published_at: date | None,
        created_by: str | None,
        cover_image_url: str | None = None,
        scheduled_publish_at: datetime | None = None,
    ) -> BlogPost:
        loc = self._validate_locale(locale)
        sl = self._validate_slug(slug)
        st = self._validate_status(status)
        cat = self._validate_category(category)
        body = self._validate_body(body_md)
        clean_tags = self._validate_tags(tags)
        self._ensure_unique_slug(db, locale=loc, slug=sl)
        pub_date = published_at
        if st == "published" and pub_date is None:
            pub_date = datetime.now(timezone.utc).date()
        record = BlogPost(
            slug=sl,
            locale=loc,
            title=title.strip(),
            description=description.strip(),
            body_md=body,
            category=cat,
            author_id=author_id.strip() or "porterchain",
            status=st,
            featured=featured,
            trending=trending,
            case_study=case_study,
            on_time_percent=on_time_percent,
            cost_delta_percent=cost_delta_percent,
            volume_metric=volume_metric,
            tags=clean_tags,
            cover_image_url=(cover_image_url or "").strip() or None,
            published_at=pub_date,
            scheduled_publish_at=self._normalize_schedule(scheduled_publish_at, status=st),
            created_by=created_by,
        )
        db.add(record)
        self._commit(db)
        db.refresh(record)
        return record

    def update_post(
        self,
        db: Session,
        post_id: str,
        *,
        slug: str | None = None,
        locale: str | None = None,
        title: str | None = None,
        description: str | None = None,
        body_md: str | None = None,
        category: str | None = None,
        author_id: str | None = None,
        status: str | None = None,
        featured: bool | None = None,
        trending: bool | None = None,
        case_study: bool | None = None,
        on_time_percent: str | None = None,
        cost_delta_percent: str | None = None,
        volume_metric: str | None = None,
        tags: list[str] | None = None,
        published_at: date | None = None,
        clear_published_at: bool = False,
        cover_image_url: str | None = None,
        clear_cover_image_url: bool = False,
        scheduled_publish_at: datetime | None = None,
        clear_scheduled_publish_at: bool = False,
    ) -> BlogPost:
        record = self.get_post(db, post_id)
        if not record:
            raise LookupError("blog_post_not_found")

        next_locale = self._validate_locale(locale) if locale is not None else record.locale
        next_slug = self._validate_slug(slug) if slug is not None else record.slug
        if slug is not None or locale is not None:
            self._ensure_unique_slug(db, locale=next_locale, slug=next_slug, exclude_id=post_id)

        if slug is not None:
            record.slug = next_slug
        if locale is not None:
            record.locale = next_locale
        if title is not None:
            record.title = title.strip()
        if description is not None:
            record.description = description.strip()
        if body_md is not None:
            record.body_md = self._validate_body(body_md)
        if category is not None:
            record.category = self._validate_category(category)
        if author_id is not None:
            record.author_id = author_id.strip() or "porterchain"
        if status is not None:
            st = self._validate_status(status)
            record.status = st
            if st == "published" and record.published_at is None and published_at is None:
                record.published_at = datetime.now(timezone.utc).date()
            if st == "published":
                record.scheduled_publish_at = None
        if featured is not None:
            record.featured = featured
        if trending is not None:
            record.trending = trending
        if case_study is not None:
            record.case_study = case_study
        if on_time_percent is not None:
            record.on_time_percent = on_time_percent or None
        if cost_delta_percent is not None:
            record.cost_delta_percent = cost_delta_percent or None
        if volume_metric is not None:
            record.volume_metric = volume_metric or None
        if tags is not None:
            record.tags = self._validate_tags(tags)
        if clear_published_at:
            record.published_at = None
        elif published_at is not None:
            record.published_at = published_at
        if clear_cover_image_url:
            record.cover_image_url = None
        elif cover_image_url is not None:
            record.cover_image_url = cover_image_url.strip() or None
        if clear_scheduled_publish_at:
            record.scheduled_publish_at = None
        elif scheduled_publish_at is not None:
            record.scheduled_publish_at = self._normalize_schedule(
                scheduled_publish_at, status=record.status
            )

        self._commit(db)
        db.refresh(record)
        return record

    def delete_post(self, db: Session, post_id: str) -> None:
        record = self.get_post(db, post_id)
        if not record:
            raise LookupError("blog_post_not_found")
        db.delete(record)
        self._commit(db)

    def publish_due_posts(
        self, db: Session, *, now: datetime | None = None, limit: int = 20
    ) -> list[BlogPost]:
        """Flip due draft schedules to published. Returns updated rows."""
        clock = now or datetime.now(timezone.utc)
        if clock.tzinfo is None:
            clock = clock.replace(tzinfo=timezone.utc)
        due = (
            db.query(BlogPost)
            .filter(
                BlogPost.status == "draft",
                BlogPost.scheduled_publish_at.isnot(None),
                BlogPost.scheduled_publish_at <= clock,
            )
            .order_by(BlogPost.scheduled_publish_at.asc())
            .limit(max(1, min(int(limit), 100)))
            .all()
        )
        if not due:
            return []
        today = clock.date()
        for record in due:
            record.status = "published"
            if record.published_at is None:
                record.published_at = today
            record.scheduled_publish_at = None
        self._commit(db)
        for record in due:
            db.refresh(record)
        return due

    def serialize(self, record: BlogPost, *, include_body: bool = True) -> dict[str, Any]:
        scheduled = record.scheduled_publish_at
        out: dict[str, Any] = {
            "id": record.id,
            "slug": record.slug,
            "locale": record.locale,
            "title": record.title,
            "description": record.description,
            "category": record.category,
            "author_id": record.author_id,
            "status": record.status,
            "featured": record.featured,
            "trending": record.trending,
            "case_study": record.case_study,
            "on_time_percent": record.on_time_percent,
            "cost_delta_percent": record.cost_delta_percent,
            "volume_metric": record.volume_metric,
            "tags": record.tags or [],
            "cover_image_url": record.cover_image_url,
            "published_at": record.published_at.isoformat() if record.published_at else None,
            "scheduled_publish_at": scheduled.isoformat() if scheduled else None,
            "reading_minutes": reading_minutes_for(record.body_md or ""),
            "created_by": record.created_by,
            "created_at": record.created_at,
            "updated_at": record.updated_at,
        }
        if include_body:
            out["body_md"] = record.body_md
        return out

    def serialize_public(self, record: BlogPost, *, include_body: bool = True) -> dict[str, Any]:
        data = self.serialize(record, include_body=include_body)
        data.pop("created_by", None)
        data.pop("scheduled_publish_at", None)
        return data

# Re-exports kept for existing importers (integration).
from datetime import timezone  # noqa: E402, F401
