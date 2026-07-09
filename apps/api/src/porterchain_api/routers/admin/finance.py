"""admin routes — finance."""

from porterchain_api.routers.admin._deps import (
    AdminContext,
    Annotated,
    Depends,
    FinanceCreditNoteRequest,
    FinanceDashboardResponse,
    FinanceFilters,
    FinanceInvoiceDetailResponse,
    FinanceInvoiceItem,
    FinanceLedgerItem,
    FinancePaymentItem,
    FinancePayoutItem,
    HTTPException,
    Session,
    _finance,
    get_admin_context,
    get_db,
    require_module,
    router,
)


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


@router.get("/finance/collections", response_model=list[FinanceInvoiceItem])
def finance_collections(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> list[FinanceInvoiceItem]:
    require_module(ctx, "finance_read")
    return [FinanceInvoiceItem(**row) for row in _finance.collections(db)]


@router.get("/finance/export")
def finance_export_gl(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> list[dict]:
    require_module(ctx, "finance_read")
    return _finance.export_gl(db)


@router.get("/finance/invoices", response_model=list[FinanceInvoiceItem])
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
) -> list[FinanceInvoiceItem]:
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
    )
    return [FinanceInvoiceItem(**row) for row in _finance.list_invoices_enriched(db, filters)]


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


@router.get("/finance/payments", response_model=list[FinancePaymentItem])
def finance_list_payments(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    status: str | None = None,
    payment_method: str | None = None,
    search: str | None = None,
) -> list[FinancePaymentItem]:
    require_module(ctx, "finance_read")
    filters = FinanceFilters(status=status, payment_method=payment_method, search=search)
    return [FinancePaymentItem(**row) for row in _finance.list_payments_enriched(db, filters)]


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
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> dict:
    require_module(ctx, "finance")
    entry = _finance.record_credit_note(
        db, ctx, order_id=body.order_id, amount_cents=body.amount_cents, reason=body.reason
    )
    return {"ledger_id": entry.id, "status": entry.status}


@router.get("/finance/summary")
def finance_summary(ctx: Annotated[AdminContext, Depends(get_admin_context)], db: Session = Depends(get_db)):
    require_module(ctx, "finance_read")
    return _finance.revenue_summary(db)


