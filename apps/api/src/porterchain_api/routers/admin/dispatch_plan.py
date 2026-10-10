"""admin routes — Dispatch Phase 2: fleet plans, re-plan, commit, explain, partners, legs, retention."""

from fastapi import Body, Query, Response

from porterchain_api.admin_engine.fleet_plan_service import FleetPlanService
from porterchain_api.admin_engine.logistics_partners_service import LogisticsPartnersService
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

_plans = FleetPlanService()
_partners = LogisticsPartnersService()
Ctx = Annotated[AdminContext, Depends(get_admin_context)]
P = "/operations/dispatch"


def _run(ctx: AdminContext, module: str, fn, *args, **kwargs):
    try:
        require_module(ctx, module)
        return fn(*args, **kwargs)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _actor(ctx: AdminContext) -> str | None:
    return getattr(getattr(ctx, "user", None), "id", None)


# ---------------------------------------------------------------- plans
@router.get(f"{P}/plans/latest")
def dispatch_plan_latest(ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    return _run(ctx, "dispatch_read", lambda: {"plan": _plans.latest(db)})


@router.post(f"{P}/plans")
def dispatch_plan_create(ctx: Ctx, db: Session = Depends(get_db), body: dict = Body(default={})) -> dict:
    """Plan the day: every waiting order, every online vehicle. Draft only — nothing is assigned."""
    ids = body.get("order_ids") if isinstance(body.get("order_ids"), list) else None
    limit = int(body.get("time_limit_s") or 5)
    return _run(ctx, "dispatch", _plans.plan, db, actor=_actor(ctx), order_ids=ids, time_limit_s=max(1, min(limit, 30)))


@router.get(f"{P}/plans/{{plan_id}}")
def dispatch_plan_get(plan_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    return _run(ctx, "dispatch_read", _plans.get, db, plan_id)


@router.post(f"{P}/plans/{{plan_id}}/replan")
def dispatch_plan_replan(plan_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    """Re-plan from live state: loaded freight stays on its vehicle; new orders slot in. Draft only."""
    return _run(ctx, "dispatch", _plans.replan, db, plan_id, actor=_actor(ctx))


@router.post(f"{P}/plans/{{plan_id}}/commit")
def dispatch_plan_commit(plan_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    """Admin approval: assign each route's orders to its driver through the normal assign path."""
    from porterchain_api.config import get_settings

    return _run(ctx, "dispatch", _plans.commit, db, get_settings(), ctx, plan_id)


@router.post(f"{P}/plans/{{plan_id}}/explain")
def dispatch_plan_explain(plan_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    """Explain + suggest only (rules; NVIDIA NIM when enabled). Never changes the plan."""
    return _run(ctx, "dispatch_read", _plans.explain, db, plan_id)


# ---------------------------------------------------------------- partners + legs
@router.get(f"{P}/partners")
def dispatch_partners(ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    return _run(ctx, "dispatch_read", lambda: {"items": _partners.list(db)})


@router.post(f"{P}/partners")
def dispatch_partner_create(ctx: Ctx, db: Session = Depends(get_db), body: dict = Body(...)) -> dict:
    return _run(ctx, "dispatch", _partners.upsert, db, ctx, body)


@router.put(f"{P}/partners/{{partner_id}}")
def dispatch_partner_update(partner_id: str, ctx: Ctx, db: Session = Depends(get_db), body: dict = Body(...)) -> dict:
    return _run(ctx, "dispatch", _partners.upsert, db, ctx, body, partner_id)


@router.get(f"{P}/orders/{{order_id}}/legs")
def dispatch_order_legs(order_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    return _run(ctx, "dispatch_read", lambda: {"items": _partners.legs(db, order_id)})


@router.post(f"{P}/orders/{{order_id}}/legs/plan")
def dispatch_order_legs_plan(order_id: str, ctx: Ctx, db: Session = Depends(get_db), save: bool = Query(False)) -> dict:
    """Local / warehouse / FTL / LTL / 3PL legs by rules. ``save=true`` stores them as planned."""
    return _run(ctx, "dispatch", _partners.plan_legs, db, ctx, order_id, save=save)


# ---------------------------------------------------------------- partner booking
@router.get(f"{P}/partner-legs")
def dispatch_partner_legs(ctx: Ctx, db: Session = Depends(get_db), status: str | None = Query(None)) -> dict:
    return _run(ctx, "dispatch_read", lambda: {"items": _partners.partner_legs(db, status=status)})


@router.get(f"{P}/partner-legs/{{leg_id}}/job-sheet.pdf")
def dispatch_partner_leg_pdf(leg_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> Response:
    pdf, name = _run(ctx, "dispatch_read", _partners.job_sheet_pdf, db, leg_id)
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="{name}"'})


@router.post(f"{P}/partner-legs/{{leg_id}}/draft")
def dispatch_partner_leg_draft(leg_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    """Email draft for the partner. Stored on the leg and returned — never sent."""
    return _run(ctx, "dispatch", _partners.draft_request, db, ctx, leg_id)


@router.post(f"{P}/partner-legs/{{leg_id}}/status")
def dispatch_partner_leg_status(leg_id: str, ctx: Ctx, db: Session = Depends(get_db), body: dict = Body(...)) -> dict:
    """Manual update: planned → requested → accepted → picked_up → delivered (or cancelled)."""
    return _run(ctx, "dispatch", _partners.set_leg_status, db, ctx, leg_id, str(body.get("status") or ""),
                body.get("note"))


# ---------------------------------------------------------------- retention
@router.get(f"{P}/retention")
def dispatch_retention_get(ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    return _run(ctx, "dispatch_read", _partners.retention_get, db)


@router.put(f"{P}/retention")
def dispatch_retention_put(ctx: Ctx, db: Session = Depends(get_db), body: dict = Body(...)) -> dict:
    return _run(ctx, "dispatch", _partners.retention_put, db, ctx, body)


@router.post(f"{P}/retention/run")
def dispatch_retention_run(ctx: Ctx, db: Session = Depends(get_db), dry_run: bool = Query(True)) -> dict:
    """Dry run by default: counts GPS pings, POD references and POD image files past the limits."""
    if not dry_run:
        role = getattr(getattr(ctx, "role", None), "value", str(getattr(ctx, "role", "")))
        if role not in {"super_admin", "admin"}:
            raise HTTPException(status_code=403, detail="retention_admin_only")
    return _run(ctx, "dispatch", _partners.retention_run, db, ctx, dry_run=dry_run)
