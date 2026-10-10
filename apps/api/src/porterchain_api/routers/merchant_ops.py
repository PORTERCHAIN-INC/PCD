"""Merchant admin ops API: board, health, credit, connections, quote preview,
documents, support rollup, owners, segments, bulk, change history.

Separate prefix (``/v1/admin/merchant-ops``) so it never collides with
``/v1/admin/merchants/{merchant_id}``. Reads need ``merchants_read``; writes need
``merchants`` plus the role rules here (``admin_engine.merchant_money_guard``);
the merchant-domain logic lives in ``merchant_engine.account_ops``.
"""

from __future__ import annotations

from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from porterchain_api.admin_engine import merchant_money_guard as guard
from porterchain_api.admin_engine.merchant_org import (
    admin_merchant_context,
    org_error_message,
    require_integrations_elevated,
    require_merchant,
)
from porterchain_api.admin_engine.rbac import AdminContext, require_module
from porterchain_api.auth.admin import get_admin_context
from porterchain_api.config import Settings, get_settings
from porterchain_api.db import get_db
from porterchain_api.merchant_engine.account_ops import board as board_ops
from porterchain_api.merchant_engine.account_ops import (
    connections,
    credit,
    documents,
    quote_preview,
    support,
)

router = APIRouter(prefix="/v1/admin/merchant-ops", tags=["merchant-ops"])
Ctx = Annotated[AdminContext, Depends(get_admin_context)]


def _run(ctx: AdminContext, module: str, fn, *args, **kwargs) -> Any:
    try:
        require_module(ctx, module)
        return fn(*args, **kwargs)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=org_error_message(str(exc))) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc) or "not_found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=org_error_message(str(exc))) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


class CreditBody(BaseModel):
    action: str
    reason: str | None = Field(default=None, max_length=255)
    limit_cents: int | None = Field(default=None, ge=0)
    override_days: int | None = Field(default=None, ge=1, le=credit.MAX_OVERRIDE_DAYS)


class OwnerBody(BaseModel):
    owner_id: str | None = None


class SegmentBody(BaseModel):
    segment: str | None = None


class BulkBody(BaseModel):
    action: str
    merchant_ids: list[str] = Field(min_length=1, max_length=board_ops.MAX_BULK)
    value: str | None = None
    reason: str | None = Field(default=None, max_length=255)


class RotateBody(BaseModel):
    grace_days: int = Field(default=7, ge=0, le=connections.MAX_ROTATE_GRACE_DAYS)
    reason: str = Field(min_length=1, max_length=255)


class ReplayBody(BaseModel):
    hours: int = Field(default=24, ge=1, le=168)
    webhook_id: str | None = None


class QuotePreviewBody(BaseModel):
    pickup: dict[str, Any] | None = None
    dropoff: dict[str, Any]
    weight_kg: float | None = Field(default=None, ge=0, le=5000)
    vehicle_class: str | None = None


class DeleteBody(BaseModel):
    reason: str | None = Field(default=None, max_length=255)


@router.get("/board")
def merchant_board(
    ctx: Ctx,
    db: Session = Depends(get_db),
    view: str = Query("needs_action", pattern="^(needs_action|all)$"),
    segment: str | None = None,
    status: str | None = None,
    owner_id: str | None = None,
    search: str | None = Query(None, max_length=120),
    sort: str = "priority",
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=5, le=100),
) -> dict:
    return _run(ctx, "merchants_read", board_ops.board, db, view=view, segment=segment, status=status,
                owner_id=owner_id, search=search, sort=sort, page=page, page_size=page_size)


@router.get("/owners")
def merchant_owners(
    ctx: Ctx, db: Session = Depends(get_db), limit: int = Query(200, ge=1, le=500)
) -> list[dict]:
    return _run(ctx, "merchants_read", board_ops.owners, db, limit=limit)


@router.post("/bulk")
def merchant_bulk(body: BulkBody, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    money = body.action in ("credit_hold", "credit_release")

    def _go():
        if money:
            guard.assert_money_editor(ctx)
        return board_ops.bulk(db, ctx, action=body.action, merchant_ids=body.merchant_ids,
                              value=body.value, reason=body.reason)

    return _run(ctx, "merchants_read" if money else "merchants", _go)


@router.get("/{merchant_id}")
def merchant_ops_overview(
    merchant_id: str, ctx: Ctx, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)
) -> dict:
    out = _run(ctx, "merchants_read", board_ops.merchant_ops, db, merchant_id, settings)
    out["can_edit_money"] = guard.can_edit_money(ctx)
    return out


@router.get("/{merchant_id}/change-history")
def merchant_change_history(
    merchant_id: str, ctx: Ctx, db: Session = Depends(get_db), limit: int = Query(100, ge=1, le=500)
) -> list[dict]:
    def _go():
        require_merchant(db, merchant_id)
        return guard.change_history(db, merchant_id, limit=limit)

    return _run(ctx, "merchants_read", _go)


