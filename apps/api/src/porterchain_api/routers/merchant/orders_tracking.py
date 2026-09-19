"""merchant routes — orders_tracking."""

from collections.abc import Callable
from typing import TypeVar

from porterchain_api.merchant_engine.cancel_policy import cancel_error_message
from porterchain_api.merchant_engine.consignee_notify import consignee_error_message
from porterchain_api.merchant_engine.orders_service import MerchantOrderFilters, print_error_message
from porterchain_api.merchant_engine.parcel_amend_service import ParcelAmendError, parcel_amend_http
from porterchain_api.merchant_engine.toronto import parse_toronto_day_bound
from porterchain_api.merchant_engine.tracking_service import AmbiguousTrackingQuery, tracking_error_message
from porterchain_api.reporting.pod_export import PodFetchFailed, PodUnavailable, pod_error_message
from porterchain_api.routers.merchant._deps import (
    Annotated,
    Depends,
    HTTPException,
    MerchantContext,
    MerchantLiveTrackingResponse,
    MerchantOrder360Response,
    MerchantOrderBulkRequest,
    MerchantOrderResponse,
    MerchantOrdersDashboardResponse,
    MerchantTrackingDashboardResponse,
    MerchantTrackingEmailRequest,
    MerchantTrackingEmailResponse,
    OrderListItem,
    OrderListPage,
    OrderTrackingResponse,
    Query,
    Session,
    Settings,
    _handle_permission,
    _order_response,
    _orders,
    _tracking,
    get_db,
    get_merchant_context,
    get_settings,
    require_module,
    router,
)
from porterchain_api.schemas_merchant import (
    MerchantLabelsBulkRequest,
    OrderParcelsPatchRequest,
    OrderParcelsPatchResponse,
)

T = TypeVar("T")
Ctx = Annotated[MerchantContext, Depends(get_merchant_context)]


def _copy(exc: BaseException, mapper) -> str:
    return mapper(str(exc) or "order_not_found")


def _invoke(ctx: MerchantContext, module: str, fn: Callable[..., T], *args: object, copy=print_error_message, **kwargs: object) -> T:
    try:
        require_module(ctx, module)
        return fn(*args, **kwargs)
    except PermissionError as exc:
        _handle_permission(exc)
        raise
    except AmbiguousTrackingQuery as exc:
        raise HTTPException(
            status_code=409, detail={"message": exc.message, "choices": exc.choices()}
        ) from None
    except ParcelAmendError as exc:
        status, message = parcel_amend_http(exc)
        raise HTTPException(status_code=status, detail=message) from exc
    except PodFetchFailed as exc:
        raise HTTPException(status_code=502, detail=pod_error_message(str(exc))) from None
    except PodUnavailable as exc:
        raise HTTPException(status_code=404, detail=pod_error_message(str(exc))) from None
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=_copy(exc, copy)) from None
    except ValueError as exc:
        detail = str(exc)
        code = 413 if "too_many" in detail else 400
        raise HTTPException(status_code=code, detail=_copy(exc, copy)) from None


def _attachment(content: bytes, filename: str, media_type: str):
    from fastapi.responses import Response

    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/orders/dashboard", response_model=MerchantOrdersDashboardResponse)
def merchant_orders_dashboard(ctx: Ctx, db: Session = Depends(get_db)) -> MerchantOrdersDashboardResponse:
    return MerchantOrdersDashboardResponse(**_invoke(ctx, "orders", _orders.orders_dashboard, db, ctx))


