"""Admin invoice adjustments: void, line credit, partial credit (GST/HST credit notes).

Rules and sources: docs/compliance/INVOICE_ADJUSTMENTS_CANADA.md. Every write needs
the ``finance`` module and staff step-up; above the approval threshold a second
admin must approve. Logic lives in ``admin_engine/finance_refund.py``.
"""

from __future__ import annotations

from typing import Literal

from fastapi import Header, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field

from porterchain_api.admin_engine import finance_refund as svc
from porterchain_api.auth.staff_step_up import enforce_staff_step_up
from porterchain_api.routers.admin._deps import (
    AdminContext,
    Annotated,
    Depends,
    HTTPException,
    Session,
    Settings,
    get_admin_context,
    get_db,
    get_settings,
    require_module,
    router,
)


class CreditNoteCreateRequest(BaseModel):
    kind: Literal["void", "lines", "partial"]
    reason_code: str = Field(min_length=2, max_length=32)
    internal_note: str | None = Field(default=None, max_length=2000)
    customer_message: str | None = Field(default=None, max_length=500)
    line_ids: list[str] | None = None
    amount_cents: int | None = Field(default=None, gt=0)


class CreditNoteDecisionRequest(BaseModel):
    note: str | None = Field(default=None, max_length=500)


def _err(exc: Exception) -> HTTPException:
    if isinstance(exc, LookupError):
        return HTTPException(status_code=404, detail=str(exc).strip("'"))
    if isinstance(exc, PermissionError):
        return HTTPException(status_code=403, detail=str(exc))
    return HTTPException(status_code=400, detail=str(exc))


_ERRORS = (LookupError, ValueError, PermissionError)


@router.get("/finance/invoices/{invoice_id}/adjustments")
def finance_invoice_adjustments(
    invoice_id: str,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> dict:
    require_module(ctx, "finance_read")
    try:
        return svc.invoice_adjustments(db, invoice_id)
    except _ERRORS as exc:
        raise _err(exc) from None


@router.post("/finance/invoices/{invoice_id}/credit-notes")
def finance_create_credit_note(
    invoice_id: str,
    body: CreditNoteCreateRequest,
    request: Request,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    authorization: Annotated[str | None, Header()] = None,
) -> dict:
    require_module(ctx, "finance")
    enforce_staff_step_up(request, authorization, settings)
    try:
        return svc.create_credit_note(db, settings, ctx, invoice_id, **body.model_dump())
    except _ERRORS as exc:
        raise _err(exc) from None


@router.post("/finance/credit-notes/{credit_note_id}/approve")
def finance_approve_credit_note(
    credit_note_id: str,
    request: Request,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    authorization: Annotated[str | None, Header()] = None,
) -> dict:
    require_module(ctx, "finance")
    enforce_staff_step_up(request, authorization, settings)
    try:
        return svc.approve_credit_note(db, settings, ctx, credit_note_id)
    except _ERRORS as exc:
        raise _err(exc) from None


@router.post("/finance/credit-notes/{credit_note_id}/reject")
def finance_reject_credit_note(
    credit_note_id: str,
    body: CreditNoteDecisionRequest,
    request: Request,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    authorization: Annotated[str | None, Header()] = None,
) -> dict:
    require_module(ctx, "finance")
    enforce_staff_step_up(request, authorization, settings)
    try:
        return svc.reject_credit_note(db, ctx, credit_note_id, body.note)
    except _ERRORS as exc:
        raise _err(exc) from None


@router.post("/finance/credit-notes/{credit_note_id}/retry-refund")
def finance_retry_credit_note_refund(
    credit_note_id: str,
    request: Request,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    authorization: Annotated[str | None, Header()] = None,
) -> dict:
    require_module(ctx, "finance")
    enforce_staff_step_up(request, authorization, settings)
    try:
        return svc.retry_credit_note_refund(db, settings, ctx, credit_note_id)
    except _ERRORS as exc:
        raise _err(exc) from None


@router.get("/finance/credit-notes/{credit_note_id}/pdf")
def finance_credit_note_pdf(
    credit_note_id: str,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> Response:
    require_module(ctx, "finance_read")
    try:
        pdf, filename = svc.credit_note_pdf_for_admin(db, credit_note_id)
    except _ERRORS as exc:
        raise _err(exc) from None
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
