"""admin routes — Interac e-Transfer review queue (finance)."""

from fastapi import Header, Request
from pydantic import BaseModel, Field

from porterchain_api.auth.staff_step_up import enforce_staff_step_up
from porterchain_api.routers.admin._deps import (
    AdminContext,
    Annotated,
    Depends,
    HTTPException,
    Query,
    Session,
    Settings,
    get_admin_context,
    get_db,
    get_settings,
    require_module,
    router,
)


def _step_up(request: Request, authorization: str | None, settings: Settings) -> None:
    enforce_staff_step_up(request, authorization, settings)



class InteracDecisionRequest(BaseModel):
    invoice_id: str | None = None
    note: str | None = Field(default=None, max_length=255)


@router.get("/finance/interac")
def finance_interac_queue(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    status: str | None = Query("open"),
    limit: int = Query(100, ge=1, le=500),
) -> dict:
    """Inbound Interac e-Transfers waiting for (or past) one-click approval."""
    require_module(ctx, "finance_read")
    from porterchain_api.billing_engine.interac.imap_reader import imap_configured
    from porterchain_api.billing_engine.interac.service import list_transfers

    return {
        "inbox_enabled": imap_configured(settings),
        "items": list_transfers(db, status=status, limit=limit),
    }


@router.post("/finance/interac/{transfer_id}/approve")
def finance_interac_approve(
    transfer_id: str,
    body: InteracDecisionRequest,
    request: Request,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    authorization: Annotated[str | None, Header()] = None,
) -> dict:
    require_module(ctx, "finance")
    _step_up(request, authorization, settings)
    from porterchain_api.billing_engine.interac.service import approve_transfer

    try:
        return approve_transfer(db, ctx, transfer_id, invoice_id=body.invoice_id, note=body.note)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/finance/interac/{transfer_id}/reject")
def finance_interac_reject(
    transfer_id: str,
    body: InteracDecisionRequest,
    request: Request,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    authorization: Annotated[str | None, Header()] = None,
) -> dict:
    require_module(ctx, "finance")
    _step_up(request, authorization, settings)
    from porterchain_api.billing_engine.interac.service import reject_transfer

    try:
        return reject_transfer(db, ctx, transfer_id, note=body.note)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/finance/interac/sync")
def finance_interac_sync(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    """Pull the billing inbox now (read-only). No-op unless INTERAC_IMAP_ENABLED."""
    require_module(ctx, "finance")
    from porterchain_api.billing_engine.interac.imap_reader import fetch_and_ingest

    try:
        return fetch_and_ingest(db, settings)
    except Exception as exc:  # noqa: BLE001 - surface IMAP errors without leaking creds
        raise HTTPException(status_code=502, detail=f"imap_error:{type(exc).__name__}") from exc


@router.get("/finance/ar-summary")
def finance_ar_summary(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> dict:
    """What's owed, what's overdue, one action per merchant, and reminder DRAFTS (never sent)."""
    require_module(ctx, "finance_read")
    from porterchain_api.billing_engine.dunning import ar_summary

    return ar_summary(db)
