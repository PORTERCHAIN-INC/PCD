"""merchant routes — billing."""

from porterchain_api.db import get_report_db
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
    from porterchain_api.billing_engine.merchant_invoice_checkout import card_payments_available

    from porterchain_api.admin_engine.platform_settings import etransfer_recipient_email

    card = card_payments_available(get_settings())  # always False for merchants now
    from porterchain_api.booking_models import Invoice

    rest = {k: v for k, v in data.items() if k not in ("lines_total_cents", "etransfer_email", "payment_reference")}
    inv = db.get(Invoice, invoice_id)
    return InvoiceDetailResponse(
        card_payment_available=card,
        etransfer_email=etransfer_recipient_email(db),
        payment_reference=getattr(inv, "payment_reference", None),
        **rest,
    )


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


@router.post("/billing/invoices/{invoice_id}/pay-card")
def pay_invoice_by_card(
    invoice_id: str,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    """G11 exception (flag merchant_card_payments_enabled): hosted card checkout for the invoice's
    outstanding balance; the portal redirects to ``url``."""
    require_module(ctx, "invoices")
    from porterchain_api.billing_engine.merchant_invoice_checkout import create_invoice_checkout

    try:
        return create_invoice_checkout(db, settings, ctx.merchant, invoice_id, getattr(ctx.user, "email", None))
    except LookupError:
        raise HTTPException(status_code=404, detail="invoice_not_found") from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None


@router.post("/billing/invoices/{invoice_id}/pay-card/sync")
def sync_invoice_card_payment(
    invoice_id: str,
    body: dict,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    """Return page: confirm the hosted checkout and record the payment (webhook-safe, idempotent)."""
    require_module(ctx, "invoices")
    from porterchain_api.billing_engine.merchant_invoice_checkout import sync_invoice_checkout

    session_id = str((body or {}).get("session_id") or "").strip()
    if not session_id.startswith("cs_"):
        raise HTTPException(status_code=400, detail="invalid_session_id")
    try:
        return sync_invoice_checkout(db, settings, ctx.merchant, invoice_id, session_id)
    except LookupError:
        raise HTTPException(status_code=404, detail="invoice_not_found") from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None


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


@router.get("/billing/credit-notes/{credit_note_id}/pdf")
def download_credit_note_pdf(
    credit_note_id: str,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "billing")
    try:
        pdf, filename = _billing.credit_note_pdf(db, ctx, credit_note_id)
    except LookupError:
        raise HTTPException(status_code=404, detail="credit_note_not_found") from None
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


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
    db: Session = Depends(get_report_db),
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
    db: Session = Depends(get_report_db),
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
    db: Session = Depends(get_report_db),
) -> Response:
    require_module(ctx, "billing")
    content = _billing.export_history_csv(db, ctx)
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=merchant-billing-history.csv"},
    )
