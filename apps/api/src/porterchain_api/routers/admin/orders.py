"""admin routes — orders."""

from fastapi.responses import RedirectResponse, Response

from porterchain_api.admin_engine.orders_service import build_admin_order_filters
from porterchain_api.merchant_engine.parcel_amend_service import ParcelAmendError, parcel_amend_http
from porterchain_api.reporting.pod_export import PodFetchFailed, PodUnavailable, pod_error_message
from porterchain_api.schemas_merchant import OrderParcelsPatchRequest, OrderParcelsPatchResponse
from porterchain_api.routers.admin._deps import (
    AdminContext,
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
    OrderListPage,
    Query,
    Session,
    Settings,
    _orders,
    get_admin_context,
    get_db,
    get_settings,
    require_module,
    router,
)

Ctx = Annotated[AdminContext, Depends(get_admin_context)]


def _invoke(ctx: AdminContext, module: str, fn, *args, **kwargs):
    try:
        require_module(ctx, module)
        return fn(*args, **kwargs)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ParcelAmendError as exc:
        status, message = parcel_amend_http(exc)
        raise HTTPException(status_code=status, detail=message) from exc
    except PodFetchFailed as exc:
        raise HTTPException(status_code=502, detail=pod_error_message(str(exc))) from None
    except PodUnavailable as exc:
        raise HTTPException(status_code=404, detail=pod_error_message(str(exc))) from None
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _attachment(content: bytes, filename: str, media_type: str = "application/pdf") -> Response:
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/orders/dashboard", response_model=OrderDashboardResponse)
def orders_dashboard(ctx: Ctx, db: Session = Depends(get_db)) -> OrderDashboardResponse:
    return OrderDashboardResponse(**_invoke(ctx, "orders_read", _orders.dashboard, db))


