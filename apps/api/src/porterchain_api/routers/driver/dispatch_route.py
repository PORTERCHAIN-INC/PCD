"""Driver routes — committed Dispatch route + stop-level check-ins (GPS, POD)."""

from fastapi import Body

from porterchain_api.routers.driver._deps import (
    Annotated,
    Depends,
    DriverContext,
    HTTPException,
    Session,
    get_db,
    get_driver_context,
    require_approved_driver,
    router,
    svc)


def _route_svc():
    from porterchain_api.dispatch_engine.driver_route import DriverRouteService

    return DriverRouteService()


def _scan_gate(db: Session):
    from porterchain_api.merchant_engine.scan_gate_service import ScanGateService

    gate = ScanGateService()
    return lambda order, phase: gate.scan_progress(db, order, phase=phase)


def _with_scans(db: Session, view: dict) -> dict:
    """Per stop: boxes scanned / required for that stop's phase (read-only rollup)."""
    from porterchain_api.dispatch_engine.driver_route import PICKUP_KINDS
    from porterchain_api.merchant_engine.scan_gate_service import ScanGateService

    route = view.get("route")
    if not route:
        return view
    progress = ScanGateService().progress_by_order_ids(db, list({s["order_id"] for s in route["stops"]}))
    for s in route["stops"]:
        p = progress.get(s["order_id"], {})
        phase = "scan_pickup" if s["kind"] in PICKUP_KINDS else "scan_delivery" if s["needs_pod"] else None
        s["scan"] = p.get(phase) if phase else None
    return view


@router.get("/dispatch/route")
def dispatch_route(
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db)):
    """Today's committed route: grouped stops in order, status per stop, next stop index."""
    require_approved_driver(ctx)
    return _with_scans(db, _route_svc().view(db, ctx.driver.id))


@router.post("/dispatch/stops/checkin")
def dispatch_checkin(
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
    body: dict = Body(...)):
    """``{keys, event, lat, lng, accuracy_m, note, pod_photo, client_id, short_reason}``.

    ``event``: arrived | picked_up | delivered | failed. Picked up / delivered need every box
    scanned; at a drop, ``short_reason`` confirms a short delivery and raises the missing-item
    alert. A customer drop needs a POD photo. ``client_id`` makes an offline replay a no-op.
    """
    require_approved_driver(ctx)

    def num(k: str) -> float | None:
        v = body.get(k)
        return float(v) if isinstance(v, (int, float)) else None

    try:
        out = _route_svc().check_in(
            db, ctx.driver, keys=[str(k) for k in body.get("keys") or []], event=str(body.get("event") or ""),
            lat=num("lat"), lng=num("lng"), accuracy_m=num("accuracy_m"),
            note=str(body["note"]) if body.get("note") else None,
            pod_photo=str(body["pod_photo"]) if body.get("pod_photo") else None,
            client_id=str(body["client_id"])[:64] if body.get("client_id") else None,
            short_reason=str(body["short_reason"]) if body.get("short_reason") else None,
            scan_gate=_scan_gate(db),
        )
        return _with_scans(db, out)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/dispatch/orders/{order_id}/checklist")
def dispatch_stop_checklist(
    order_id: str,
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db)):
    """Pickup checklist per item. A multi-box item (e.g. furniture in 3 boxes) counts as one item."""
    require_approved_driver(ctx)
    from porterchain_api.merchant_engine.scan_gate_service import ScanGateService

    try:
        order = svc.require_assigned_order(db, driver_id=ctx.driver.id, order_id=order_id)
        data = ScanGateService().pickup_checklist(db, order)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    items = data.get("items") or []
    for it in items:
        n = int(it.get("box_count") or 1)
        it["counts_as"] = 1
        it["rule"] = f"{n} boxes · counts as 1 item" if n > 1 else None
    data["item_count"] = len(items)
    data["box_count"] = sum(len(it.get("boxes") or []) for it in items)
    return data
