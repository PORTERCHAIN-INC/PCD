"""Admin blog CMS — create, update, delete website posts + media upload."""

from typing import Annotated

from fastapi import Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from porterchain_api.admin_engine.platform_settings import document_allowed_types, document_max_bytes
from porterchain_api.auth.admin import get_admin_context
from porterchain_api.admin_engine.rbac import AdminContext, require_module
from porterchain_api.config import Settings, get_settings
from porterchain_api.content_engine.blog_media import save_blog_image
from porterchain_api.content_engine.blog_revalidate import notify_blog_revalidate
from porterchain_api.db import get_db
from porterchain_api.platform.pagination import DEFAULT_LIST_LIMIT, MAX_LIST_LIMIT
from porterchain_api.routers.admin._deps import (
    BlogPostCreateRequest,
    BlogPostItem,
    BlogPostUpdateRequest,
    _blog,
    _perm,
    log_admin_audit,
    router,
)


_IMAGE_EXT = frozenset({"jpg", "jpeg", "png", "webp", "gif"})


def _serialize(record) -> BlogPostItem:
    return BlogPostItem(**_blog.serialize(record, include_body=True))


def _bump_website(settings: Settings, record) -> None:
    """Invalidate website blog cache after CMS mutations."""
    notify_blog_revalidate(
        settings,
        locale=getattr(record, "locale", None),
        slug=getattr(record, "slug", None),
    )


@router.get("/blog/posts", response_model=list[BlogPostItem])
def list_blog_posts(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    locale: str | None = None,
    status: str | None = None,
    category: str | None = None,
    search: str | None = None,
    limit: int = Query(DEFAULT_LIST_LIMIT, ge=1, le=MAX_LIST_LIMIT),
) -> list[BlogPostItem]:
    try:
        require_module(ctx, "content_read")
    except PermissionError as exc:
        _perm(exc)
    rows = _blog.list_posts(
        db, locale=locale, status=status, category=category, search=search, limit=limit
    )
    return [_serialize(row) for row in rows]


@router.get("/blog/posts/{post_id}", response_model=BlogPostItem)
def get_blog_post(
    post_id: str,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> BlogPostItem:
    try:
        require_module(ctx, "content_read")
    except PermissionError as exc:
        _perm(exc)
    record = _blog.get_post(db, post_id)
    if not record:
        raise HTTPException(status_code=404, detail="blog_post_not_found")
    return _serialize(record)


@router.post("/blog/media", status_code=201)
async def upload_blog_media(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    file: UploadFile = File(...),
) -> dict[str, str]:
    try:
        require_module(ctx, "content")
    except PermissionError as exc:
        _perm(exc)
    raw = await file.read()
    allowed = document_allowed_types(db)
    imageish = frozenset(f".{ext}" for ext in allowed if ext in _IMAGE_EXT)
    try:
        path = save_blog_image(
            filename=file.filename or "upload.jpg",
            content=raw,
            content_type=file.content_type,
            max_bytes=min(document_max_bytes(db), 100 * 1024 * 1024),
            allowed_ext=imageish,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    return {"url": path, "path": path}


@router.post("/blog/posts", response_model=BlogPostItem, status_code=201)
def create_blog_post(
    body: BlogPostCreateRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> BlogPostItem:
    try:
        require_module(ctx, "content")
    except PermissionError as exc:
        _perm(exc)
    try:
        record = _blog.create_post(
            db,
            slug=body.slug,
            locale=body.locale,
            title=body.title,
            description=body.description,
            body_md=body.body_md,
            category=body.category,
            author_id=body.author_id,
            status=body.status,
            featured=body.featured,
            trending=body.trending,
            case_study=body.case_study,
            on_time_percent=body.on_time_percent,
            cost_delta_percent=body.cost_delta_percent,
            volume_metric=body.volume_metric,
            tags=body.tags,
            cover_image_url=body.cover_image_url,
            published_at=body.published_at,
            created_by=ctx.user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    log_admin_audit(
        db,
        ctx,
        action="blog_post_create",
        resource_type="blog_post",
        resource_id=record.id,
        payload={"slug": record.slug, "locale": record.locale, "status": record.status},
    )
    _bump_website(settings, record)
    return _serialize(record)


@router.patch("/blog/posts/{post_id}", response_model=BlogPostItem)
def update_blog_post(
    post_id: str,
    body: BlogPostUpdateRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> BlogPostItem:
    try:
        require_module(ctx, "content")
    except PermissionError as exc:
        _perm(exc)
    try:
        record = _blog.update_post(
            db,
            post_id,
            slug=body.slug,
            locale=body.locale,
            title=body.title,
            description=body.description,
            body_md=body.body_md,
            category=body.category,
            author_id=body.author_id,
            status=body.status,
            featured=body.featured,
            trending=body.trending,
            case_study=body.case_study,
            on_time_percent=body.on_time_percent,
            cost_delta_percent=body.cost_delta_percent,
            volume_metric=body.volume_metric,
            tags=body.tags,
            cover_image_url=body.cover_image_url,
            clear_cover_image_url=body.clear_cover_image_url,
            published_at=body.published_at,
            clear_published_at=body.clear_published_at,
        )
    except LookupError:
        raise HTTPException(status_code=404, detail="blog_post_not_found") from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    log_admin_audit(
        db,
        ctx,
        action="blog_post_update",
        resource_type="blog_post",
        resource_id=post_id,
        payload=body.model_dump(exclude_unset=True),
    )
    _bump_website(settings, record)
    return _serialize(record)


@router.delete("/blog/posts/{post_id}", status_code=204)
def delete_blog_post(
    post_id: str,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> None:
    try:
        require_module(ctx, "content")
    except PermissionError as exc:
        _perm(exc)
    record = _blog.get_post(db, post_id)
    if not record:
        raise HTTPException(status_code=404, detail="blog_post_not_found")
    locale, slug = record.locale, record.slug
    try:
        _blog.delete_post(db, post_id)
    except LookupError:
        raise HTTPException(status_code=404, detail="blog_post_not_found") from None
    log_admin_audit(
        db,
        ctx,
        action="blog_post_delete",
        resource_type="blog_post",
        resource_id=post_id,
    )
    notify_blog_revalidate(settings, locale=locale, slug=slug)
