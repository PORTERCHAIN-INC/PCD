"""merchant routes — reports."""

from porterchain_api.routers.merchant._deps import (
    Annotated,
    Depends,
    HTTPException,
    MerchantContext,
    MerchantReportSaveRequest,
    MerchantReportScheduleRequest,
    ReportSummaryResponse,
    Response,
    Session,
    _reports,
    get_db,
    get_merchant_context,
    require_module,
    router,
)


@router.get("/reports/summary", response_model=ReportSummaryResponse)
def reports_summary(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> ReportSummaryResponse:
    require_module(ctx, "reports")
    return ReportSummaryResponse(**_reports.summary(db, ctx))


@router.get("/reports/overview")
def reports_overview(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "reports")
    return _reports.overview(db, ctx)


@router.get("/reports/executive")
def reports_executive(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "reports")
    return _reports.executive(db, ctx)


@router.get("/reports/delivery-performance")
def reports_delivery_performance(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "reports")
    return _reports.delivery_performance(db, ctx)


@router.get("/reports/order-volume")
def reports_order_volume(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "reports")
    return _reports.order_volume(db, ctx)


@router.get("/reports/invoices")
def reports_invoices(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "reports")
    return _reports.invoice_reports(db, ctx)


@router.get("/reports/drivers")
def reports_drivers(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "reports")
    return _reports.driver_reports(db, ctx)


@router.get("/reports/vehicles")
def reports_vehicles(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "reports")
    return _reports.vehicle_reports(db, ctx)


@router.get("/reports/destinations")
def reports_destinations(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "reports")
    return _reports.destination_reports(db, ctx)


@router.get("/reports/claims")
def reports_claims(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "reports")
    return _reports.claims_reports(db, ctx)


@router.get("/reports/sla-history")
def reports_sla_history(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
):
    """§8.3.2 — 12-month SLA history for merchant portal."""
    require_module(ctx, "reports")
    return _reports.sla_history(db, ctx)


@router.get("/reports/switching-costs")
def reports_switching_costs(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
):
    """§8.3 — integration depth, SLA history, tariffs, RBAC audit snapshot."""
    require_module(ctx, "reports")
    return _reports.switching_costs(db, ctx)


@router.get("/reports/saved")
def reports_saved_list(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
):
    require_module(ctx, "reports")
    return _reports.list_saved_reports(ctx)


@router.post("/reports/saved")
def reports_saved_create(
    body: MerchantReportSaveRequest,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "reports")
    return _reports.save_report(
        db,
        ctx,
        name=body.name,
        report_type=body.report_type,
        chart_type=body.chart_type,
        filters=body.filters,
    )


@router.delete("/reports/saved/{report_id}")
def reports_saved_delete(
    report_id: str,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "reports")
    _reports.delete_saved_report(db, ctx, report_id)
    return {"ok": True}


@router.get("/reports/scheduled")
def reports_scheduled_list(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
):
    require_module(ctx, "reports")
    return _reports.list_scheduled_reports(ctx)


@router.post("/reports/scheduled")
def reports_scheduled_create(
    body: MerchantReportScheduleRequest,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "reports")
    return _reports.save_scheduled_report(
        db,
        ctx,
        name=body.name,
        report_type=body.report_type,
        schedule=body.schedule,
        email=body.email,
    )


@router.get("/reports/export/{report_type}.csv")
def reports_export_csv(
    report_type: str,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "reports")
    content = _reports.export_csv(db, ctx, report_type)
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=merchant-{report_type}-report.csv"},
    )


@router.get("/reports/export/{report_type}.xlsx")
def reports_export_excel(
    report_type: str,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "reports")
    try:
        content = _reports.export_excel(db, ctx, report_type)
    except ValueError as exc:
        if str(exc) == "excel_support_unavailable":
            raise HTTPException(
                status_code=503, detail="Excel export is not available on this server."
            ) from exc
        raise
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=merchant-{report_type}-report.xlsx"},
    )


