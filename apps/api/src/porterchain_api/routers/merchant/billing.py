"""merchant routes — billing."""

from porterchain_api.routers.merchant._deps import (
    Annotated,
    BillingStatementResponse,
    Depends,
    HTTPException,
    InvoiceListItem,
    MerchantBillingHistoryItem,
    MerchantBillingOverviewResponse,
    MerchantContext,
    MerchantContractPricingResponse,
    MerchantCreditNoteItem,
    MerchantPaymentItem,
    MerchantStatementDetailResponse,
    MerchantTaxSummaryResponse,
    RedirectResponse,
    Response,
    Session,
    _billing,
    get_db,
    get_merchant_context,
    require_module,
    router,
)


@router.get("/billing/overview", response_model=MerchantBillingOverviewResponse)
def billing_overview(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> MerchantBillingOverviewResponse:
    require_module(ctx, "billing")
    data = _billing.overview(db, ctx)
    return MerchantBillingOverviewResponse(
        **{k: v for k, v in data.items() if k not in ("tax_summary", "contract_pricing")},
        tax_summary=MerchantTaxSummaryResponse(**data["tax_summary"]),
        contract_pricing=MerchantContractPricingResponse(**data["contract_pricing"]),
    )


@router.get("/billing/statement", response_model=BillingStatementResponse)
def billing_statement(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> BillingStatementResponse:
    require_module(ctx, "billing")
    return BillingStatementResponse(**_billing.statement_summary(db, ctx))


@router.get("/billing/statement/detail", response_model=MerchantStatementDetailResponse)
def billing_statement_detail(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> MerchantStatementDetailResponse:
    require_module(ctx, "statements")
    return MerchantStatementDetailResponse(**_billing.statement_detail(db, ctx))


@router.get("/billing/invoices", response_model=list[InvoiceListItem])
def list_invoices(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> list[InvoiceListItem]:
    require_module(ctx, "invoices")
    rows = _billing.list_invoices_enriched(db, ctx)
    return [InvoiceListItem(**r) for r in rows]


@router.get("/billing/invoices/{invoice_id}/pdf")
def download_invoice_pdf(
    invoice_id: str,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "invoices")
    try:
        url = _billing.get_invoice_pdf_url(db, ctx, invoice_id)
    except LookupError:
        raise HTTPException(status_code=404, detail="invoice_not_found") from None
    if not url:
        raise HTTPException(status_code=404, detail="pdf_not_available")
    return RedirectResponse(url=url)


@router.get("/billing/payments", response_model=list[MerchantPaymentItem])
def list_billing_payments(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> list[MerchantPaymentItem]:
    require_module(ctx, "billing")
    return [MerchantPaymentItem(**r) for r in _billing.list_payments(db, ctx)]


@router.get("/billing/credit-notes", response_model=list[MerchantCreditNoteItem])
def list_credit_notes(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> list[MerchantCreditNoteItem]:
    require_module(ctx, "billing")
    return [MerchantCreditNoteItem(**r) for r in _billing.list_credit_notes(db, ctx)]


@router.get("/billing/history", response_model=list[MerchantBillingHistoryItem])
def billing_history(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> list[MerchantBillingHistoryItem]:
    require_module(ctx, "billing")
    return [MerchantBillingHistoryItem(**r) for r in _billing.billing_history(db, ctx)]


@router.get("/billing/tax-summary", response_model=MerchantTaxSummaryResponse)
def billing_tax_summary(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> MerchantTaxSummaryResponse:
    require_module(ctx, "billing")
    return MerchantTaxSummaryResponse(**_billing.tax_summary(db, ctx))


@router.get("/billing/contract", response_model=MerchantContractPricingResponse)
def billing_contract(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> MerchantContractPricingResponse:
    require_module(ctx, "billing")
    return MerchantContractPricingResponse(**_billing.contract_pricing(db, ctx))


@router.get("/billing/export/invoices.csv")
def export_invoices_csv(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> Response:
    require_module(ctx, "invoices")
    content = _billing.export_invoices_csv(db, ctx)
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=merchant-invoices.csv"},
    )


@router.get("/billing/export/statement.csv")
def export_statement_csv(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> Response:
    require_module(ctx, "statements")
    content = _billing.export_statement_csv(db, ctx)
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=merchant-statement.csv"},
    )


@router.get("/billing/export/history.csv")
def export_history_csv(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> Response:
    require_module(ctx, "billing")
    content = _billing.export_history_csv(db, ctx)
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=merchant-billing-history.csv"},
    )