@router.post("/{merchant_id}/credit")
def merchant_credit(merchant_id: str, body: CreditBody, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    # Finance is not in the `merchants` module; the money-editor role check is the gate.
    def _go():
        guard.assert_money_editor(ctx)
        m = require_merchant(db, merchant_id)
        return credit.set_credit(db, ctx, m, action=body.action, reason=body.reason,
                                 limit_cents=body.limit_cents, override_days=body.override_days)

    return _run(ctx, "merchants_read", _go)


@router.put("/{merchant_id}/owner")
def merchant_owner(merchant_id: str, body: OwnerBody, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    return _run(ctx, "merchants", board_ops.set_owner, db, ctx, merchant_id, body.owner_id)


@router.put("/{merchant_id}/segment")
def merchant_segment(merchant_id: str, body: SegmentBody, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    return _run(ctx, "merchants", board_ops.set_segment, db, ctx, merchant_id, body.segment)


@router.get("/{merchant_id}/connections")
def merchant_connections(
    merchant_id: str, ctx: Ctx, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)
) -> dict:
    def _go():
        require_merchant(db, merchant_id)
        return connections.watchdog(db, merchant_id, settings)

    return _run(ctx, "merchants_read", _go)


@router.post("/{merchant_id}/api-keys/{key_id}/rotate")
def merchant_rotate_key(
    merchant_id: str, key_id: str, body: RotateBody, ctx: Ctx, db: Session = Depends(get_db)
) -> dict:
    def _go():
        require_integrations_elevated(ctx)
        return connections.rotate_api_key(db, ctx, merchant_id, key_id, grace_days=body.grace_days,
                                          reason=body.reason)

    return _run(ctx, "merchants", _go)


@router.post("/{merchant_id}/webhooks/replay-failed")
def merchant_replay_failed(
    merchant_id: str,
    body: ReplayBody,
    ctx: Ctx,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    def _go():
        mctx = admin_merchant_context(db, merchant_id, ctx)
        return connections.replay_failed_webhooks(db, ctx, mctx, settings, hours=body.hours,
                                                  webhook_id=body.webhook_id)

    return _run(ctx, "merchants", _go)


@router.post("/{merchant_id}/shopify/{shop_id}/backfill")
def merchant_shopify_backfill(
    merchant_id: str,
    shop_id: str,
    ctx: Ctx,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    return _run(ctx, "merchants", connections.backfill_shopify, db, ctx, merchant_id, shop_id, settings)


@router.post("/{merchant_id}/quote-preview")
def merchant_quote_preview(
    merchant_id: str, body: QuotePreviewBody, ctx: Ctx, db: Session = Depends(get_db)
) -> dict:
    return _run(ctx, "merchants_read", quote_preview.preview, db, merchant_id, body.model_dump())


@router.get("/{merchant_id}/documents")
def merchant_documents(merchant_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    def _go():
        require_merchant(db, merchant_id)
        return {"items": documents.list_documents(db, merchant_id), "kinds": documents.KINDS,
                "max_bytes": documents.MAX_BYTES}

    return _run(ctx, "merchants_read", _go)


@router.post("/{merchant_id}/documents", status_code=201)
async def merchant_document_upload(
    merchant_id: str,
    ctx: Ctx,
    db: Session = Depends(get_db),
    file: UploadFile = File(...),
    kind: str = Form(...),
    expires_on: date | None = Form(None),
    note: str | None = Form(None),
) -> dict:
    data = await file.read(documents.MAX_BYTES + 1)
    return _run(ctx, "merchants", documents.upload_document, db, ctx, merchant_id, kind=kind,
                filename=file.filename or "document", content_type=file.content_type or "",
                data=data, expires_on=expires_on, note=note)


@router.get("/{merchant_id}/documents/{doc_id}/download")
def merchant_document_download(
    merchant_id: str, doc_id: str, ctx: Ctx, db: Session = Depends(get_db)
) -> Response:
    def _go():
        guard.assert_role(ctx, guard.DOCUMENT_READ_ROLES, "document_read_forbidden")
        return documents.read_document(db, ctx, merchant_id, doc_id)

    doc, data = _run(ctx, "merchants_read", _go)
    return Response(
        content=data,
        media_type=doc.content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{doc.filename}"',
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.delete("/{merchant_id}/documents/{doc_id}", status_code=204)
def merchant_document_delete(
    merchant_id: str, doc_id: str, ctx: Ctx, db: Session = Depends(get_db), body: DeleteBody | None = None
) -> Response:
    def _go():
        guard.assert_role(ctx, guard.DOCUMENT_DELETE_ROLES, "document_delete_forbidden")
        return documents.delete_document(db, ctx, merchant_id, doc_id, reason=body.reason if body else None)

    _run(ctx, "merchants_read", _go)
    return Response(status_code=204)


@router.get("/{merchant_id}/support")
def merchant_support(merchant_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    def _go():
        require_merchant(db, merchant_id)
        return support.support_rollup(db, merchant_id)

    return _run(ctx, "merchants_read", _go)
