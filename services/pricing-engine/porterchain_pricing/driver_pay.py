"""
Driver pay plan — super-admin setting (`system_config` key `driver_pay_plan`)
and one pure function that turns worked time and stops into pay.

This is configuration + calculation only. Existing payouts (rate card
flat / percent per delivery, earnings ledger) are unchanged; nothing here moves
money. Amounts are integer cents.

Modes:
* hourly      — paid minutes × hourly rate, with optional minimum paid hours.
* per_stop    — stops × per_stop + pickups × per_pickup.
* per_route   — routes × per_route + stops above `route_included_stops` × extra.
* wave_block  — blocks × block_cents (+ stops above `block_included_stops` × extra);
                blocks = max(given, ceil(paid hours / block_hours)).
* hybrid      — max(guaranteed hourly, per-stop sum).
"""

from __future__ import annotations

import copy
import math
from dataclasses import dataclass, field
from typing import Any

MODES = ("hourly", "per_stop", "per_route", "wave_block", "hybrid")

#: EXAMPLE values awaiting a decision; $27/h and the 4 h block are decided.
PLACEHOLDER_PATHS = (
    "per_stop_cents",
    "per_pickup_cents",
    "per_route_cents",
    "route_included_stops",
    "route_extra_stop_cents",
    "wave_block.block_cents",
    "wave_block.included_stops",
    "wave_block.extra_stop_cents",
)

_DEFAULT_PLAN: dict[str, Any] = {
    "schema": 1,
    "mode": "wave_block",
    "hourly_cents": 2700,
    "minimum_paid_hours": 0,
    "per_stop_cents": 800,
    "per_pickup_cents": 0,
    "per_route_cents": 10800,
    "route_included_stops": 4,
    "route_extra_stop_cents": 800,
    "wave_block": {"block_hours": 4, "block_cents": 10800, "included_stops": 0, "extra_stop_cents": 0},
}


def default_driver_pay_plan() -> dict[str, Any]:
    return copy.deepcopy(_DEFAULT_PLAN)


def _nonneg_int(value: Any, path: str) -> int:
    try:
        out = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"driver_pay_invalid:{path}") from exc
    if out < 0:
        raise ValueError(f"driver_pay_invalid:{path}")
    return out


def normalize_driver_pay_plan(raw: Any) -> dict[str, Any]:
    src = raw if isinstance(raw, dict) else {}
    plan = default_driver_pay_plan()
    for key, value in src.items():
        if key == "wave_block" and isinstance(value, dict):
            plan["wave_block"].update(value)
        elif key in plan:
            plan[key] = value
    mode = str(plan.get("mode") or "")
    if mode not in MODES:
        raise ValueError("driver_pay_invalid:mode")
    out: dict[str, Any] = {"schema": 1, "mode": mode}
    for key in (
        "hourly_cents",
        "per_stop_cents",
        "per_pickup_cents",
        "per_route_cents",
        "route_included_stops",
        "route_extra_stop_cents",
    ):
        out[key] = _nonneg_int(plan[key], key)
    try:
        out["minimum_paid_hours"] = max(0.0, float(plan.get("minimum_paid_hours") or 0))
    except (TypeError, ValueError) as exc:
        raise ValueError("driver_pay_invalid:minimum_paid_hours") from exc
    wb = plan["wave_block"]
    try:
        block_hours = float(wb.get("block_hours") or 0)
    except (TypeError, ValueError) as exc:
        raise ValueError("driver_pay_invalid:wave_block.block_hours") from exc
    if block_hours <= 0:
        raise ValueError("driver_pay_invalid:wave_block.block_hours")
    out["wave_block"] = {
        "block_hours": block_hours,
        "block_cents": _nonneg_int(wb.get("block_cents"), "wave_block.block_cents"),
        "included_stops": _nonneg_int(wb.get("included_stops", 0), "wave_block.included_stops"),
        "extra_stop_cents": _nonneg_int(wb.get("extra_stop_cents", 0), "wave_block.extra_stop_cents"),
    }
    return out


@dataclass(frozen=True)
class DriverPayLine:
    code: str
    label: str
    amount_cents: int


@dataclass(frozen=True)
class DriverPay:
    mode: str
    total_cents: int
    lines: tuple[DriverPayLine, ...] = field(default_factory=tuple)


def _hourly(plan: dict[str, Any], paid_minutes: float) -> DriverPay:
    hours = max(paid_minutes / 60.0, float(plan["minimum_paid_hours"]))
    cents = int(round(hours * plan["hourly_cents"]))
    return DriverPay("hourly", cents, (DriverPayLine("hourly", f"{hours:g} h × hourly", cents),))


def _per_stop(plan: dict[str, Any], stops: int, pickups: int) -> DriverPay:
    lines = [
        DriverPayLine("stops", f"{stops} stops", stops * plan["per_stop_cents"]),
        DriverPayLine("pickups", f"{pickups} pickups", pickups * plan["per_pickup_cents"]),
    ]
    lines = [line for line in lines if line.amount_cents]
    return DriverPay("per_stop", sum(line.amount_cents for line in lines), tuple(lines))


def compute_driver_pay(
    plan_raw: Any,
    *,
    paid_minutes: float = 0.0,
    stops: int = 0,
    pickups: int = 0,
    routes: int = 0,
    blocks: int = 0,
) -> DriverPay:
    """Pay for one pay period of work under the plan (validated first)."""
    plan = normalize_driver_pay_plan(plan_raw)
    paid_minutes = max(float(paid_minutes or 0), 0.0)
    stops = max(int(stops or 0), 0)
    pickups = max(int(pickups or 0), 0)
    mode = plan["mode"]

    if mode == "hourly":
        return _hourly(plan, paid_minutes)
    if mode == "per_stop":
        return _per_stop(plan, stops, pickups)
    if mode == "per_route":
        n_routes = max(int(routes or 0), 1 if stops else 0)
        extra = max(stops - plan["route_included_stops"] * n_routes, 0)
        lines = [
            DriverPayLine("routes", f"{n_routes} routes", n_routes * plan["per_route_cents"]),
            DriverPayLine("extra_stops", f"{extra} stops over included", extra * plan["route_extra_stop_cents"]),
        ]
        lines = [line for line in lines if line.amount_cents]
        return DriverPay(mode, sum(line.amount_cents for line in lines), tuple(lines))
    if mode == "wave_block":
        wb = plan["wave_block"]
        by_time = math.ceil(paid_minutes / 60.0 / wb["block_hours"] - 1e-9) if paid_minutes else 0
        n_blocks = max(int(blocks or 0), by_time, 1 if (stops or pickups) else 0)
        extra = max(stops - wb["included_stops"] * n_blocks, 0) if wb["included_stops"] else 0
        lines = [
            DriverPayLine("blocks", f"{n_blocks} × {wb['block_hours']:g} h block", n_blocks * wb["block_cents"]),
            DriverPayLine("extra_stops", f"{extra} stops over included", extra * wb["extra_stop_cents"]),
        ]
        lines = [line for line in lines if line.amount_cents]
        return DriverPay(mode, sum(line.amount_cents for line in lines), tuple(lines))
    # hybrid: guaranteed hourly vs per-stop sum, whichever is higher.
    hourly = _hourly(plan, paid_minutes)
    per_stop = _per_stop(plan, stops, pickups)
    best = per_stop if per_stop.total_cents > hourly.total_cents else hourly
    return DriverPay("hybrid", best.total_cents, best.lines)
