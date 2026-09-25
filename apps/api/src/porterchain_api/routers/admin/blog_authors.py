"""Admin blog author CMS routes — split from blog.py for D2 LOC gates."""

from typing import Annotated

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from porterchain_api.auth.admin import get_admin_context
from porterchain_api.admin_engine.rbac import AdminContext, require_module
from porterchain_api.db import get_db
from porterchain_api.routers.admin._deps import (
    BlogAuthorCreateRequest,
    BlogAuthorItem,
    BlogAuthorUpdateRequest,
    _blog,
    _perm,
    log_admin_audit,
    router,
)


def _serialize_author(record) -> BlogAuthorItem:
    return BlogAuthorItem(**_blog.serialize_author(record))


@router.get("/blog/authors", response_model=list[BlogAuthorItem])
def list_blog_authors(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> list[BlogAuthorItem]:
    try:
        require_module(ctx, "content_read")
    except PermissionError as exc:
        _perm(exc)
    return [_serialize_author(row) for row in _blog.list_authors(db)]


@router.post("/blog/authors", response_model=BlogAuthorItem, status_code=201)
def create_blog_author(
    body: BlogAuthorCreateRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> BlogAuthorItem:
    try:
        require_module(ctx, "content")
    except PermissionError as exc:
        _perm(exc)
    try:
        record = _blog.create_author(
            db, author_id=body.id, name=body.name, role=body.role, bio=body.bio
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    log_admin_audit(
        db,
        ctx,
        action="blog_author_create",
        resource_type="blog_author",
        resource_id=record.id,
        payload={"name": record.name},
    )
    return _serialize_author(record)


@router.patch("/blog/authors/{author_id}", response_model=BlogAuthorItem)
def update_blog_author(
    author_id: str,
    body: BlogAuthorUpdateRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> BlogAuthorItem:
    try:
        require_module(ctx, "content")
    except PermissionError as exc:
        _perm(exc)
    try:
        record = _blog.update_author(
            db, author_id, name=body.name, role=body.role, bio=body.bio
        )
    except LookupError:
        raise HTTPException(status_code=404, detail="blog_author_not_found") from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    log_admin_audit(
        db,
        ctx,
        action="blog_author_update",
        resource_type="blog_author",
        resource_id=author_id,
        payload=body.model_dump(exclude_unset=True),
    )
    return _serialize_author(record)


@router.delete("/blog/authors/{author_id}", status_code=204)
def delete_blog_author(
    author_id: str,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> None:
    try:
        require_module(ctx, "content")
    except PermissionError as exc:
        _perm(exc)
    try:
        _blog.delete_author(db, author_id)
    except LookupError:
        raise HTTPException(status_code=404, detail="blog_author_not_found") from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    log_admin_audit(
        db,
        ctx,
        action="blog_author_delete",
        resource_type="blog_author",
        resource_id=author_id,
    )
