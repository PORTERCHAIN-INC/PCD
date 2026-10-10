"""merchant routes — account statement PDF (balance, PC codes, e-Transfer, open invoices)."""

from porterchain_api.routers.merchant._deps import (
    Annotated,
    Depends,
    MerchantContext,
    Response,
    Session,
    get_db,
    get_merchant_context,
    require_module,
    router,
)


@router.get("/billing/statement.pdf")
def billing_statement_pdf(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> Response:
    require_module(ctx, "billing")
    from porterchain_api.admin_engine.platform_settings import supplier_gst_hst_number
    from porterchain_api.reporting.statement import statement_data, statement_pdf

    data = statement_data(db, ctx.merchant)
    pdf = statement_pdf(data, tax_number=supplier_gst_hst_number(db))
    name = f"porterchain-statement-{data['generated']}.pdf"
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{name}"', "Cache-Control": "no-store"},
    )
