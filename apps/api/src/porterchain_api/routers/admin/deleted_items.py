"""Settings > Deleted items: soft delete, restore, permanent delete. /v1/admin/deleted-items/*"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from porterchain_api import soft_delete as sd
from porterchain_api.admin_engine.audit import commit_admin_write
from porterchain_api.admin_engine.rbac import AdminContext
from porterchain_api.auth.admin import get_admin_context
from porterchain_api.db import get_db
from porterchain_api.routers.admin._deps import router


class DeleteBody(BaseModel):
    reason: str | None = Field(default=None, max_length=500)


class PurgeBody(BaseModel):
    confirm: str = Field(min_length=1, max_length=255)


class RetentionBody(BaseModel):
    retention_days: int = Field(ge=1, le=3650)


def _fail(exc: Exception) -> None:
    if isinstance(exc, sd.Blocked):
        raise HTTPException(status_code=409, detail={"code": exc.code, "message": exc.reason}) from exc
    if isinstance(exc, PermissionError):
        raise HTTPException(status_code=403, detail={"code": "forbidden", "message": str(exc)}) from exc
    if isinstance(exc, LookupError):
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "Not found."}) from exc
    raise exc


@router.get("/deleted-items/meta")
def deleted_items_meta(ctx: Annotated[AdminContext, Depends(get_admin_context)], db: Session = Depends(get_db)) -> dict[str, Any]:
    return {"entities": [{"key": k, "title": e.title} for k, e in sd.REGISTRY.items()],
            "retention_days": sd.retention_days(db), "can_delete": sd.can_delete(ctx), "can_purge": sd.can_purge(ctx)}


@router.put("/deleted-items/settings")
def deleted_items_settings(body: RetentionBody, ctx: Annotated[AdminContext, Depends(get_admin_context)],
                           db: Session = Depends(get_db)) -> dict[str, int]:
    try:
        days = sd.set_retention_days(db, ctx, body.retention_days)
    except (sd.Blocked, PermissionError) as exc:
        _fail(exc)
    commit_admin_write(db)
    return {"retention_days": days}


@router.get("/deleted-items")
def deleted_items_list(ctx: Annotated[AdminContext, Depends(get_admin_context)], db: Session = Depends(get_db),
                       entity: str | None = Query(None), q: str | None = Query(None, max_length=120),
                       state: str = Query("deleted", pattern="^(deleted|restored|purged)$")) -> dict[str, Any]:
    if not sd.can_delete(ctx):
        _fail(PermissionError("Only admins can see deleted items."))
    return {"items": sd.list_batches(db, entity_key=entity, q=q, state=state), "retention_days": sd.retention_days(db)}


@router.get("/deleted-items/check/{entity}/{row_id}")
def deleted_items_check(entity: str, row_id: str, ctx: Annotated[AdminContext, Depends(get_admin_context)],
                        db: Session = Depends(get_db)) -> dict[str, Any]:
    try:
        out = sd.check(db, entity, row_id)
    except (sd.Blocked, LookupError) as exc:
        _fail(exc)
    out["can_delete"] = sd.can_delete(ctx)
    return out


@router.post("/deleted-items/{entity}/{row_id}/delete")
def deleted_items_delete(entity: str, row_id: str, body: DeleteBody, ctx: Annotated[AdminContext, Depends(get_admin_context)],
                         db: Session = Depends(get_db)) -> dict[str, Any]:
    try:
        b = sd.soft_delete(db, ctx, entity, row_id, reason=body.reason)
    except (sd.Blocked, PermissionError, LookupError) as exc:
        db.rollback()
        _fail(exc)
    commit_admin_write(db)
    return sd.batch_out(b)


@router.post("/deleted-items/{batch_id}/restore")
def deleted_items_restore(batch_id: str, ctx: Annotated[AdminContext, Depends(get_admin_context)],
                          db: Session = Depends(get_db)) -> dict[str, Any]:
    try:
        b = sd.restore(db, ctx, batch_id)
    except (sd.Blocked, PermissionError, LookupError) as exc:
        db.rollback()
        _fail(exc)
    commit_admin_write(db)
    return sd.batch_out(b)


@router.post("/deleted-items/{batch_id}/purge")
def deleted_items_purge(batch_id: str, body: PurgeBody, ctx: Annotated[AdminContext, Depends(get_admin_context)],
                        db: Session = Depends(get_db)) -> dict[str, Any]:
    from porterchain_api.platform import forensics

    try:
        b = sd.purge(db, ctx, batch_id, confirm=body.confirm)
    except (sd.Blocked, PermissionError, LookupError) as exc:
        db.rollback()
        forensics.record(None, "erasure", "soft_delete.purge_refused", actor=ctx.user.id, target_type="deleted_batch",
                         target_id=batch_id, outcome="denied", detail={"reason": getattr(exc, "reason", str(exc))})
        _fail(exc)
    commit_admin_write(db)
    forensics.record(None, "erasure", "soft_delete.purge", actor=ctx.user.id, target_type=b.entity,
                     target_id=b.root_id, detail={"batch_id": b.id, "mode": (b.outcome or {}).get("mode")})
    return sd.batch_out(b)


@router.post("/deleted-items/auto-purge/run")
def deleted_items_auto_purge(ctx: Annotated[AdminContext, Depends(get_admin_context)],
                             db: Session = Depends(get_db)) -> dict[str, int]:
    if not sd.can_purge(ctx):
        _fail(PermissionError("Only a super admin can run auto-purge."))
    return sd.auto_purge(db)
