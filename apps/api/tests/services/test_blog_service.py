"""BlogService + blog media — professional coverage for CMS (§2.1.11)."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from porterchain_api.content_engine.blog_media import (
    blog_media_dir,
    public_media_path,
    resolve_media_file,
    save_blog_image,
)
from porterchain_api.content_engine.blog_service import BlogService
from porterchain_api.website_content_models import BlogPost


def _slug(prefix: str = "post") -> str:
    return f"{prefix}-{uuid4().hex[:10]}"


def _create(
    db: Session,
    *,
    slug: str | None = None,
    locale: str = "en",
    title: str = "GTA Same-Day Capacity",
    status: str = "draft",
    category: str = "logistics",
    published_at: date | None = None,
    cover_image_url: str | None = None,
) -> BlogPost:
    return BlogService().create_post(
        db,
        slug=slug or _slug("gta"),
        locale=locale,
        title=title,
        description="Capacity when docks slip.",
        body_md="# Hello\n\nBody.",
        category=category,
        author_id="porterchain",
        status=status,
        featured=False,
        trending=False,
        case_study=False,
        on_time_percent=None,
        cost_delta_percent=None,
        volume_metric=None,
        tags=["gta", "capacity"],
        published_at=published_at,
        created_by="admin-1",
        cover_image_url=cover_image_url,
    )


def test_create_list_get_and_serialize(db: Session) -> None:
    svc = BlogService()
    slug = _slug("capacity")
    post = _create(db, slug=slug, status="published")
    assert post.status == "published"
    assert post.published_at is not None
    assert post.slug == slug

    listed = svc.list_posts(db, locale="en", published_only=True, limit=50)
    assert any(p.id == post.id for p in listed)
    capped = svc.list_posts(db, locale="en", limit=1)
    assert len(capped) == 1

    by_id = svc.get_post(db, post.id)
    assert by_id is not None
    assert by_id.title == "GTA Same-Day Capacity"

    by_slug = svc.get_by_locale_slug(db, locale="EN", slug=slug.upper())
    assert by_slug is not None and by_slug.id == post.id

    published = svc.get_published_by_slug(db, locale="EN", slug=slug.upper())
    assert published is not None

    full = svc.serialize(post, include_body=True)
    assert full["body_md"].startswith("# Hello")
    assert full["tags"] == ["gta", "capacity"]
    assert full["published_at"] is not None

    slim = svc.serialize(post, include_body=False)
    assert "body_md" not in slim
    public = svc.serialize_public(post, include_body=True)
    assert "created_by" not in public
    assert public["body_md"].startswith("# Hello")


def test_list_filters_status_category_search(db: Session) -> None:
    svc = BlogService()
    draft = _create(db, slug=_slug("draft"), status="draft", category="technology")
    live = _create(
        db,
        slug=_slug("live"),
        status="published",
        category="construction",
        title="Construction Dock Windows",
    )
    archived = _create(db, slug=_slug("old"), status="archived", category="retail")

    assert any(p.id == draft.id for p in svc.list_posts(db, status="draft"))
    assert any(p.id == live.id for p in svc.list_posts(db, category="construction"))
    assert any(p.id == live.id for p in svc.list_posts(db, search="Dock"))
    assert any(p.id == archived.id for p in svc.list_posts(db, status="archived"))
    assert all(p.status == "published" for p in svc.list_posts(db, published_only=True))


def test_validation_errors(db: Session) -> None:
    with pytest.raises(ValueError, match="blog_invalid_slug"):
        _create(db, slug="Bad Slug!")
    with pytest.raises(ValueError, match="blog_invalid_locale"):
        _create(db, locale="de")
    with pytest.raises(ValueError, match="blog_invalid_status"):
        _create(db, status="pending")
    with pytest.raises(ValueError, match="blog_invalid_category"):
        _create(db, category="not-a-real-category")

    slug = _slug("unique")
    _create(db, slug=slug, locale="en")
    with pytest.raises(ValueError, match="blog_slug_exists"):
        _create(db, slug=slug, locale="en")


def test_update_publish_cover_and_delete(db: Session) -> None:
    svc = BlogService()
    post = _create(db, slug=_slug("update"), status="draft", published_at=None)
    assert post.published_at is None

    updated = svc.update_post(
        db,
        post.id,
        title=" Updated Title ",
        description=" Updated desc ",
        body_md="## Revised",
        category="wholesale",
        author_id="  ",
        status="published",
        featured=True,
        trending=True,
        case_study=True,
        on_time_percent="98",
        cost_delta_percent="-12",
        volume_metric="40 stops/day",
        tags=["wholesale"],
        cover_image_url=" /v1/public/blog/media/cover.webp ",
    )
    assert updated.title == "Updated Title"
    assert updated.description == "Updated desc"
    assert updated.category == "wholesale"
    assert updated.author_id == "porterchain"
    assert updated.status == "published"
    assert updated.published_at is not None
    assert updated.featured is True
    assert updated.cover_image_url == "/v1/public/blog/media/cover.webp"

    next_slug = _slug("updated")
    cleared = svc.update_post(
        db,
        post.id,
        clear_published_at=True,
        clear_cover_image_url=True,
        on_time_percent="",
        cost_delta_percent="",
        volume_metric="",
        slug=next_slug,
        locale="fr",
        published_at=date(2026, 1, 15),
    )
    # clear_published_at takes precedence over published_at in the same call.
    assert cleared.published_at is None
    assert cleared.cover_image_url is None
    assert cleared.slug == next_slug
    assert cleared.locale == "fr"
    assert cleared.on_time_percent is None

    with_date = svc.update_post(db, post.id, published_at=date(2026, 2, 1))
    assert with_date.published_at == date(2026, 2, 1)

    with pytest.raises(LookupError, match="blog_post_not_found"):
        svc.update_post(db, "missing-id", title="x")

    svc.delete_post(db, post.id)
    assert svc.get_post(db, post.id) is None

    with pytest.raises(LookupError, match="blog_post_not_found"):
        svc.delete_post(db, post.id)


def test_slug_unique_on_update_excludes_self(db: Session) -> None:
    svc = BlogService()
    alpha = _slug("alpha")
    beta = _slug("beta")
    a = _create(db, slug=alpha, locale="en")
    _create(db, slug=beta, locale="en")

    # Same slug on self is fine
    same = svc.update_post(db, a.id, slug=alpha, title="Alpha again")
    assert same.slug == alpha

    with pytest.raises(ValueError, match="blog_slug_exists"):
        svc.update_post(db, a.id, slug=beta)


def test_blog_media_save_and_resolve(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BLOG_MEDIA_DIR", str(tmp_path))
    assert blog_media_dir() == tmp_path

    url = save_blog_image(
        filename="hero.PNG",
        content=b"\x89PNG\r\n\x1a\n" + b"0" * 64,
        content_type="image/png",
    )
    assert url.startswith("/v1/public/blog/media/")
    assert public_media_path("x.webp") == "/v1/public/blog/media/x.webp"

    name = url.rsplit("/", 1)[-1]
    resolved = resolve_media_file(name)
    assert resolved is not None and resolved.is_file()

    assert resolve_media_file("../escape.png") is None
    assert resolve_media_file("missing.webp") is None

    with pytest.raises(ValueError, match="blog_media_too_large"):
        save_blog_image(filename="big.jpg", content=b"x" * (5 * 1024 * 1024 + 1), content_type="image/jpeg")
    with pytest.raises(ValueError, match="blog_media_invalid_type"):
        save_blog_image(filename="note.txt", content=b"hi", content_type="text/plain")
    with pytest.raises(ValueError, match="blog_media_invalid_type"):
        save_blog_image(filename="pic.jpg", content=b"hi", content_type="application/octet-stream")
