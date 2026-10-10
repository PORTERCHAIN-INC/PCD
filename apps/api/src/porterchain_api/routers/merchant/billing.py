"""merchant routes — billing."""

from porterchain_api.routers.merchant._deps import (
    Annotated,
    BillingStatementResponse,
    Depends,
    HTTPException,
    InvoiceDetailResponse,
    InvoiceListItem,
    MerchantBillingHistoryItem,
    MerchantBillingOverviewResponse,
    MerchantContext,
    MerchantContractPricingResponse,
    MerchantCreditNoteItem,
    MerchantPaymentItem,
    MerchantRateCardResponse,
    MerchantStatementDetailResponse,
    MerchantTaxSummaryResponse,
    Response,
    Session,
    Settings,
    _billing,
    get_db,
    get_merchant_context,
    get_settings,
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


@router.get("/billing/invoices/{invoice_id}", response_model=InvoiceDetailResponse)
def get_invoice_detail(
    invoice_id: str,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> InvoiceDetailResponse:
    require_module(ctx, "invoices")
    from porterchain_api.merchant_engine.billing_pack import billing_error_message

    try:
        data = _billing.invoice_detail(db, ctx, invoice_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=billing_error_message(str(exc))) from None
    return InvoiceDetailResponse(**{k: v for k, v in data.items() if k != "lines_total_cents"})


@router.get("/billing/invoices/{invoice_id}/pdf")
def download_invoice_pdf(
    invoice_id: str,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
):
    from porterchain_api.merchant_engine.billing_pack import billing_error_message

    require_module(ctx, "invoices")
    try:
        pdf, filename = _billing.invoice_pdf(db, ctx, invoice_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=billing_error_message(str(exc))) from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=billing_error_message(str(exc))) from None
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/billing/invoices/{invoice_id}/remind")
def remind_invoice(
    invoice_id: str,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> dict:
    require_module(ctx, "invoices")
    from porterchain_api.merchant_engine.billing_pack import billing_error_message

    try:
        return _billing.remind_invoice(db, ctx, invoice_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=billing_error_message(str(exc))) from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=billing_error_message(str(exc))) from None


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


@router.get("/pricing/rate-card", response_model=MerchantRateCardResponse)
def merchant_rate_card(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> MerchantRateCardResponse:
    require_module(ctx, "billing")
    from porterchain_api.merchant_engine.rate_card_view import merchant_rate_card as build_card

    return MerchantRateCardResponse(**build_card(db, ctx.merchant))


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


@router.get("/billing/cod")
def billing_cod_status(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
) -> dict:
    """COD / Stripe Connect status for the merchant."""
    require_module(ctx, "billing")
    m = ctx.merchant
    return {
        "cod_enabled": bool(getattr(m, "cod_enabled", False)),
        "stripe_connect_account_id": getattr(m, "stripe_connect_account_id", None),
        "connect_ready": bool(getattr(m, "stripe_connect_account_id", None)),
    }


@router.post("/billing/cod/connect")
def billing_cod_connect(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    """Start Stripe Connect Express onboarding (or return mock link)."""
    require_module(ctx, "billing")
    from porterchain_api.billing_engine.stripe_cod_service import StripeCodService

    return StripeCodService().create_connect_account_link(db, settings, ctx.merchant)


@router.post("/billing/cod/enable")
def billing_cod_enable(
    body: dict,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> dict:
    require_module(ctx, "billing")
    from porterchain_api.billing_engine.stripe_cod_service import StripeCodService

    enabled = bool(body.get("enabled"))
    try:
        merchant = StripeCodService().set_cod_enabled(db, ctx.merchant, enabled=enabled)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "cod_enabled": merchant.cod_enabled,
        "stripe_connect_account_id": merchant.stripe_connect_account_id,
    }


