"""admin routes — Stripe payouts/disputes, margin, GST/HST report, accounting exports."""

from porterchain_api.db import get_report_db
from datetime import UTC, datetime, timedelta

from fastapi import Header, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field

from porterchain_api.auth.staff_step_up import enforce_staff_step_up
from porterchain_api.routers.admin._deps import (
    AdminContext,
    Annotated,
    Depends,
    HTTPException,
    Query,
    Session,
    Settings,
    get_admin_context,
    get_db,
    get_settings,
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


@router.get("/finance/tax-registration")
def tax_registration(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> dict:
    """Our GST/HST number (single source for all documents) or a warning when unset."""
    require_module(ctx, "finance_read")
    from porterchain_api.platform.tax_registration import registration_status

    return registration_status(db)


class TaxRegistrationChange(BaseModel):
    #: Empty/null = we stop being a registrant from ``effective_from``.
    gst_hst_number: str | None = Field(default=None, max_length=32)
    legal_name: str | None = Field(default=None, max_length=255)
    effective_from: str = Field(min_length=10, max_length=10)
    note: str | None = Field(default=None, max_length=500)


@router.post("/finance/tax-registration")
def change_tax_registration(
    body: TaxRegistrationChange,
    request: Request,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    authorization: Annotated[str | None, Header()] = None,
) -> dict:
    """Register / change / end GST/HST from a date (append-only; step-up; audited)."""
    require_module(ctx, "finance")
    enforce_staff_step_up(request, authorization, settings)
    from porterchain_api.admin_engine.tax_registration_admin import change_registration

    try:
        return change_registration(db, ctx, **body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None


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


@router.get("/settings/future")
def future_features(
    ctx: Annotated[AdminContext, Depends(get_admin_context)], db: Session = Depends(get_db)
) -> dict:
    """Settings → Future: scoped toggles with parcels/day thresholds and current volume."""
    require_module(ctx, "settings")
    from porterchain_api.platform.future_features import future_overview

    return future_overview(db)


@router.get("/privacy/access-export")
def privacy_access_export(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_report_db),
    email: str | None = None,
    phone: str | None = None,
) -> dict:
    """PIPEDA access request: all personal data held for one email/phone (read-only)."""
    require_module(ctx, "settings")
    from porterchain_api.platform.privacy_access import subject_access_export

    try:
        return subject_access_export(db, email=email, phone=phone)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/finance/tax-report")
def finance_tax_report(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_report_db),
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
    db: Session = Depends(get_report_db),
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
