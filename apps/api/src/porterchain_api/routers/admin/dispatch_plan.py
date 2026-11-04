"""admin routes — Dispatch Phase 2: fleet plans, re-plan, commit, explain, partners, legs, retention."""

from fastapi import Body, Query, Response

from porterchain_api.admin_engine.fleet_contracts_service import FleetContractsService
from porterchain_api.admin_engine.fleet_plan_service import FleetPlanService
from porterchain_api.admin_engine.logistics_partners_service import HubSplitService, LogisticsPartnersService
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
_hub = HubSplitService()
_contracts = FleetContractsService()
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
    def read() -> dict:
        plan = _plans.latest(db)
        return {"plan": plan, **_plans.insights(db, plan)}

    return _run(ctx, "dispatch_read", read)


@router.post(f"{P}/plans")
def dispatch_plan_create(ctx: Ctx, db: Session = Depends(get_db), body: dict = Body(default={})) -> dict:
    """Plan the day: every waiting order, every online vehicle. Draft unless ``commit`` is true
    (Ops Today "Optimize routes": draft + commit in one call; undo via /plans/{id}/undo)."""
    ids = body.get("order_ids") if isinstance(body.get("order_ids"), list) else None
    limit = int(body.get("time_limit_s") or 5)
    draft = _run(ctx, "dispatch", _plans.plan, db, actor=_actor(ctx), order_ids=ids, time_limit_s=max(1, min(limit, 30)))
    if body.get("commit") is True:
        from porterchain_api.config import get_settings

        return _run(ctx, "dispatch", _plans.commit, db, get_settings(), ctx, draft["id"])
    return draft


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


