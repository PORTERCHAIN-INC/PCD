"""Doc 79 Insights: finance + operations metrics (finance/owner roles; staff only)."""
from __future__ import annotations

from dataclasses import replace
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from porterchain_api.admin_engine.rbac import AdminContext, AdminRole
from porterchain_api.auth.admin import get_admin_context
from porterchain_api.metrics_engine import formulas as f
from porterchain_api.metrics_engine.baseline import baseline

router = APIRouter(prefix="/v1/admin/metrics", tags=["admin-metrics"])
_ALLOWED = (AdminRole.SUPER_ADMIN, AdminRole.ADMIN, AdminRole.FINANCE)


def _guard(ctx: AdminContext) -> None:
    if ctx.role not in _ALLOWED:
        raise HTTPException(status_code=403, detail="finance_role_required")


@router.get("/baseline")
def get_baseline(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    stops_per_day: float = Query(20, gt=0, le=1000),
    wacc: float | None = Query(None, gt=0, lt=1),
    price_per_stop: float | None = Query(None, gt=0),
    stops: int | None = Query(None, gt=0),
    hours: float | None = Query(None, gt=0),
    km: float | None = Query(None, ge=0),
):
    _guard(ctx)
    p = f.DEFAULT_PARAMS if wacc is None else replace(f.DEFAULT_PARAMS, wacc=wacc)
    route = {k: v for k, v in {"price_per_stop": price_per_stop, "stops": stops, "hours": hours, "km": km}.items() if v is not None}
    out = baseline(p, route, stops_per_day)
    out["kingman"] = {str(rho): round(f.kingman_wq(1, 0.5, rho, 10), 1) for rho in (0.70, 0.85, 0.90, 0.95)}
    out["utilisation_thresholds"] = {"yellow": p.utilisation_yellow, "red": p.utilisation_red}
    out["compliance_money"] = {
        "gap_cost_per_rental_truck_day": round(f.compliance_gap_cost(0.02, 0.30, 310, 96.75), 2),
        "oos_loss_no_substitute": round(f.oos_margin_loss(12, 96.75 / 12), 2),
        "oos_loss_with_substitute": round(f.oos_margin_loss(12, 96.75 / 12, 12, 3.0), 2),
        "assumptions": "U80-2: Pa 0.02, Pv 0.30, Cf $310, Cl $96.75",
    }
    return out
