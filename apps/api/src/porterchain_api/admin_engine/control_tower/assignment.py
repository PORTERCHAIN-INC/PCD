"""Dispatch queue + assignable driver listing (compliance gate)."""

from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from porterchain_api.admin_models import Driver
from porterchain_api.models import Order
from porterchain_api.order_engine.buckets import DELIVERY_ONLY_POOL, DISPATCH_POOL, IN_FLIGHT

from porterchain_api.admin_engine.control_tower._helpers import now_utc


class AssignmentMixin:
    def queue(self, db: Session, *, limit: int = 200) -> list[dict]:
        return self.dispatch_pool(db, limit=limit)

    def dispatch_pool(self, db: Session, *, limit: int = 200) -> list[dict]:
        """Unassigned orders waiting for dispatch (waiting + retryable)."""
        now = now_utc()
        merchants = self._merchant_names(db)
        drivers = self._driver_names(db)
        hours = self._instant_sla_hours(db)
        pool_states = DISPATCH_POOL + DELIVERY_ONLY_POOL
        rows = (
            db.query(Order)
            .filter(
                Order.assigned_driver_id.is_(None),
                Order.state.in_(pool_states),
            )
            .order_by(Order.scheduled_at.asc())
            .limit(limit)
            .all()
        )
        return [self._order_card(o, merchants, drivers, now, instant_sla_hours=hours) for o in rows]

    def assignable_drivers(self, db: Session) -> list[dict]:
        # Compliance gate only (PC-owned). Prefer Fleetbase live online when the
        # bridge is up (D-26); otherwise fall back to mirrored Driver.is_online.
        rows = (
            db.query(Driver)
            .filter(Driver.status == "APPROVED")
            .order_by(Driver.rating.desc().nullslast())
            .limit(100)
            .all()
        )
        loads = dict(
            db.query(Order.assigned_driver_id, func.count(Order.id))
            .filter(Order.state.in_(IN_FLIGHT), Order.assigned_driver_id.isnot(None))
            .group_by(Order.assigned_driver_id)
            .all()
        )
        online_by_fb: dict[str, bool] = {}
        try:
            from porterchain_api.config import get_settings
            from porterchain_api.services.fleetbase_integration import get_fleetbase_integration

            fb = get_fleetbase_integration(get_settings())
            if fb.is_enabled:
                for fd in fb.list_drivers(limit=300):
                    fid = str(fd.get("id") or fd.get("uuid") or "")
                    if not fid:
                        continue
                    online = fd.get("online")
                    if not isinstance(online, bool):
                        online = str(fd.get("status") or "").lower() in {"online", "active"}
                    online_by_fb[fid] = bool(online)
        except Exception:
            online_by_fb = {}

        out: list[dict] = []
        for d in rows:
            if d.fleetbase_driver_id and d.fleetbase_driver_id in online_by_fb:
                is_online = online_by_fb[d.fleetbase_driver_id]
            else:
                is_online = bool(d.is_online) or d.availability == "online"
            out.append(
                {
                    "id": d.id,
                    "name": d.full_name,
                    "rating": d.rating,
                    "is_online": is_online,
                    "active_orders": loads.get(d.id, 0),
                    "medical_transport_certified": bool(d.medical_transport_certified),
                }
            )
        return out