@router.post(f"{P}/plans/{{plan_id}}/undo")
def dispatch_plan_undo(plan_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    """Undo a commit (15 min): release only orders still DRIVER_ASSIGNED to the planned driver."""
    return _run(ctx, "dispatch", _plans.undo, db, ctx, plan_id)


@router.post(f"{P}/plans/{{plan_id}}/explain")
def dispatch_plan_explain(plan_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    """Explain + suggest only (rules; an LLM (FEATURE_AI, off in Phase 0) when enabled). Never changes the plan."""
    return _run(ctx, "dispatch_read", _plans.explain, db, plan_id)


# ---------------------------------------------------------------- partners + legs
@router.get(f"{P}/partners")
def dispatch_partners(ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    return _run(ctx, "dispatch_read", lambda: {"items": _partners.list(db)})


@router.get(f"{P}/partners/stats")
def dispatch_partner_stats(ctx: Ctx, db: Session = Depends(get_db), days: int = Query(30, ge=1, le=365)) -> dict:
    return _run(ctx, "dispatch_read", _partners.stats, db, days=days)


@router.post(f"{P}/partners/bulk-active")
def dispatch_partner_bulk_active(ctx: Ctx, db: Session = Depends(get_db), body: dict = Body(...)) -> dict:
    """Pause or reactivate several partners at once (audited per partner)."""
    return _run(ctx, "dispatch", _partners.bulk_active, db, ctx, list(body.get("ids") or []), bool(body.get("active")))


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


@router.post(f"{P}/orders/{{order_id}}/partner-leg")
def dispatch_order_assign_partner(order_id: str, ctx: Ctx, db: Session = Depends(get_db), body: dict = Body(...)) -> dict:
    """L97: hand the order to a courier / contractor fleet partner (one pickup → drop leg)."""
    return _run(ctx, "dispatch", _partners.assign_partner_leg, db, ctx, order_id,
                str(body.get("partner_id") or ""), body.get("note"))


@router.get(f"{P}/orders/{{order_id}}/hub-split")
def dispatch_order_hub_split(order_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    return _run(ctx, "dispatch_read", _hub.view, db, order_id)


@router.post(f"{P}/orders/{{order_id}}/hub-split")
def dispatch_order_hub_split_create(order_id: str, ctx: Ctx, db: Session = Depends(get_db),
                                    body: dict = Body(...)) -> dict:
    """Split at warehouse: pickup leg -> hub, delivery leg hub -> customer (own drivers)."""
    from porterchain_api.config import get_settings

    return _run(ctx, "dispatch", _hub.split, db, get_settings(), ctx, order_id,
                hub_partner_id=str(body.get("hub_partner_id") or ""),
                pickup_driver_id=body.get("pickup_driver_id") or None,
                delivery_driver_id=body.get("delivery_driver_id") or None)


@router.post(f"{P}/orders/{{order_id}}/delivery-leg")
def dispatch_order_release_delivery(order_id: str, ctx: Ctx, db: Session = Depends(get_db),
                                    body: dict = Body(default={})) -> dict:
    """Collect-only / warehouse parcel: create the delivery leg (Plan the day sees it), optionally assign."""
    from porterchain_api.config import get_settings

    return _run(ctx, "dispatch", _hub.release_delivery_leg, db, get_settings(), ctx, order_id,
                driver_id=(body or {}).get("driver_id") or None)


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


@router.post(f"{P}/partner-legs/{{leg_id}}/sync-order")
def dispatch_partner_leg_sync_order(leg_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    """L140 backfill: final leg delivered before the fix -> move the order to Delivered."""
    return _run(ctx, "dispatch", _partners.sync_order_from_leg, db, ctx, leg_id)


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


# ---------------------------------------------------------------- fleet partner contracts
@router.get(f"{P}/fleet-contracts")
def fleet_contracts_list(ctx: Ctx, db: Session = Depends(get_db), partner_id: str | None = Query(None)) -> dict:
    return _run(ctx, "dispatch_read", lambda: {"items": _contracts.list(db, partner_id)})


@router.post(f"{P}/fleet-contracts")
def fleet_contracts_create(ctx: Ctx, db: Session = Depends(get_db), body: dict = Body(...)) -> dict:
    return _run(ctx, "dispatch", _contracts.upsert, db, ctx, body)


@router.put(f"{P}/fleet-contracts/{{contract_id}}")
def fleet_contracts_update(contract_id: str, ctx: Ctx, db: Session = Depends(get_db), body: dict = Body(...)) -> dict:
    return _run(ctx, "dispatch", _contracts.upsert, db, ctx, body, contract_id)


@router.delete(f"{P}/fleet-contracts/{{contract_id}}")
def fleet_contracts_delete(contract_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    return _run(ctx, "dispatch", _contracts.delete, db, ctx, contract_id)


@router.get(f"{P}/partners/{{partner_id}}/payable-statement")
def fleet_payable_statement(
    partner_id: str, ctx: Ctx, db: Session = Depends(get_db),
    start: str = Query(...), end: str = Query(...),
) -> dict:
    from datetime import date as _date

    def go():
        try:
            s, e = _date.fromisoformat(start), _date.fromisoformat(end)
        except ValueError as exc:
            raise ValueError("start/end must be YYYY-MM-DD") from exc
        if e < s:
            raise ValueError("end must be on or after start")
        return _contracts.payable_statement(db, partner_id, s, e)

    return _run(ctx, "dispatch_read", go)


# ---------------------------------------------------------------- free-text translations (admin = English)
_TRANSLATION_MODULE = {"order": "orders_read", "booking": "orders_read", "claim": "claims_read",
                       "support_ticket": "support_read"}


@router.get("/translations")
def free_text_translations(
    ctx: Ctx, db: Session = Depends(get_db),
    entity_type: str = Query(...), entity_id: str = Query(...),
) -> dict:
    from porterchain_api.platform.free_text_translation import for_entity

    module = _TRANSLATION_MODULE.get(entity_type)
    if module is None:
        raise HTTPException(status_code=400, detail="unknown entity_type")
    return _run(ctx, module, lambda: {"items": for_entity(db, entity_type, entity_id)})
