"""Driver: documents for the stop they are on; staff: everything + history."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from porterchain_api.admin_engine.rbac import require_module as admin_require_module
from porterchain_api.booking_attachments import service as svc
from porterchain_api.db import get_db
from porterchain_api.routers.booking_attachments._common import (
    ACtx,
    DCtx,
    call,
    file_response,
    read,
    tx,
)

router = APIRouter(tags=["booking-attachments"])


@router.get("/driver-api/v1/orders/{order_id}/attachments")
def driver_list(order_id: str, ctx: DCtx, db: Session = Depends(get_db)):
    return tx(db, svc.list_for_driver, db, ctx.driver.id, order_id)


@router.get("/driver-api/v1/attachments/{attachment_id}/file")
def driver_file(
    attachment_id: str, ctx: DCtx, db: Session = Depends(get_db)
) -> Response:
    att, data = tx(db, svc.driver_download, db, ctx.driver.id, attachment_id)
    return file_response(att, data)


@router.post("/driver-api/v1/attachments/{attachment_id}/link")
def driver_link(
    attachment_id: str, ctx: DCtx, db: Session = Depends(get_db)
) -> dict[str, Any]:
    token = tx(db, svc.driver_link, db, ctx.driver.id, attachment_id)
    return {
        "path": f"/v1/attachment-links/{token}",
        "expires_in": int(svc.LINK_TTL.total_seconds()),
    }


@router.get("/v1/attachment-links/{token}")
def redeem_link(token: str, db: Session = Depends(get_db)) -> Response:
    att, data = tx(db, svc.redeem_link, db, token)
    return file_response(att, data)


@router.post("/driver-api/v1/attachments/{attachment_id}/shown")
async def driver_shown(
    attachment_id: str,
    ctx: DCtx,
    db: Session = Depends(get_db),
    proof: UploadFile | None = File(None),
):
    data = await read(proof) if proof is not None else None
    return await run_in_threadpool(
        tx, db, svc.mark_shown, db, ctx.driver.id, attachment_id, data or None
    )


@router.get("/v1/admin/orders/{order_id}/attachments")
def staff_list(order_id: str, ctx: ACtx, db: Session = Depends(get_db)):
    admin_require_module(ctx, "orders")
    return call(svc.list_for_staff, db, order_id)


@router.get("/v1/admin/attachments/{attachment_id}/file")
def staff_file(
    attachment_id: str, ctx: ACtx, db: Session = Depends(get_db), proof: bool = False
) -> Response:
    admin_require_module(ctx, "orders")
    att, data, ctype = tx(
        db, svc.staff_download, db, str(ctx.user.id), attachment_id, proof=proof
    )
    return file_response(att, data, ctype)