@router.get("/orders", response_model=OrderListPage)
def list_orders(
    ctx: Ctx,
    db: Session = Depends(get_db),
    state: str | None = None,
    payment_status: str | None = None,
    invoice_status: str | None = None,
    driver_id: str | None = None,
    priority: str | None = None,
    service_type: str | None = None,
    city: str | None = None,
    search: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    amount_min_cents: int | None = None,
    amount_max_cents: int | None = None,
    include_sandbox: bool = Query(False),
    sandbox_only: bool = Query(False),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> OrderListPage:
    page = _invoke(
        ctx,
        "orders",
        _orders.list_page,
        db,
        ctx,
        MerchantOrderFilters(
            state=state,
            payment_status=payment_status,
            invoice_status=invoice_status,
            driver_id=driver_id,
            priority=priority,
            service_type=service_type,
            city=city,
            search=search,
            date_from=parse_toronto_day_bound(date_from, end=False),
            date_to=parse_toronto_day_bound(date_to, end=True),
            amount_min_cents=amount_min_cents,
            amount_max_cents=amount_max_cents,
            include_sandbox=include_sandbox or sandbox_only,
            sandbox_only=sandbox_only,
            limit=limit,
            offset=offset,
        ),
    )
    return OrderListPage(
        items=[OrderListItem(**row) for row in page["items"]],
        total=page["total"],
        limit=page["limit"],
        offset=page["offset"],
    )


@router.get("/orders/pickup-list.pdf")
def merchant_pickup_list_pdf(ctx: Ctx, db: Session = Depends(get_db), ids: list[str] = Query(default_factory=list)):
    """Dock pickup list — not a Fleetbase manifest or carrier label."""
    pdf, filename = _invoke(ctx, "orders", _orders.pickup_list_pdf, db, ctx, ids)
    return _attachment(pdf, filename, "application/pdf")


@router.get("/orders/pickup-manifest.pdf")
def merchant_pickup_manifest_pdf(ctx: Ctx, db: Session = Depends(get_db), ids: list[str] = Query(default_factory=list)):
    """Box-count pickup manifest (thermal labels companion)."""
    pdf, filename = _invoke(ctx, "orders", _orders.pickup_manifest_pdf, db, ctx, ids)
    return _attachment(pdf, filename, "application/pdf")


@router.post("/orders/labels/bulk")
def merchant_labels_bulk_pdf(body: MerchantLabelsBulkRequest, ctx: Ctx, db: Session = Depends(get_db)):
    """Bulk 4×6 thermal labels — max 100 orders / 500 pages."""
    pdf, filename = _invoke(ctx, "orders", _orders.labels_bulk_pdf, db, ctx, body.order_ids)
    return _attachment(pdf, filename, "application/pdf")


@router.post("/orders/bulk")
def merchant_orders_bulk(
    body: MerchantOrderBulkRequest, ctx: Ctx, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)
) -> dict:
    results = _invoke(ctx, "orders_write", _orders.bulk_action, db, settings, ctx, body.order_ids, body.action)
    ok_count = sum(1 for row in results if row.get("ok"))
    return {"results": results, "ok_count": ok_count, "failed_count": len(results) - ok_count}


@router.get("/orders/{order_id}", response_model=MerchantOrderResponse)
def get_order(order_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> MerchantOrderResponse:
    order = _invoke(ctx, "orders", _orders.get_order, db, ctx, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="order_not_found")
    return _order_response(order)


@router.get("/orders/{order_id}/360", response_model=MerchantOrder360Response)
def merchant_order_360(
    order_id: str, ctx: Ctx, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)
) -> MerchantOrder360Response:
    return MerchantOrder360Response(**_invoke(ctx, "orders", _orders.get_detail_360, db, settings, ctx, order_id))


@router.patch("/orders/{order_id}/parcels", response_model=OrderParcelsPatchResponse)
def merchant_amend_parcels(
    order_id: str,
    body: OrderParcelsPatchRequest,
    ctx: Ctx,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> OrderParcelsPatchResponse:
    result = _invoke(
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
    return OrderParcelsPatchResponse(**result)


@router.get("/orders/{order_id}/tracking", response_model=MerchantLiveTrackingResponse)
def merchant_order_tracking(
    order_id: str, ctx: Ctx, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)
) -> MerchantLiveTrackingResponse:
    return MerchantLiveTrackingResponse(
        **_invoke(ctx, "tracking", _tracking.live_tracking, db, settings, ctx, order_id, copy=tracking_error_message)
    )


@router.get("/tracking/dashboard", response_model=MerchantTrackingDashboardResponse)
def merchant_tracking_dashboard(
    ctx: Ctx, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)
) -> MerchantTrackingDashboardResponse:
    return MerchantTrackingDashboardResponse(**_invoke(ctx, "tracking", _tracking.dashboard, db, settings, ctx))


