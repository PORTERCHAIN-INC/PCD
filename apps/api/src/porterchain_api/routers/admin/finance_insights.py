"""admin routes — Stripe payouts/disputes, margin, GST/HST report, accounting exports."""

from datetime import UTC, datetime, timedelta

from fastapi.responses import Response

from porterchain_api.routers.admin._deps import (
    AdminContext,
    Annotated,
    Depends,
    HTTPException,
    Query,
    Session,
    get_admin_context,
    get_db,
    require_module,
    router,
)


def _period(start: str | None, end: str | None) -> tuple[datetime, datetime]:
    try:
        e = datetime.fromisoformat(end).replace(tzinfo=UTC) if end else datetime.now(UTC)
        s = datetime.fromisoformat(start).replace(tzinfo=UTC) if start else e - timedelta(days=90)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="date_invalid") from exc
    if end:
        e = e + timedelta(days=1)  # inclusive end date
    if e <= s:
        raise HTTPException(status_code=400, detail="period_invalid")
    return s, e


@router.get("/finance/stripe")
def finance_stripe(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> dict:
    """Bank payouts reconciled against charges, fees, refunds and disputes."""
    require_module(ctx, "finance_read")
    from porterchain_api.platform.stripe_money import stripe_overview

    return stripe_overview(db)


@router.get("/finance/margin")
def finance_margin(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    days: int = Query(30, ge=1, le=366),
    merchant_id: str | None = None,
) -> dict:
    require_module(ctx, "finance_read")
    from porterchain_api.reporting.margin import margin_report

    return margin_report(db, days=days, merchant_id=merchant_id)


@router.get("/analytics/ops")
def ops_analytics(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    days: int = Query(30, ge=1, le=366),
) -> dict:
    """Cost/stop, margins by merchant/FSA/vehicle/route, on-time, fill, failed, trend, FSA forecast."""
    require_module(ctx, "finance_read")
    from porterchain_api.reporting.analytics import ops_analytics as _ops

    return _ops(db, days=days)


@router.get("/finance/tax-report")
def finance_tax_report(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    start: str | None = None,
    end: str | None = None,
) -> dict:
    require_module(ctx, "finance_read")
    from porterchain_api.reporting.tax_report import hst_report

    s, e = _period(start, end)
    return hst_report(db, s, e)


@router.get("/finance/exports/{kind}.csv")
def finance_export_csv(
    kind: str,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    start: str | None = None,
    end: str | None = None,
) -> Response:
    """kind: hst | quickbooks | xero."""
    require_module(ctx, "finance_read")
    from porterchain_api.reporting.tax_report import accounting_csv, hst_report, hst_report_csv

    s, e = _period(start, end)
    if kind == "hst":
        body = hst_report_csv(hst_report(db, s, e))
    elif kind in ("quickbooks", "xero"):
        body = accounting_csv(db, s, e, fmt=kind)
    else:
        raise HTTPException(status_code=404, detail="unknown_export")
    name = f"porterchain-{kind}-{s.date()}-{(e - timedelta(days=1)).date()}.csv"
    return Response(
        content=body,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{name}"', "Cache-Control": "no-store"},
    )
