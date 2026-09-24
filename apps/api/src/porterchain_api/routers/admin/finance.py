"""admin routes — finance."""

from fastapi import Header, Request

from porterchain_api.auth.staff_step_up import enforce_staff_step_up
from porterchain_api.billing_engine.stripe_cod_service import StripeCodService
from porterchain_api.routers.admin._deps import (
    AdminContext,
    Annotated,
    Depends,
    FinanceCollectionItem,
    FinanceCreditNoteRequest,
    FinanceDashboardResponse,
    FinanceFilters,
    FinanceInvoiceDetailResponse,
    FinanceInvoiceItem,
    FinanceInvoicePage,
    FinanceLedgerItem,
    FinancePaymentItem,
    FinancePaymentPage,
    FinancePayoutItem,
    HTTPException,
    MerchantArGenerateRequest,
    MerchantArRecordPaymentRequest,
    Session,
    Settings,
    _finance,
    get_admin_context,
    get_db,
    get_settings,
    Query,
    require_module,
    router,
)


def _step_up(
    request: Request,
    authorization: str | None,
    settings: Settings,
) -> None:
    enforce_staff_step_up(request, authorization, settings)


@router.get("/finance/dashboard", response_model=FinanceDashboardResponse)
def finance_dashboard(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> FinanceDashboardResponse:
    require_module(ctx, "finance_read")
    return FinanceDashboardResponse(**_finance.dashboard(db))


@router.get("/finance/reports")
def finance_reports(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> dict:
    require_module(ctx, "finance_read")
    return _finance.reports(db)


@router.get("/finance/collections", response_model=list[FinanceCollectionItem])
def finance_collections(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> list[FinanceCollectionItem]:
    """Open invoices in chase order, with due date, aging, and who to call (BL)."""
    require_module(ctx, "finance_read")
    return [FinanceCollectionItem(**row) for row in _finance.collections(db)]


@router.get("/finance/export")
def finance_export_gl(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> list[dict]:
    require_module(ctx, "finance_read")
    return _finance.export_gl(db)


@router.get("/finance/invoices", response_model=FinanceInvoicePage)
def finance_list_invoices(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    status: str | None = None,
    merchant_id: str | None = None,
    currency: str | None = None,
    search: str | None = None,
    outstanding_only: bool = False,
    date_from: str | None = None,
    date_to: str | None = None,
    amount_min_cents: int | None = None,
    amount_max_cents: int | None = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> FinanceInvoicePage:
    require_module(ctx, "finance_read")
    from datetime import datetime

    filters = FinanceFilters(
        status=status,
        merchant_id=merchant_id,
        currency=currency,
        search=search,
        outstanding_only=outstanding_only,
        date_from=datetime.fromisoformat(date_from) if date_from else None,
        date_to=datetime.fromisoformat(date_to) if date_to else None,
        amount_min_cents=amount_min_cents,
        amount_max_cents=amount_max_cents,
        limit=limit,
        offset=offset,
    )
    page = _finance.list_invoices_page(db, filters)
    return FinanceInvoicePage(
        items=[FinanceInvoiceItem(**row) for row in page["items"]],
        total=page["total"],
        limit=page["limit"],
        offset=page["offset"],
    )


@router.get("/finance/invoices/{invoice_id}", response_model=FinanceInvoiceDetailResponse)
def finance_invoice_detail(
    invoice_id: str,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> FinanceInvoiceDetailResponse:
    require_module(ctx, "finance_read")
    detail = _finance.get_invoice_detail(db, invoice_id)
    if not detail:
        raise HTTPException(status_code=404, detail="invoice_not_found")
    return FinanceInvoiceDetailResponse(**detail)


@router.get("/finance/payments", response_model=FinancePaymentPage)
def finance_list_payments(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    status: str | None = None,
    payment_method: str | None = None,
    search: str | None = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> FinancePaymentPage:
    require_module(ctx, "finance_read")
    filters = FinanceFilters(
        status=status,
        payment_method=payment_method,
        search=search,
        limit=limit,
        offset=offset,
    )
    page = _finance.list_payments_page(db, filters)
    return FinancePaymentPage(
        items=[FinancePaymentItem(**row) for row in page["items"]],
        total=page["total"],
        limit=page["limit"],
        offset=page["offset"],
    )


@router.get("/finance/payouts", response_model=list[FinancePayoutItem])
def finance_list_payouts(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    status: str | None = None,
) -> list[FinancePayoutItem]:
    require_module(ctx, "finance_read")
    return [FinancePayoutItem(**row) for row in _finance.list_payouts_enriched(db, status=status)]


@router.get("/finance/ledger", response_model=list[FinanceLedgerItem])
def finance_ledger(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> list[FinanceLedgerItem]:
    require_module(ctx, "finance_read")
    return [FinanceLedgerItem(**row) for row in _finance.list_ledger(db)]


@router.get("/finance/duplicates")
def finance_duplicates(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> dict:
    require_module(ctx, "finance_read")
    return {"payments": _finance.find_duplicate_payments(db)}


@router.post("/finance/credit-notes")
def finance_credit_note(
    body: FinanceCreditNoteRequest,
    request: Request,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    authorization: Annotated[str | None, Header()] = None,
) -> dict:
    require_module(ctx, "finance")
    _step_up(request, authorization, settings)
    entry = _finance.record_credit_note(
        db, ctx, order_id=body.order_id, amount_cents=body.amount_cents, reason=body.reason
    )
    return {"ledger_id": entry.id, "status": entry.status}


@router.get("/finance/merchant-ar/preview")
def finance_merchant_ar_preview(
    merchant_id: str,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    period_start: str | None = None,
    period_end: str | None = None,
) -> dict:
    require_module(ctx, "finance_read")
    from datetime import datetime

    from porterchain_api.admin_engine.merchant_ar_service import MerchantArService

    svc = MerchantArService()
    try:
        return svc.preview(
            db,
            merchant_id=merchant_id,
            period_start=datetime.fromisoformat(period_start) if period_start else None,
            period_end=datetime.fromisoformat(period_end) if period_end else None,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/finance/merchant-ar/generate")
def finance_merchant_ar_generate(
    body: MerchantArGenerateRequest,
    request: Request,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    authorization: Annotated[str | None, Header()] = None,
) -> dict:
    require_module(ctx, "finance")
    _step_up(request, authorization, settings)
    from porterchain_api.admin_engine.merchant_ar_service import MerchantArService

    svc = MerchantArService()
    try:
        return svc.generate(
            db,
            ctx,
            merchant_id=body.merchant_id,
            period_start=body.period_start,
            period_end=body.period_end,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/finance/invoices/{invoice_id}/record-payment")
def finance_record_invoice_payment(
    invoice_id: str,
    body: MerchantArRecordPaymentRequest,
    request: Request,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    authorization: Annotated[str | None, Header()] = None,
) -> dict:
    require_module(ctx, "finance")
    _step_up(request, authorization, settings)
    from porterchain_api.admin_engine.merchant_ar_service import MerchantArService

    svc = MerchantArService()
    try:
        return svc.record_payment(
            db,
            ctx,
            invoice_id,
            method=body.method,
            amount_cents=body.amount_cents,
            reference=body.reference,
            paid_at=body.paid_at,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/finance/invoices/{invoice_id}/remind")
def finance_remind_invoice(
    invoice_id: str,
    request: Request,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    authorization: Annotated[str | None, Header()] = None,
) -> dict:
    require_module(ctx, "finance")
    _step_up(request, authorization, settings)
    try:
        return _finance.remind_invoice(db, ctx, invoice_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/finance/invoices/{invoice_id}/refund")
def finance_refund_invoice(
    invoice_id: str,
    request: Request,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    authorization: Annotated[str | None, Header()] = None,
    amount_cents: int | None = None,
) -> dict:
    require_module(ctx, "finance")
    _step_up(request, authorization, settings)
    try:
        return _finance.refund_invoice(db, ctx, settings, invoice_id, amount_cents=amount_cents)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/finance/summary")
def finance_summary(ctx: Annotated[AdminContext, Depends(get_admin_context)], db: Session = Depends(get_db)):
    require_module(ctx, "finance_read")
    return _finance.revenue_summary(db)


@router.get("/finance/cod")
def finance_cod_queue(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    status: str | None = Query(default=None),
):
    """COD collection queue — orders with cod_amount_cents set."""
    require_module(ctx, "finance_read")
    return StripeCodService().list_collection_queue(db, status=status)


