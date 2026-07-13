"""Public blog read API — published posts for website SSG + media files."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from porterchain_api.admin_engine.blog_media import resolve_media_file
from porterchain_api.admin_engine.blog_service import AdminBlogService
from porterchain_api.db import get_db
from porterchain_api.platform.pagination import DEFAULT_LIST_LIMIT, MAX_LIST_LIMIT
from porterchain_api.schemas_public import PublicBlogPostItem, PublicBlogPostMeta

router = APIRouter(prefix="/v1/public/blog", tags=["public-blog"])
_blog = AdminBlogService()

_MEDIA_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
}


def _meta(record) -> PublicBlogPostMeta:
    data = _blog.serialize(record, include_body=False)
    return PublicBlogPostMeta(**data)


def _full(record) -> PublicBlogPostItem:
    data = _blog.serialize(record, include_body=True)
    return PublicBlogPostItem(**data)


@router.get("/posts", response_model=list[PublicBlogPostMeta])
def list_published_posts(
    db: Session = Depends(get_db),
    locale: Annotated[str, Query(min_length=2, max_length=8)] = "en",
    category: str | None = None,
    limit: int = Query(DEFAULT_LIST_LIMIT, ge=1, le=MAX_LIST_LIMIT),
) -> list[PublicBlogPostMeta]:
    rows = _blog.list_posts(
        db,
        locale=locale.strip().lower(),
        category=category,
        published_only=True,
        limit=limit,
    )
    return [_meta(row) for row in rows]


@router.get("/posts/{slug}", response_model=PublicBlogPostItem)
def get_published_post(
    slug: str,
    db: Session = Depends(get_db),
    locale: Annotated[str, Query(min_length=2, max_length=8)] = "en",
) -> PublicBlogPostItem:
    record = _blog.get_published_by_slug(db, locale=locale.strip().lower(), slug=slug.strip().lower())
    if not record:
        raise HTTPException(status_code=404, detail="blog_post_not_found")
    return _full(record)


@router.get("/media/{filename}")
def get_blog_media(filename: str) -> FileResponse:
    path = resolve_media_file(filename)
    if not path:
        raise HTTPException(status_code=404, detail="blog_media_not_found")
    media_type = _MEDIA_TYPES.get(path.suffix.lower(), "application/octet-stream")
    return FileResponse(
        path,
        media_type=media_type,
        headers={"Cache-Control": "public, max-age=31536000, immutable"},
    )
