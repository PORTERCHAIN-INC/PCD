"""admin routes — orders."""

from datetime import datetime

from porterchain_api.routers.admin._deps import (
    AdminContext,
    AdminOrderFilters,
    Annotated,
    Depends,
    HTTPException,
    AdminCreateOrderRequest,
    AdminCreateOrderResponse,
    OrderBulkRequest,
    OrderTemperatureRequest,
    OrderDashboardResponse,
    OrderDetail360Response,
    OrderListItem,
    Session,
    Settings,
    _orders,
    get_admin_context,
    get_db,
    get_settings,
    require_module,
    router,
)


@router.get("/orders/dashboard", response_model=OrderDashboardResponse)
def orders_dashboard(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> OrderDashboardResponse:
    require_module(ctx, "orders_read")
    return OrderDashboardResponse(**_orders.dashboard(db))


@router.get("/orders/reports")
def orders_reports(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> dict:
    require_module(ctx, "orders_read")
    return _orders.reports(db)


@router.get("/orders", response_model=list[OrderListItem])
def list_orders(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    state: str | None = None,
    payment_status: str | None = None,
    invoice_status: str | None = None,
    merchant_id: str | None = None,
    driver_id: str | None = None,
    customer_id: str | None = None,
    priority: str | None = None,
    service_type: str | None = None,
    city: str | None = None,
    search: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    amount_min_cents: int | None = None,
    amount_max_cents: int | None = None,
    limit: int = 500,
    offset: int = 0,
) -> list[OrderListItem]:
    require_module(ctx, "orders_read")
    filters = AdminOrderFilters(
        state=state,
        payment_status=payment_status,
        invoice_status=invoice_status,
        merchant_id=merchant_id,
        driver_id=driver_id,
        customer_id=customer_id,
        priority=priority,
        service_type=service_type,
        city=city,
        search=search,
        date_from=datetime.fromisoformat(date_from) if date_from else None,
        date_to=datetime.fromisoformat(date_to) if date_to else None,
        amount_min_cents=amount_min_cents,
        amount_max_cents=amount_max_cents,
        limit=limit,
        offset=offset,
    )
    return [OrderListItem(**row) for row in _orders.list_enriched(db, filters)]


@router.post("/orders", response_model=AdminCreateOrderResponse)
def create_order(
    body: AdminCreateOrderRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> AdminCreateOrderResponse:
    """Multi-waypoint order builder — persists rich compliance_metadata.stops for Fleetbase."""
    require_module(ctx, "orders_write")
    from porterchain_api.admin_engine.order_builder_service import OrderBuilderService

    try:
        result = OrderBuilderService().create(db, settings, ctx, body)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return AdminCreateOrderResponse(**result)


@router.post("/orders/bulk")
def orders_bulk(
    body: OrderBulkRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    require_module(ctx, "orders_write")
    results = _orders.bulk_action(
        db,
        settings,
        ctx,
        body.order_ids,
        body.action,
        driver_id=body.driver_id,
    )
    return {"results": results}


@router.get("/orders/{order_id}", response_model=OrderDetail360Response)
def get_order_detail(
    order_id: str,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> OrderDetail360Response:
    require_module(ctx, "orders_read")
    detail = _orders.get_detail_360(db, settings, order_id)
    if not detail:
        raise HTTPException(status_code=404, detail="order_not_found")
    return OrderDetail360Response(**detail)


@router.get("/orders/{order_id}/tracking")
def get_order_tracking(
    order_id: str,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    require_module(ctx, "orders_read")
    tracking = _orders.order_tracking(db, settings, order_id)
    if not tracking:
        raise HTTPException(status_code=404, detail="order_not_found")
    return tracking


@router.get("/orders/{order_id}/timeline")
def order_timeline(
    order_id: str,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "orders_read")
    events = _orders.order_timeline(db, order_id)
    return [
        {
            "event_type": e.event_type,
            "from_state": e.from_state,
            "to_state": e.to_state,
            "occurred_at": e.occurred_at.isoformat(),
            "payload": e.payload,
        }
        for e in events
    ]


@router.get("/orders/{order_id}/audit-export")
def order_audit_export(
    order_id: str,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> dict:
    """§8.1.4 — compliance audit trail export."""
    require_module(ctx, "orders_read")
    payload = _orders.audit_export(db, order_id)
    if not payload:
        raise HTTPException(status_code=404, detail="order_not_found")
    return payload


@router.post("/orders/{order_id}/temperature")
def record_order_temperature(
    order_id: str,
    body: OrderTemperatureRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    """§8.1.3 — record cold-chain reading; alerts on excursion."""
    require_module(ctx, "orders_write")
    from porterchain_api.booking_engine.medical_compliance import MedicalComplianceService

    try:
        return MedicalComplianceService().record_temperature(
            db,
            settings,
            order_id,
            celsius=body.celsius,
            actor_type="admin",
            actor_id=ctx.user.id,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/orders/{order_id}/compliance-dossier.pdf")
def order_compliance_dossier_pdf(
    order_id: str,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
):
    """§8.1.13 — compliance PDF dossier for audit / regulatory review."""
    from fastapi.responses import Response

    require_module(ctx, "orders_read")
    result = _orders.compliance_dossier_pdf(db, order_id)
    if not result:
        raise HTTPException(status_code=404, detail="order_not_found")
    pdf, filename = result
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/orders/{order_id}/invoice")
def generate_order_invoice(
    order_id: str,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> dict:
    """Manual Generate invoice — requires POD_COMPLETED (idempotent if INVOICED)."""
    require_module(ctx, "orders_write")
    from porterchain_api.booking_engine.invoice_service import InvoiceService

    try:
        invoice = InvoiceService().manual_invoice(db, order_id)
        db.commit()
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "order_id": order_id,
        "invoice_id": invoice.id,
        "invoice_number": invoice.invoice_number,
        "receipt_number": invoice.receipt_number,
        "amount_cents": invoice.amount_cents,
    }


@router.post("/orders/{order_id}/resend-receipt")
def resend_order_receipt(
    order_id: str,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> dict:
    """Resend HTML payment/invoice receipt email via notification engine."""
    require_module(ctx, "orders_write")
    from porterchain_api.booking_engine.invoice_service import InvoiceService

    try:
        result = InvoiceService().resend_receipt(db, order_id)
        db.commit()
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return result


@router.get("/orders/{order_id}/label.pdf")
def order_label_pdf(
    order_id: str,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
):
    """Shipping label PDF for warehouse print (PC commercial doc)."""
    from fastapi.responses import Response

    require_module(ctx, "orders_read")
    result = _orders.label_pdf(db, order_id)
    if not result:
        raise HTTPException(status_code=404, detail="order_not_found")
    pdf, filename = result
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/orders/{order_id}/manifest.pdf")
def order_manifest_pdf(
    order_id: str,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
):
    """Single-order dispatch manifest PDF."""
    from fastapi.responses import Response

    require_module(ctx, "orders_read")
    result = _orders.manifest_pdf(db, order_id)
    if not result:
        raise HTTPException(status_code=404, detail="order_not_found")
    pdf, filename = result
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/orders/{order_id}/invoice.pdf")
def order_invoice_pdf(
    order_id: str,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
):
    """Commercial invoice PDF when Stripe-hosted PDF is absent."""
    from fastapi.responses import Response

    require_module(ctx, "orders_read")
    result = _orders.invoice_pdf(db, order_id)
    if not result:
        raise HTTPException(status_code=404, detail="invoice_not_found")
    pdf, filename = result
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/orders/{order_id}/assist")
def order_assist(
    order_id: str,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    """Scoped Order 360 assist — proposals + playbooks (propose-only)."""
    require_module(ctx, "orders_read")
    from porterchain_api.admin_engine.order_assist_service import OrderAssistService

    try:
        return OrderAssistService().assist(db, settings, order_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/orders/{order_id}/assist/decide")
def order_assist_decide(
    order_id: str,
    body: dict,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    """Accept or reject an assist proposal. Accept runs existing write APIs only."""
    require_module(ctx, "orders_write")
    from porterchain_api.admin_engine.order_assist_service import OrderAssistService

    proposal_id = str(body.get("proposal_id") or "")
    decision = str(body.get("decision") or "")
    payload = body.get("payload") if isinstance(body.get("payload"), dict) else {}
    if not proposal_id or not decision:
        raise HTTPException(status_code=400, detail="proposal_id_and_decision_required")
    try:
        result = OrderAssistService().decide(
            db,
            settings,
            ctx,
            order_id,
            proposal_id=proposal_id,
            decision=decision,
            payload=payload,
        )
        db.commit()
        return result
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/orders/{order_id}/playbooks/{playbook_id}")
def order_run_playbook(
    order_id: str,
    playbook_id: str,
    body: dict,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    """Run a named playbook — requires confirm:true (no silent writes)."""
    require_module(ctx, "orders_write")
    from porterchain_api.admin_engine.order_assist_service import OrderAssistService

    confirm = bool(body.get("confirm"))
    note = body.get("note") if isinstance(body.get("note"), str) else None
    try:
        result = OrderAssistService().run_playbook(
            db,
            settings,
            ctx,
            order_id,
            playbook_id,
            confirm=confirm,
            note=note,
        )
        db.commit()
        return result
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
