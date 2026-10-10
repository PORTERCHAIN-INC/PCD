"""admin routes — Cash page (AR by merchant, reminder drafts) and Driver Pay runs."""

from datetime import datetime

from fastapi import Header, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field

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


class DraftDecision(BaseModel):
    ids: list[str] = Field(min_length=1, max_length=200)


class PayoutRunCreate(BaseModel):
    period_start: datetime
    period_end: datetime


def _errors(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/finance/cash")
def finance_cash(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> dict:
    """Everything owed, by merchant and age, plus what is waiting for a decision."""
    require_module(ctx, "finance_read")
    from porterchain_api.finance_ops.cash import cash_board

    return cash_board(db)


@router.get("/finance/reminders")
def finance_reminder_drafts(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    status: str = "draft",
) -> dict:
    require_module(ctx, "finance_read")
    from porterchain_api.finance_ops.reminders import list_drafts

    return {"items": list_drafts(db, status=status)}


@router.post("/finance/reminders/queue")
def finance_reminders_queue(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> dict:
    """Write drafts only — nothing is sent until approved."""
    require_module(ctx, "finance")
    from porterchain_api.finance_ops.reminders import queue_drafts

    return queue_drafts(db)


@router.post("/finance/reminders/approve")
def finance_reminders_approve(
    body: DraftDecision,
    request: Request,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    authorization: Annotated[str | None, Header()] = None,
) -> dict:
    require_module(ctx, "finance")
    enforce_staff_step_up(request, authorization, settings)
    from porterchain_api.finance_ops.reminders import decide

    return decide(db, ctx, body.ids, approve=True)


@router.post("/finance/reminders/discard")
def finance_reminders_discard(
    body: DraftDecision,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> dict:
    require_module(ctx, "finance")
    from porterchain_api.finance_ops.reminders import decide

    return decide(db, ctx, body.ids, approve=False)


@router.get("/finance/payout-runs")
def finance_payout_runs(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> dict:
    require_module(ctx, "finance_read")
    from porterchain_api.finance_ops.payout_runs import list_runs

    return {"items": list_runs(db)}


@router.post("/finance/payout-runs", status_code=201)
def finance_payout_run_create(
    body: PayoutRunCreate,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> dict:
    require_module(ctx, "finance")
    from porterchain_api.finance_ops.payout_runs import create_run, run_payload

    return run_payload(_errors(create_run, db, ctx, body.period_start, body.period_end))


@router.post("/finance/payout-runs/{run_id}/{action}")
def finance_payout_run_action(
    run_id: str,
    action: str,
    request: Request,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    authorization: Annotated[str | None, Header()] = None,
) -> dict:
    require_module(ctx, "finance")
    from porterchain_api.finance_ops import payout_runs as pr

    fns = {"approve": pr.approve_run, "mark-paid": pr.mark_run_paid, "discard": pr.discard_run}
    if action not in fns:
        raise HTTPException(status_code=404, detail="unknown_action")
    if action != "discard":
        enforce_staff_step_up(request, authorization, settings)
    return pr.run_payload(_errors(fns[action], db, ctx, run_id))


@router.get("/finance/payout-runs/{run_id}/bank.csv")
def finance_payout_run_csv(
    run_id: str,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> Response:
    require_module(ctx, "finance")
    from porterchain_api.finance_ops.payout_runs import bank_csv

    body, name = _errors(bank_csv, db, run_id)
    return Response(
        content=body,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{name}"', "Cache-Control": "no-store"},
    )