@router.get("/orders/reports")
def orders_reports(ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    return _invoke(ctx, "orders_read", _orders.reports, db)


@router.get("/orders", response_model=OrderListPage)
def list_orders(
    ctx: Ctx,
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
    date_field: str | None = None,
    queue: str | None = None,
    include_carryover: bool = Query(False),
    amount_min_cents: int | None = None,
    amount_max_cents: int | None = None,
    include_sandbox: bool = Query(False),
    sandbox_only: bool = Query(False),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> OrderListPage:
    filters = _invoke(
        ctx, "orders_read", build_admin_order_filters,
        state=state, payment_status=payment_status, invoice_status=invoice_status,
        merchant_id=merchant_id, driver_id=driver_id, customer_id=customer_id,
        priority=priority, service_type=service_type, city=city, search=search,
        date_from=date_from, date_to=date_to, date_field=date_field, queue=queue,
        include_carryover=include_carryover, amount_min_cents=amount_min_cents,
        amount_max_cents=amount_max_cents, include_sandbox=include_sandbox,
        sandbox_only=sandbox_only, limit=limit, offset=offset,
    )
    page = _invoke(ctx, "orders_read", _orders.list_page, db, filters)
    return OrderListPage(
        items=[OrderListItem(**row) for row in page["items"]],
        total=page["total"],
        limit=page["limit"],
        offset=page["offset"],
    )


@router.post("/orders", response_model=AdminCreateOrderResponse)
def create_order(
    body: AdminCreateOrderRequest,
    ctx: Ctx,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> AdminCreateOrderResponse:
    """Multi-waypoint order builder — persists rich compliance_metadata.stops for Fleetbase."""
    return AdminCreateOrderResponse(**_invoke(ctx, "orders_write", _orders.create_built, db, settings, ctx, body))


@router.post("/orders/bulk")
def orders_bulk(
    body: OrderBulkRequest,
    ctx: Ctx,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    return _invoke(ctx, "orders_write", _orders.bulk_results, db, settings, ctx, body)


@router.post("/orders/labels/bulk")
def order_labels_bulk_pdf(body: dict, ctx: Ctx, db: Session = Depends(get_db)):
    pdf, filename = _invoke(ctx, "orders_read", _orders.labels_bulk_from_body, db, body)
    return _attachment(pdf, filename)


@router.get("/orders/pickup-manifest.pdf")
def orders_pickup_manifest_pdf(
    ctx: Ctx, db: Session = Depends(get_db), ids: list[str] = Query(default_factory=list)
):
    pdf, filename = _invoke(ctx, "orders_read", _orders.pickup_manifest_required, db, ids)
    return _attachment(pdf, filename)


@router.get("/orders/{order_id}", response_model=OrderDetail360Response)
def get_order_detail(
    order_id: str, ctx: Ctx, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)
) -> OrderDetail360Response:
    return OrderDetail360Response(
        **_invoke(ctx, "orders_read", _orders.require_detail_360, db, settings, order_id)
    )


@router.patch("/orders/{order_id}/parcels", response_model=OrderParcelsPatchResponse)
def admin_amend_parcels(
    order_id: str,
    body: OrderParcelsPatchRequest,
    ctx: Ctx,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> OrderParcelsPatchResponse:
    return OrderParcelsPatchResponse(
        **_invoke(
            ctx,
            "orders_write",
            _orders.amend_parcels,
            db,
            ctx,
            order_id,
            [s.model_dump(exclude_unset=True) for s in body.stops],
            vehicle_class=body.vehicle_class,
            settings=settings,
        )
    )


@router.get("/orders/{order_id}/tracking")
def get_order_tracking(
    order_id: str, ctx: Ctx, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)
) -> dict:
    return _invoke(ctx, "orders_read", _orders.require_tracking, db, settings, order_id)


@router.get("/orders/{order_id}/timeline")
def order_timeline(order_id: str, ctx: Ctx, db: Session = Depends(get_db)):
    return _invoke(ctx, "orders_read", _orders.timeline_payload, db, order_id)


@router.get("/orders/{order_id}/audit-export")
def order_audit_export(order_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    """§8.1.4 — compliance audit trail export."""
    return _invoke(ctx, "orders_read", _orders.require_audit_export, db, order_id)


@router.post("/orders/{order_id}/temperature")
def record_order_temperature(
    order_id: str,
    body: OrderTemperatureRequest,
    ctx: Ctx,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    """§8.1.3 — record cold-chain reading; alerts on excursion."""
    return _invoke(
        ctx, "orders_write", _orders.record_admin_temperature, db, settings, ctx, order_id, body.celsius
    )


@router.get("/orders/{order_id}/compliance-dossier.pdf")
def order_compliance_dossier_pdf(order_id: str, ctx: Ctx, db: Session = Depends(get_db)):
    """§8.1.13 — compliance PDF dossier for audit / regulatory review."""
    pdf, filename = _invoke(ctx, "orders_read", _orders.compliance_dossier_required, db, order_id)
    return _attachment(pdf, filename)


@router.get("/orders/{order_id}/pod.zip")
def order_pod_bundle(
    order_id: str, ctx: Ctx, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)
):
    """Download every POD photo and the signature for one shipment (BR)."""
    archive, filename = _invoke(ctx, "orders_read", _orders.pod_bundle, db, settings, order_id)
    return _attachment(archive, filename, "application/zip")


@router.get("/orders/{order_id}/pod/{slug}")
def order_pod_artifact(
    order_id: str,
    slug: str,
    ctx: Ctx,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """Download one POD photo or the signature (BR).

    The caller names an artifact, never a URL: the media address comes from the
    shipment's own proofs so this cannot be pointed at anything else.
    """
    payload, media_type, filename = _invoke(
        ctx, "orders_read", _orders.pod_artifact, db, settings, order_id, slug
    )
    return _attachment(payload, filename, media_type)


@router.post("/orders/{order_id}/invoice")
def generate_order_invoice(order_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    """Manual Generate invoice — requires POD_COMPLETED (idempotent if INVOICED)."""
    return _invoke(ctx, "orders_write", _orders.manual_invoice_payload, db, order_id)


@router.post("/orders/{order_id}/resend-receipt")
def resend_order_receipt(order_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    """Resend HTML payment/invoice receipt email via notification engine."""
    return _invoke(ctx, "orders_write", _orders.resend_receipt_committed, db, order_id)


@router.get("/orders/{order_id}/label.pdf")
def order_label_pdf(order_id: str, ctx: Ctx):
    """Retired dishonest dock alias — use labels.pdf (4×6 thermal)."""
    _invoke(ctx, "orders_read", lambda: None)
    return RedirectResponse(url=f"/v1/admin/orders/{order_id}/labels.pdf", status_code=307)


@router.get("/orders/{order_id}/labels.pdf")
def order_labels_pdf(order_id: str, ctx: Ctx, db: Session = Depends(get_db)):
    """4×6 thermal labels — one PDF page per package."""
    pdf, filename = _invoke(ctx, "orders_read", _orders.labels_pdf_required, db, order_id)
    return _attachment(pdf, filename)


@router.get("/orders/{order_id}/manifest.pdf")
def order_manifest_pdf(order_id: str, ctx: Ctx, db: Session = Depends(get_db)):
    """Single-order pickup list PDF (not a Fleetbase vehicle manifest)."""
    pdf, filename = _invoke(ctx, "orders_read", _orders.manifest_pdf_required, db, order_id)
    return _attachment(pdf, filename)


@router.get("/orders/{order_id}/invoice.pdf")
def order_invoice_pdf(order_id: str, ctx: Ctx, db: Session = Depends(get_db)):
    """Commercial invoice PDF when Stripe-hosted PDF is absent."""
    pdf, filename = _invoke(ctx, "orders_read", _orders.invoice_pdf_required, db, order_id)
    return _attachment(pdf, filename)


@router.get("/orders/{order_id}/assist")
def order_assist(
    order_id: str, ctx: Ctx, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)
) -> dict:
    """Scoped Order 360 assist — proposals + playbooks (propose-only)."""
    return _invoke(ctx, "orders_read", _orders.assist, db, settings, order_id)


@router.post("/orders/{order_id}/assist/decide")
def order_assist_decide(
    order_id: str,
    body: dict,
    ctx: Ctx,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    """Accept or reject an assist proposal. Accept runs existing write APIs only."""
    return _invoke(ctx, "orders_write", _orders.assist_decide_from_body, db, settings, ctx, order_id, body)


@router.post("/orders/{order_id}/playbooks/{playbook_id}")
def order_run_playbook(
    order_id: str,
    playbook_id: str,
    body: dict,
    ctx: Ctx,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    """Run a named playbook — requires confirm:true (no silent writes)."""
    return _invoke(
        ctx, "orders_write", _orders.run_playbook_from_body, db, settings, ctx, order_id, playbook_id, body
    )


@router.post("/orders/{order_id}/shopify/release")
def order_shopify_release(
    order_id: str,
    ctx: Ctx,
    db: Session = Depends(get_db),
) -> dict:
    """Release a held Shopify BOOKED order to Fleetbase (DISPATCH_READY)."""
    from porterchain_api.admin_engine.shopify_control_service import release_shopify_order_to_dispatch

    return _invoke(ctx, "orders_write", release_shopify_order_to_dispatch, db, ctx, order_id)


@router.post("/orders/{order_id}/shopify/repush-fulfillment")
def order_shopify_repush_fulfillment(
    order_id: str,
    ctx: Ctx,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    """Manually re-push Shopify fulfillment / tracking for a Shopify order."""
    from porterchain_api.admin_engine.shopify_control_service import repush_shopify_fulfillment

    try:
        require_module(ctx, "orders_write")
        return repush_shopify_fulfillment(db, ctx, order_id, settings)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

