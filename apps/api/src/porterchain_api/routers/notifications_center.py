"""Admin Notifications center — /v1/admin/notifications/center/*

One screen: live log + detail, dead letters with replay, suppression list, speed
metrics, template manager (EN/FR preview, test-to-self, copy edits with history),
event x persona matrix and the daily ops digest switch.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from porterchain_api.admin_engine.rbac import AdminContext, require_module
from porterchain_api.auth.admin import get_admin_context
from porterchain_api.db import get_db
from porterchain_api.notification_engine import center, template_copy
from porterchain_api.notification_engine import center_settings as cs

router = APIRouter(prefix="/v1/admin/notifications/center", tags=["notifications-center"])
Ctx = Annotated[AdminContext, Depends(get_admin_context)]


def _read(ctx: AdminContext) -> None:
    try:
        require_module(ctx, "notifications_read")
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


def _write(ctx: AdminContext) -> None:
    try:
        require_module(ctx, "notifications")
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


def _who(ctx: AdminContext) -> str | None:
    return getattr(ctx.user, "email", None)


@router.get("/metrics")
def get_metrics(ctx: Ctx, db: Session = Depends(get_db), hours: int = Query(24, ge=1, le=168)) -> dict:
    _read(ctx)
    return center.metrics(db, hours=hours)


@router.get("/log")
def get_log(
    ctx: Ctx,
    db: Session = Depends(get_db),
    persona: str | None = None,
    event: str | None = None,
    status: str | None = None,
    channel: str | None = None,
    q: str | None = Query(None, max_length=200),
    before: datetime | None = None,
    limit: int = Query(100, ge=1, le=500),
) -> list[dict]:
    _read(ctx)
    return center.list_log(db, persona=persona, event=event, status=status, channel=channel, q=q, before=before, limit=limit)


@router.get("/log/{notification_id}")
def get_detail(notification_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    _read(ctx)
    out = center.detail(db, notification_id)
    if out is None:
        raise HTTPException(status_code=404, detail="notification_not_found")
    return out


@router.get("/dead-letters")
def get_dead_letters(ctx: Ctx, db: Session = Depends(get_db), limit: int = Query(100, le=500)) -> list[dict]:
    _read(ctx)
    return center.dead_letters(db, limit=limit)


@router.post("/dead-letters/{notification_id}/replay")
def replay_one(notification_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    _write(ctx)
    if not center.replay(db, notification_id):
        raise HTTPException(status_code=404, detail="notification_not_replayable")
    return {"ok": True}


@router.post("/dead-letters/replay-all")
def replay_all(ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    _write(ctx)
    return {"replayed": center.replay_all(db)}


@router.get("/suppressions")
def get_suppressions(
    ctx: Ctx, db: Session = Depends(get_db), include_released: bool = False, limit: int = Query(200, ge=1, le=1000)
) -> list[dict]:
    _read(ctx)
    return center.suppressions(db, include_released=include_released, limit=limit)


class UnsuppressBody(BaseModel):
    email: str = Field(min_length=3, max_length=320)


@router.post("/suppressions/release")
def release(body: UnsuppressBody, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    _write(ctx)
    if not center.unsuppress(db, body.email, author=_who(ctx)):
        raise HTTPException(status_code=404, detail="not_suppressed")
    return {"ok": True}


@router.get("/templates")
def get_templates(ctx: Ctx, db: Session = Depends(get_db), limit: int = Query(500, ge=1, le=500)) -> list[dict]:
    _read(ctx)
    return center.template_catalog(db)[:limit]


class DraftBody(BaseModel):
    lang: str = Field("en", pattern="^(en|fr)$")
    subject: str | None = Field(None, max_length=200)
    intro: str | None = Field(None, max_length=600)


@router.get("/templates/{template}/preview")
def preview(template: str, ctx: Ctx, lang: str = Query("en", pattern="^(en|fr)$")) -> dict:
    _read(ctx)
    try:
        return center.preview(template, lang=lang)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/templates/{template}/preview")
def preview_draft(template: str, body: DraftBody, ctx: Ctx) -> dict:
    """Live preview of unsaved copy."""
    _read(ctx)
    try:
        template_copy.validate(body.subject)
        template_copy.validate(body.intro)
        return center.preview(template, lang=body.lang, draft={"subject": body.subject or "", "intro": body.intro or ""})
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.put("/templates/{template}/copy")
def save_copy(template: str, body: DraftBody, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    _write(ctx)
    from porterchain_api.notification_engine.templates import TEMPLATES

    if template not in TEMPLATES:
        raise HTTPException(status_code=404, detail="template_not_found")
    try:
        row = template_copy.save(db, template=template, lang=body.lang, subject=body.subject, intro=body.intro, author=_who(ctx))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"version": row.version, "active": row.is_active}


@router.get("/templates/{template}/history")
def copy_history(
    template: str, ctx: Ctx, db: Session = Depends(get_db), limit: int = Query(100, ge=1, le=500)
) -> list[dict]:
    _read(ctx)
    return template_copy.history(db, template)[:limit]


class TestBody(BaseModel):
    lang: str = Field("en", pattern="^(en|fr)$")


@router.post("/templates/{template}/test")
def send_test(template: str, body: TestBody, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    """Test send goes to the signed-in admin's own address only."""
    _write(ctx)
    try:
        return center.send_test(db, template, lang=body.lang, admin_id=str(ctx.user.id or ctx.user.email), admin_email=_who(ctx) or "")
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/matrix")
def get_matrix(ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    _read(ctx)
    return center.matrix(db)


class MatrixBody(BaseModel):
    event: str = Field(min_length=2, max_length=80)
    persona: str
    enabled: bool


@router.put("/matrix")
def put_matrix(body: MatrixBody, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    _write(ctx)
    try:
        off = cs.set_matrix_cell(db, body.event, body.persona, body.enabled, author=_who(ctx))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"off": sorted(off)}


@router.get("/digest")
def get_digest(ctx: Ctx, db: Session = Depends(get_db)) -> dict[str, Any]:
    _read(ctx)
    return {"settings": cs.get_setting(db, cs.DIGEST_KEY, cs.DIGEST_DEFAULT), "preview": center.build_digest(db)}


class DigestBody(BaseModel):
    enabled: bool
    approve: bool = False


@router.put("/digest")
def put_digest(body: DigestBody, ctx: Ctx, db: Session = Depends(get_db)) -> dict[str, Any]:
    """Turning the digest on needs an explicit approval, recorded with who and when."""
    _write(ctx)
    cfg = cs.get_setting(db, cs.DIGEST_KEY, cs.DIGEST_DEFAULT)
    if body.enabled and not (cfg.get("approved") or body.approve):
        raise HTTPException(status_code=409, detail="approval_required")
    if body.approve:
        cfg.update({"approved": True, "approved_by": _who(ctx), "approved_at": datetime.now(UTC).isoformat()})
    cfg["enabled"] = body.enabled
    if not body.enabled:
        cfg.update({"approved": False, "approved_by": None, "approved_at": None})
    cs.set_setting(db, cs.DIGEST_KEY, cfg, author=_who(ctx))
    return {"settings": cfg}
