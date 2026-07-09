"""Order platform reports and live tracking."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from porterchain_api.admin_models import Claim
from porterchain_api.config import Settings
from porterchain_api.models import Order
from porterchain_api.order_engine.buckets import FAILED_STATES, RETURNED_STATES


class OrderPlatformReportsMixin:
    def reports(self, db: Session) -> dict[str, Any]:
        now = self._now()
        month_start = datetime(now.year, now.month, 1)
        merchants = self._merchant_map(db)
        drivers = self._driver_map(db)

        by_merchant: dict[str, int] = {}
        by_driver: dict[str, int] = {}
        for o in db.query(Order).filter(Order.created_at >= month_start).all():
            if o.merchant_id:
                name = merchants.get(o.merchant_id, o.merchant_id)
                by_merchant[name] = by_merchant.get(name, 0) + 1
            if o.assigned_driver_id:
                name = drivers[o.assigned_driver_id].full_name if o.assigned_driver_id in drivers else o.assigned_driver_id
                by_driver[name] = by_driver.get(name, 0) + 1

        failed = db.query(func.count(Order.id)).filter(Order.state.in_(FAILED_STATES), Order.created_at >= month_start).scalar() or 0
        returns = db.query(func.count(Order.id)).filter(Order.state.in_(RETURNED_STATES), Order.created_at >= month_start).scalar() or 0
        claims = db.query(func.count(Claim.id)).filter(Claim.created_at >= month_start).scalar() or 0
        revenue = (
            db.query(func.coalesce(func.sum(Order.amount_cents), 0))
            .filter(Order.created_at >= month_start, Order.state.notin_(("CANCELLED", "REFUNDED")))
            .scalar()
            or 0
        )

        return {
            "monthly_orders": db.query(func.count(Order.id)).filter(Order.created_at >= month_start).scalar() or 0,
            "monthly_revenue_cents": int(revenue),
            "failed_deliveries": int(failed),
            "returns": int(returns),
            "claims": int(claims),
            "avg_delivery_hours": self._avg_duration_hours(db, "order.picked_up", "order.delivered"),
            "top_merchants": sorted(by_merchant.items(), key=lambda x: -x[1])[:10],
            "top_drivers": sorted(by_driver.items(), key=lambda x: -x[1])[:10],
        }

    def order_tracking(self, db: Session, settings: Settings, order_id: str) -> dict[str, Any] | None:
        order = self.get_order(db, order_id)
        if not order:
            return None
        live = None
        try:
            live = self._tracking.get_live_tracking(db, settings, order)
        except Exception:
            pass
        return {
            "order_id": order.id,
            "tracking_number": order.tracking_number,
            "state": order.state,
            "scheduled_at": order.scheduled_at,
            "live": live,
            "history": [
                {
                    "event_type": ev.event_type,
                    "to_state": ev.to_state,
                    "occurred_at": ev.occurred_at,
                    "payload": ev.payload,
                }
                for ev in self.order_timeline(db, order_id)
            ],
        }
