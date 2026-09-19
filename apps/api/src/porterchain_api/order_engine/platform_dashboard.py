"""Order platform dashboard aggregates."""

from __future__ import annotations

from datetime import datetime, time
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from porterchain_api.admin_models import Claim
from porterchain_api.booking_models import Order
from porterchain_api.order_engine.buckets import (
    ASSIGNED_STATES,
    DONE_STATES,
    FAILED_STATES,
    PICKED_UP_STATES,
    RETURNED_STATES,
    WAITING_DISPATCH,
)


class OrderPlatformDashboardMixin:
    def dashboard(self, db: Session) -> dict[str, Any]:
        now = self._now()
        sod = datetime.combine(now.date(), time.min)
        stats = self._tower.stats(db)

        def count(states: tuple[str, ...]) -> int:
            return db.query(func.count(Order.id)).filter(Order.state.in_(states)).scalar() or 0

        delivered_today = (
            db.query(func.count(Order.id))
            .filter(Order.state.in_(DONE_STATES), Order.updated_at >= sod)
            .scalar()
            or 0
        )
        open_claims = db.query(func.count(Claim.id)).filter(Claim.status.notin_(("closed", "archived", "rejected"))).scalar() or 0

        sla_met = 0
        sla_total = 0
        for o in db.query(Order).filter(Order.state.in_(DONE_STATES), Order.updated_at >= sod).limit(200).all():
            sla_total += 1
            if self._tower._sla_status(o, now) == "met":
                sla_met += 1
        avg_sla = round((sla_met / sla_total * 100) if sla_total else 100.0, 1)

        return {
            "orders_today": stats["orders_today"],
            "orders_in_progress": stats["active_deliveries"],
            "waiting_dispatch": count(WAITING_DISPATCH),
            "assigned": count(ASSIGNED_STATES),
            "picked_up": count(PICKED_UP_STATES),
            "delivered": delivered_today,
            "failed": count(FAILED_STATES),
            "returned": count(RETURNED_STATES),
            "claims": int(open_claims),
            "revenue_today_cents": stats["revenue_today_cents"],
            "avg_delivery_hours": self._avg_duration_hours(db, "order.picked_up", "order.delivered"),
            "avg_pickup_hours": self._avg_duration_hours(db, "order.driver_assigned", "order.picked_up"),
            "avg_sla_percent": avg_sla,
        }
