"""admin routes — Dispatch (Today / Plan / Live / Exceptions / Fleet / Metrics).

Paths stay under /v1/admin/operations/dispatch/* next to the Control Tower API.
"""

from fastapi import Body, Query

from porterchain_api.admin_engine.dispatch_board_service import DispatchBoardService, recommend
from porterchain_api.admin_engine.job_offers_service import JobOffersService
from porterchain_api.routers.admin._deps import (
    AdminContext,
    Annotated,
    Depends,
    HTTPException,
    Session,
    get_admin_context,
    get_db,
    require_module,
    router,
)

_board = DispatchBoardService()
_offers = JobOffersService()
Ctx = Annotated[AdminContext, Depends(get_admin_context)]
P = "/operations/dispatch"


def _invoke(ctx: AdminContext, module: str, fn, *args, **kwargs):
    try:
        require_module(ctx, module)
        return fn(*args, **kwargs)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get(f"{P}/metrics")
def dispatch_metrics(ctx: Ctx, db: Session = Depends(get_db), days: int = Query(7, ge=1, le=90)) -> dict:
    """Speed bar: order→dispatch, on-time %, first attempt %, cost/stop, fill %, stops/driver-hour."""
    return _invoke(ctx, "dispatch_read", _board.metrics, db, days=days)


@router.get(f"{P}/exceptions")
def dispatch_exceptions(
    ctx: Ctx,
    db: Session = Depends(get_db),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> dict:
    """One queue, worst then newest first: open exceptions, failed/damaged/lost/returns,
    late/at-risk ETAs, unassigned >15 min. Paged; ``total``/``counts`` cover the whole queue."""
    return _invoke(ctx, "dispatch_read", _board.exceptions_queue, db, offset=offset, limit=limit)


@router.post(f"{P}/exceptions/apply")
def dispatch_exception_apply(ctx: Ctx, db: Session = Depends(get_db), body: dict = Body(...)) -> dict:
    """Apply one suggested fix an admin approved: ``{item_id, order_id, action, params}``.

    action: reroute (drafts a re-plan) | reassign | reschedule | contact (order.delayed notice).
    """
    from porterchain_api.admin_engine.exception_fixes_service import ExceptionFixesService
    from porterchain_api.config import get_settings

    return _invoke(
        ctx, "dispatch", ExceptionFixesService().apply, db, get_settings(), ctx,
        item_id=str(body.get("item_id") or ""), order_id=str(body.get("order_id") or ""),
        action=str(body.get("action") or ""), params=body.get("params") if isinstance(body.get("params"), dict) else {},
    )


@router.get(f"{P}/live-eta")
def dispatch_live_eta(ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    return _invoke(ctx, "dispatch_read", lambda: {"items": _board.live_etas(db)})


@router.get(f"{P}/orders/{{order_id}}/recommend")
def dispatch_recommend(order_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    """Recommended vehicle (≤ max fill) and drivers ranked by insertion cost."""
    return _invoke(ctx, "dispatch_read", recommend, db, order_id)


@router.get(f"{P}/orders/{{order_id}}/offers")
def dispatch_offers(order_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    return _invoke(ctx, "dispatch_read", lambda: {"items": _offers.list_for_order(db, order_id)})


@router.post(f"{P}/orders/{{order_id}}/offer")
def dispatch_offer(order_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    """Offer to the best driver; expires after the fleet TTL (180 s) then passes on."""
    return _invoke(ctx, "dispatch", _offers.offer, db, order_id, actor_id=ctx.user.id)


@router.post(f"{P}/offers/sweep")
def dispatch_offers_sweep(ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    return _invoke(ctx, "dispatch", _offers.sweep, db)


@router.get(f"{P}/fleet-capacity")
def dispatch_fleet_get(ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    return _invoke(ctx, "dispatch_read", _board.fleet_get, db)


@router.put(f"{P}/fleet-capacity")
def dispatch_fleet_put(ctx: Ctx, db: Session = Depends(get_db), body: dict = Body(...)) -> dict:
    """Admin / super admin only. Validated; audited with before/after."""
    return _invoke(ctx, "dispatch", _board.fleet_put, db, ctx, body)
