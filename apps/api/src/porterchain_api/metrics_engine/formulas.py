"""Doc 79 §2: the business formulas, plain Python (no AI, no paid services).

Money is integer cents or Decimal dollars; ratios are floats. HST is never revenue or cost.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Iterable

# --- Finance parameters (doc 79 §0; Settings → Finance parameters, versioned) -----------------
@dataclass(frozen=True)
class FinanceParams:
    version: int = 1
    wacc: float = 0.18
    tax_rate: float = 0.122
    driver_cost_per_h: float = 30.0
    vehicle_cost_per_km: float = 0.17
    cash_fixed_per_month: float = 430.0
    working_days_per_month: int = 22
    invested_capital: float = 77_000.0
    software_cost: float = 50_000.0
    software_life_years: int = 3
    civic_cost: float = 22_000.0
    civic_residual: float = 7_000.0
    civic_life_years: int = 5
    ev_multiple: float = 4.0
    utilisation_yellow: float = 0.85
    utilisation_red: float = 0.90
    free_dwell_min: int = 30
    driver_cost_per_min: float = 0.50


DEFAULT_PARAMS = FinanceParams()

# --- Chart of accounts (doc 79 §1) -------------------------------------------------------------
ACCOUNTS = {
    "4100": "Delivery fees", "4200": "Add-ons", "4300": "B2B contract revenue", "4400": "Broker margin", "4500": "Storage",
    "5100": "Driver pay", "5200": "Fuel and tolls", "5300": "Vehicle rental", "5400": "Carrier / partner payouts",
    "5500": "Packaging and labels", "5600": "Payment fees", "5700": "Cargo claims (net of recoveries)",
    "6100": "Hosting", "6200": "Software", "6300": "Insurance", "6400": "Marketing", "6500": "Admin, accounting, phone",
    "7100": "Depreciation", "7200": "Amortisation", "8100": "Interest", "8200": "Income tax",
}
HST_ACCOUNTS = {"2200"}  # HST payable is a liability, never P&L


@dataclass
class Pnl:
    revenue: int
    direct: int
    gross_profit: int
    opex: int
    depreciation: int
    amortisation: int
    ebit: int
    interest: int
    taxes: int
    net_income: int
    ebitda_top_down: int
    ebitda_bottom_up: int
    by_account: dict[str, int] = field(default_factory=dict)

    @property
    def ebitda_margin(self) -> float:
        return self.ebitda_top_down / self.revenue if self.revenue else 0.0


def pnl(lines: Iterable[tuple[str, int]]) -> Pnl:
    """lines: (account_code, cents) net of HST; credit notes are negative 4xxx lines."""
    acc: dict[str, int] = {}
    for code, cents in lines:
        if code in HST_ACCOUNTS:
            continue  # A-FIN-02: HST never enters revenue or cost
        if code not in ACCOUNTS:
            raise ValueError(f"unknown_account:{code}")
        acc[code] = acc.get(code, 0) + int(cents)
    s = lambda p: sum(v for k, v in acc.items() if k.startswith(p))  # noqa: E731
    revenue, direct, opex = s("4"), s("5"), s("6")
    dep, amort = acc.get("7100", 0), acc.get("7200", 0)
    interest, taxes = acc.get("8100", 0), acc.get("8200", 0)
    gp = revenue - direct
    ebit = gp - opex - dep - amort
    net = ebit - interest - taxes
    return Pnl(revenue, direct, gp, opex, dep, amort, ebit, interest, taxes, net,
               ebitda_top_down=ebit + dep + amort, ebitda_bottom_up=net + interest + taxes + dep + amort, by_account=acc)


# --- Returns ------------------------------------------------------------------------------------
def roi(gain: float, cost: float) -> float:
    return (gain - cost) / cost


def simple_annual_return(annual_gain: float, cost: float) -> float:
    return annual_gain / cost


def payback_years(cost: float, annual_gain: float) -> float:
    return cost / annual_gain if annual_gain > 0 else math.inf


def roa_dupont(revenue: float, total_assets: float, ebit: float) -> float:
    return (revenue / total_assets) * (ebit / revenue)


def nopat(ebit: float, tax_rate: float) -> float:
    return ebit * (1 - tax_rate)


def roic(nopat_v: float, invested_capital: float) -> float:
    return nopat_v / invested_capital


def capm(rf: float, beta: float, rm: float) -> float:
    return rf + beta * (rm - rf)


def wacc(e: float, d: float, re: float, rd: float, tc: float) -> float:
    v = e + d
    return e / v * re + d / v * rd * (1 - tc)


def eva(nopat_v: float, invested_capital: float, wacc_v: float) -> float:
    return nopat_v - invested_capital * wacc_v


def enterprise_value(adj_ebitda: float, multiple: float) -> float:
    return adj_ebitda * multiple


# --- Working capital and operations ------------------------------------------------------------
def ccc(dio: float, dso: float, dpo: float) -> float:
    return dio + dso - dpo


def dso_days(receivable_days: Iterable[float]) -> float:
    xs = list(receivable_days)
    return sum(xs) / len(xs) if xs else 0.0


def littles_law(rate: float, time: float) -> float:
    return rate * time


def kingman_wq(ca2: float, cs2: float, rho: float, tau: float) -> float:
    if rho >= 1:
        return math.inf
    return ((ca2 + cs2) / 2) * (rho / (1 - rho)) * tau


def utilisation_alert(rho: float, p: FinanceParams = DEFAULT_PARAMS) -> str:
    if rho > p.utilisation_red:
        return "red"
    if rho > p.utilisation_yellow:
        return "yellow"
    return "ok"


def safety_stock(z: float, lead: float, sigma_d: float, demand: float, sigma_l: float) -> float:
    return z * math.sqrt(lead * sigma_d**2 + demand**2 * sigma_l**2)


def eoq_backorders(annual_demand: float, order_cost: float, holding: float, backorder: float) -> float:
    return math.sqrt(2 * annual_demand * order_cost / holding * (holding + backorder) / backorder)


# --- Unit economics (doc 79 §4, §6, colours = doc 72) ------------------------------------------
def margin_colour(margin: float) -> str:
    if margin <= 0.35:
        return "red"
    if margin < 0.50:
        return "yellow"
    return "green"


def route_economics(revenue: float, hours: float, km: float, stops: int, p: FinanceParams = DEFAULT_PARAMS) -> dict:
    direct = hours * p.driver_cost_per_h + km * p.vehicle_cost_per_km
    contribution = revenue - direct
    margin = contribution / revenue if revenue else 0.0
    return {
        "revenue": round(revenue, 2), "direct_cost": round(direct, 2), "contribution": round(contribution, 2),
        "margin": margin, "colour": margin_colour(margin), "per_stop": contribution / stops if stops else 0.0,
        "cost_per_stop": direct / stops if stops else 0.0, "revenue_per_driver_hour": revenue / hours if hours else 0.0,
        "stops_per_hour": stops / hours if hours else 0.0,
    }


def failed_delivery_cost(minutes: float, km: float, reattempt: float, fee_recovered: float,
                         p: FinanceParams = DEFAULT_PARAMS) -> float:
    return minutes * p.driver_cost_per_min + km * p.vehicle_cost_per_km + reattempt - fee_recovered


def cac(marketing: float, new_paying_orgs: int) -> float:
    return marketing / new_paying_orgs if new_paying_orgs else math.inf


def ltv(avg_monthly_contribution: float, gross_margin_months: float) -> float:
    return avg_monthly_contribution * gross_margin_months


def annual_da(p: FinanceParams = DEFAULT_PARAMS) -> float:
    return p.software_cost / p.software_life_years + (p.civic_cost - p.civic_residual) / p.civic_life_years


def break_even_stops(contribution_per_stop: float, p: FinanceParams = DEFAULT_PARAMS) -> dict:
    days = p.working_days_per_month
    da_m = annual_da(p) / 12
    eva_ebit_y = p.invested_capital * p.wacc / (1 - p.tax_rate)
    cash = p.cash_fixed_per_month
    acct = cash + da_m
    eva_m = eva_ebit_y / 12 + cash + da_m  # contribution must cover EBIT target + cash fixed + D&A
    per_day = lambda m: m / days / contribution_per_stop  # noqa: E731
    return {"cash": per_day(cash), "accounting": per_day(acct), "eva": per_day(eva_m),
            "eva_ebit_per_year": eva_ebit_y}


def payback_months(stops_per_day: float, contribution_per_stop: float, p: FinanceParams = DEFAULT_PARAMS) -> float:
    monthly = stops_per_day * p.working_days_per_month * contribution_per_stop - p.cash_fixed_per_month
    return p.invested_capital / monthly if monthly > 0 else math.inf


# --- Service and claims (doc 79 §6a) -----------------------------------------------------------
def otif(delivered: int, on_time_in_full: int) -> float:
    return on_time_in_full / delivered if delivered else 0.0


def otif_colour(v: float) -> str:
    return "green" if v >= 0.98 else "yellow" if v >= 0.95 else "red"


def dwell_leakage(dwell_min: float, p: FinanceParams = DEFAULT_PARAMS) -> tuple[float, float]:
    over = max(0.0, dwell_min - p.free_dwell_min)
    return over, over * p.driver_cost_per_min


def claim_cap(weight_kg: float, declared_value: float | None, *, covered: bool = False,
              proof_of_value: bool = False) -> float:
    """Ravi 2026-10-29: no cover -> default liability $4.41/kg (O. Reg. 643/05 Sch. 1);
    paid declared-value cover + proof of value -> declared value, max $2,500 per parcel."""
    default = round(4.41 * weight_kg, 2)
    if covered and proof_of_value and declared_value:
        return min(float(declared_value), 2500.0)
    return default


def claim_payable(loss: float, weight_kg: float, declared_value: float | None, *, covered: bool = False,
                  proof_of_value: bool = False) -> float:
    return min(loss, claim_cap(weight_kg, declared_value, covered=covered, proof_of_value=proof_of_value))


# --- Vehicle compliance money (doc 79 §6b / doc 80 §3) -----------------------------------------
def compliance_gap_cost(pa: float, pv: float, cf: float, cl: float) -> float:
    return pa * pv * (cf + cl)


def oos_margin_loss(n_stops: int, cm_stop: float, n_sub: int = 0, cm_sub: float = 0.0, c_idle: float = 0.0) -> float:
    return n_stops * cm_stop - cm_sub * n_sub + c_idle