@router.get("/track/{tracking_number}", response_model=OrderTrackingResponse)
def track_by_number(
    tracking_number: str, ctx: Ctx, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)
) -> OrderTrackingResponse:
    """Accepts a tracking number, an order number, or a PO (BK)."""

    def _run() -> OrderTrackingResponse:
        live = _tracking.track_by_number(db, settings, ctx, tracking_number)
        order = _orders.get_order(db, ctx, str(live["order_id"]))
        if not order:
            raise LookupError("tracking_not_found")
        return OrderTrackingResponse(
            order=_order_response(order),
            timeline=live.get("timeline") or live.get("tracking_history") or [],
            live_tracking=live,
        )

    return _invoke(ctx, "tracking", _run, copy=tracking_error_message)


@router.post("/orders/{order_id}/tracking-email", response_model=MerchantTrackingEmailResponse)
def merchant_email_consignee_tracking(
    order_id: str,
    ctx: Ctx,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    body: MerchantTrackingEmailRequest | None = None,
) -> MerchantTrackingEmailResponse:
    payload = body or MerchantTrackingEmailRequest()
    result = _invoke(
        ctx,
        "orders_write",
        _orders.email_consignee_tracking,
        db,
        settings,
        ctx,
        order_id,
        payload.email,
        copy=consignee_error_message,
    )
    return MerchantTrackingEmailResponse(**result)


@router.post("/orders/{order_id}/cancel", response_model=MerchantOrderResponse)
def cancel_order(
    order_id: str, ctx: Ctx, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)
) -> MerchantOrderResponse:
    order = _invoke(
        ctx, "orders_write", _orders.cancel_owned, db, ctx, order_id, settings, copy=cancel_error_message
    )
    return _order_response(order)


@router.post("/orders/{order_id}/duplicate", response_model=MerchantOrderResponse)
def duplicate_order(
    order_id: str, ctx: Ctx, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)
) -> MerchantOrderResponse:
    return _order_response(_invoke(ctx, "orders_write", _orders.duplicate_owned, db, settings, ctx, order_id))


@router.get("/orders/{order_id}/compliance-dossier.pdf")
def merchant_compliance_dossier_pdf(order_id: str, ctx: Ctx, db: Session = Depends(get_db)):
    """§8.1.13 — download compliance dossier for owned orders."""
    pdf, filename = _invoke(ctx, "orders", _orders.compliance_dossier_pdf, db, ctx, order_id)
    return _attachment(pdf, filename, "application/pdf")


@router.get("/orders/{order_id}/pod.zip")
def merchant_pod_bundle(
    order_id: str, ctx: Ctx, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)
):
    """Download every POD photo and the signature for one shipment (BR)."""
    archive, filename = _invoke(
        ctx, "orders", _orders.pod_bundle, db, settings, ctx, order_id, copy=pod_error_message
    )
    return _attachment(archive, filename, "application/zip")


@router.get("/orders/{order_id}/pod/{slug}")
def merchant_pod_artifact(
    order_id: str, slug: str, ctx: Ctx, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)
):
    """Download one POD photo or the signature (BR).

    The caller names an artifact, never a URL: the media address comes from the
    shipment's own proofs so this cannot be pointed at anything else.
    """
    payload, media_type, filename = _invoke(
        ctx, "orders", _orders.pod_artifact, db, settings, ctx, order_id, slug, copy=pod_error_message
    )
    return _attachment(payload, filename, media_type)


@router.get("/orders/{order_id}/print-preview.pdf")
def merchant_print_preview_pdf(order_id: str, ctx: Ctx, db: Session = Depends(get_db)):
    """One-order dock sheet. Not a carrier shipping label."""
    pdf, filename = _invoke(ctx, "orders", _orders.print_preview_pdf, db, ctx, order_id)
    return _attachment(pdf, filename, "application/pdf")


@router.get("/orders/{order_id}/labels.pdf")
def merchant_labels_pdf(order_id: str, ctx: Ctx, db: Session = Depends(get_db)):
    """4×6 thermal labels — one PDF page per package."""
    pdf, filename = _invoke(ctx, "orders", _orders.labels_pdf, db, ctx, order_id)
    return _attachment(pdf, filename, "application/pdf")
