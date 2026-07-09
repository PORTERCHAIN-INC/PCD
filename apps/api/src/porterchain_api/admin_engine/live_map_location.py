"""Location and assignment query helpers for the live operations map."""

from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from porterchain_api.admin_engine.control_tower_service import IN_FLIGHT
from porterchain_api.admin_models import Vehicle
from porterchain_api.driver_models import DriverLocationPing
from porterchain_api.models import Order


class LiveMapLocationMixin:
    def _latest_pings(self, db: Session) -> dict[str, DriverLocationPing]:
        subq = (
            db.query(
                DriverLocationPing.driver_id,
                func.max(DriverLocationPing.created_at).label("max_at"),
            )
            .group_by(DriverLocationPing.driver_id)
            .subquery()
        )
        rows = (
            db.query(DriverLocationPing)
            .join(
                subq,
                (DriverLocationPing.driver_id == subq.c.driver_id)
                & (DriverLocationPing.created_at == subq.c.max_at),
            )
            .all()
        )
        return {p.driver_id: p for p in rows}

    def _driver_vehicle_map(self, db: Session) -> dict[str, Vehicle]:
        vehicles = db.query(Vehicle).filter(Vehicle.is_active.is_(True)).all()
        out: dict[str, Vehicle] = {}
        for v in vehicles:
            if v.driver_id and v.driver_id not in out:
                out[v.driver_id] = v
        return out

    def _active_order_by_driver(self, db: Session) -> dict[str, Order]:
        rows = db.query(Order).filter(Order.state.in_(IN_FLIGHT), Order.assigned_driver_id.isnot(None)).all()
        return {o.assigned_driver_id: o for o in rows if o.assigned_driver_id}
