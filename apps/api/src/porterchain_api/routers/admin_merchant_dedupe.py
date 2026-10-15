"""Admin: likely-duplicate merchants queue + Merge tool (undoable)."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from porterchain_api.admin_engine import merchant_merge as mm
from porterchain_api.db import get_db
from porterchain_api.routers.merchants_integrations import Ctx, _invoke

router = APIRouter(prefix="/v1/admin/merchant-duplicates", tags=["merchants"])


class MergeBody(BaseModel):
    source_merchant_id: str
    target_merchant_id: str


@router.get("")
def duplicate_queue(ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    return {"items": _invoke(ctx, "merchants_read", mm.list_duplicate_queue, db)}


@router.get("/preview")
def merge_preview(source: str, target: str, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    return {"moves": _invoke(ctx, "merchants_read", mm.merge_preview, db, source, target)}


@router.post("/{merchant_id}/keep-separate")
def keep_separate(merchant_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    return _invoke(ctx, "merchants", mm.keep_separate, db, ctx, merchant_id)


@router.post("/merge")
def merge(body: MergeBody, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    return _invoke(ctx, "merchants", mm.merge_merchants, db, ctx, body.source_merchant_id, body.target_merchant_id)


@router.post("/merges/{merge_id}/undo")
def undo(merge_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    return _invoke(ctx, "merchants", mm.undo_merge, db, ctx, merge_id)
