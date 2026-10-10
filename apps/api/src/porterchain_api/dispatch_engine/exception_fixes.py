"""Rules-first fixes for Exceptions queue items. Suggest only — an admin applies one.

Actions:
- ``reroute``     re-plan the committed plan that carries the order (a new draft to commit);
- ``reassign``    hand the order to the best-ranked available driver;
- ``reschedule``  move the order to the next delivery slot and back into the pool;
- ``contact``     tell the customer/merchant (``order.delayed`` notification);
- ``rescue``      vehicle breakdown: move everything on the van to the nearest van that fits.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

ACTIONS = ("rescue", "reroute", "reassign", "reschedule", "contact")
ISSUE_MESSAGE = "There is an issue with your delivery. Our team will email you the next steps today."
BEFORE_PICKUP = {"DISPATCH_READY", "DRIVER_ASSIGNED", "DRIVER_ACCEPTED", "DRIVER_EN_ROUTE", "DRIVER_REJECTED"}


def _fix(action: str, label: str, why: str, **params: Any) -> dict[str, Any]:
    return {"action": action, "label": label, "why": why, "params": params}


def suggest(
    item: dict[str, Any],
    *,
    plan_id: str | None,
    best_driver: dict[str, Any] | None,
    next_slot: datetime | None,
) -> list[dict[str, Any]]:
    """Ranked fixes for one queue item; first = recommended."""
    kind, typ, state = item.get("kind"), str(item.get("type") or ""), str(item.get("state") or "")
    out: list[dict[str, Any]] = []
    driver = best_driver and _fix(
        "reassign", f"Reassign to {best_driver['name']}",
        f"cheapest insertion ({best_driver.get('insertion_minutes')} min added)", driver_id=best_driver["driver_id"],
    )
    reroute = plan_id and _fix("reroute", "Re-plan routes", "re-sequence the live plan around this stop", plan_id=plan_id)
    slot = next_slot and _fix(
        "reschedule", f"Reschedule to {next_slot:%a %H:%M}", "next open delivery slot", scheduled_at=next_slot.isoformat()
    )
    contact = _fix("contact", "Tell the customer", "send a delay update with the new ETA")

    if kind in {"late", "at_risk"}:
        if state in BEFORE_PICKUP and driver:
            out.append(driver)
        if reroute:
            out.append(reroute)
        out.append(contact)
    elif kind == "unassigned":
        if driver:
            out.append(driver)
        if reroute:
            out.append(reroute)
    elif kind == "margin":
        if reroute:
            out.append(_fix("reroute", "Re-plan to consolidate", "fewer, fuller routes lower cost per stop",
                            plan_id=plan_id))
        if driver:
            out.append(driver)
    elif kind == "failed" or typ in {"FAILED_DELIVERY", "CUSTOMER_UNAVAILABLE"}:
        if slot:
            out.append(slot)
        out.append(contact)
    elif typ == "VEHICLE_BREAKDOWN" and item.get("driver_id"):
        out.append(_fix("rescue", "Send rescue van", "nearest van that fits meets this one; boxes scan across",
                        driver_id=item["driver_id"]))
    elif typ in {"DRIVER_TIMEOUT", "DRIVER_REJECT", "VEHICLE_BREAKDOWN"}:
        if driver:
            out.append(driver)
        if reroute:
            out.append(reroute)
    elif kind in {"damaged", "lost", "claim", "return"} or typ in {"PARCEL_DAMAGED", "PARCEL_LOST"}:
        out.append(_fix("contact", "Tell the customer", "explain the issue and open the claim path",
                        message=ISSUE_MESSAGE))
    elif typ in {"WRONG_ADDRESS", "package_missing", "package_short_at_drop"}:
        out.append(contact)
    return [f for f in out if f]
