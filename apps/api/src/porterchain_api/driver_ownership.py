"""Which driver may act on an order (shared by driver API + scan lookup)."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session


def driver_owns_order(db: Session, driver_id: str, order: Any) -> bool:
    """Directly assigned, or (unassigned) a stop on the driver's current committed route.

    Before Oct 2026 any driver could act on an unassigned order.
    """
    if order is None:
        return False
    if order.assigned_driver_id:
        return order.assigned_driver_id == driver_id
    try:
        from porterchain_api.dispatch_engine.driver_route import DriverRouteService

        route = DriverRouteService().current_route(db, driver_id)
        if route is None:
            return False
        return any(str(s.get("order_id")) == str(order.id) for s in (route.stops or []))
    except Exception:  # noqa: BLE001 - fail closed
        return False
