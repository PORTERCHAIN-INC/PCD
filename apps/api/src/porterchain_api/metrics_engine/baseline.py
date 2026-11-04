"""Doc 79 §4 baseline economics on the invested capital, computed from FinanceParams."""
from __future__ import annotations

from dataclasses import asdict
from typing import Any

from porterchain_api.metrics_engine import formulas as f

GTA_ROUTE = {"price_per_stop": 16.20, "stops": 12, "hours": 3.0, "km": 45.0}


def baseline(p: f.FinanceParams = f.DEFAULT_PARAMS, route: dict[str, Any] | None = None,
             stops_per_day: float = 20) -> dict[str, Any]:
    r = {**GTA_ROUTE, **(route or {})}
    econ = f.route_economics(r["price_per_stop"] * r["stops"], r["hours"], r["km"], r["stops"], p)
    cps = econ["per_stop"]  # unrounded ($8.0625); shown as $8.06
    be = f.break_even_stops(cps, p)
    days_y = p.working_days_per_month * 12
    revenue_y = stops_per_day * days_y * r["price_per_stop"]
    direct_y = stops_per_day * days_y * (econ["direct_cost"] / r["stops"])
    ebitda_y = revenue_y - direct_y - p.cash_fixed_per_month * 12
    ebit_y = ebitda_y - f.annual_da(p)
    nop = f.nopat(ebit_y, p.tax_rate)
    return {
        "params": asdict(p),
        "route": {**econ, "contribution_per_stop": round(cps, 2)},
        "annual_da": round(f.annual_da(p), 2),
        "break_even_stops_per_day": {k: round(v, 1) for k, v in be.items() if k != "eva_ebit_per_year"},
        "year": {
            "stops_per_day": stops_per_day, "revenue": round(revenue_y, 2), "ebitda": round(ebitda_y, 2),
            "ebitda_margin": ebitda_y / revenue_y if revenue_y else 0.0, "ebit": round(ebit_y, 2),
            "nopat": round(nop, 2), "roic": f.roic(nop, p.invested_capital),
            "eva": round(f.eva(nop, p.invested_capital, p.wacc), 2),
            "ev_illustrative": round(f.enterprise_value(ebitda_y, p.ev_multiple), 2),
        },
        "payback_months": {str(n): round(f.payback_months(n, cps, p), 1) for n in (12, 20, 40)},
    }
