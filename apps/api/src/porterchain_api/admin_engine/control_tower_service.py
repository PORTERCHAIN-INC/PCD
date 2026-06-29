"""Operations Control Tower aggregation.

Per masterrule.md: order state machine, exceptions, claims, support, SLA and
notifications are Porterchain business logic. Dispatch/GPS/routes are executed
in Fleetbase and reached only via the Porterchain API + Fleetbase adapter.
This service reads the Porterchain order mirror; it never calls Fleetbase.
"""

from __future__ import annotations

from datetime import UTC, datetime, time, timedelta
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from porterchain_api.admin_models import Claim, Driver, SupportTicket, Vehicle
from porterchain_api.models import DomainEvent, Order, OrderException

# Operational order states.
WAITING = ("DISPATCH_READY",)
PICKUP_LEG = ("DRIVER_ASSIGNED", "DRIVER_ACCEPTED", "DRIVER_EN_ROUTE", "AT_PICKUP")
DELIVERY_LEG = ("PICKED_UP", "IN_TRANSIT", "AT_DESTINATION")
IN_FLIGHT = PICKUP_LEG + DELIVERY_LEG
FAILED_STATES = ("FAILED", "RETURN_TO_SENDER", "LOST", "DAMAGED")
DONE_STATES = ("DELIVERED", "POD_COMPLETED", "INVOICED", "CLOSED")

# Board column → order states.
BOARD_COLUMNS: list[tuple[str, tuple[str, ...]]] = [
    ("waiting_dispatch", ("BOOKED", "DISPATCH_READY")),
    ("assigned", ("DRIVER_ASSIGNED",)),
    ("accepted", ("DRIVER_ACCEPTED",)),
    ("heading_to_pickup", ("DRIVER_EN_ROUTE",)),
    ("at_pickup", ("AT_PICKUP",)),
    ("picked_up", ("PICKED_UP",)),
    ("in_transit", ("IN_TRANSIT",)),
    ("near_delivery", ("AT_DESTINATION",)),
    ("delivered", ("DELIVERED", "POD_COMPLETED")),
    ("failed", ("FAILED",)),
    ("returned", ("RETURN_TO_SENDER",)),
    ("lost", ("LOST",)),
    ("damaged", ("DAMAGED",)),
]

HIGH_PRIORITY_CENTS = 20000
CARD_CAP = 60


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class ControlTowerService:
    # ------------------------------------------------------------------ #
    # KPIs
    # ------------------------------------------------------------------ #
    def stats(self, db: Session) -> dict[str, Any]:
        now = _now()
        sod = datetime.combine(now.date(), time.min)

        def count(states: tuple[str, ...]) -> int:
            return db.query(func.count(Order.id)).filter(Order.state.in_(states)).scalar() or 0

        orders_today = db.query(func.count(Order.id)).filter(Order.created_at >= sod).scalar() or 0
        revenue_today = (
            db.query(func.coalesce(func.sum(Order.amount_cents), 0)).filter(Order.created_at >= sod).scalar() or 0
        )
        delayed = (
            db.query(func.count(Order.id))
            .filter(Order.state.in_(IN_FLIGHT), Order.scheduled_at < now)
            .scalar()
            or 0
        )
        high_priority = (
            db.query(func.count(Order.id))
            .filter(Order.state.in_(IN_FLIGHT), Order.amount_cents >= HIGH_PRIORITY_CENTS)
            .scalar()
            or 0
        )
        return {
            "orders_today": orders_today,
            "revenue_today_cents": int(revenue_today),
            "active_deliveries": count(IN_FLIGHT),
            "waiting_dispatch": count(WAITING),
            "pending_pickups": count(PICKUP_LEG),
            "pending_deliveries": count(DELIVERY_LEG),
            "delayed_orders": delayed,
            "high_priority_orders": high_priority,
            "failed_deliveries": count(FAILED_STATES),
            "completed_today": db.query(func.count(Order.id)).filter(Order.state.in_(DONE_STATES), Order.updated_at >= sod).scalar() or 0,
            "drivers_online": db.query(func.count(Driver.id)).filter(Driver.is_online == True).scalar() or 0,  # noqa: E712
            "drivers_offline": db.query(func.count(Driver.id)).filter(Driver.is_online == False).scalar() or 0,  # noqa: E712
            "vehicles_active": db.query(func.count(Vehicle.id)).filter(Vehicle.is_active == True).scalar() or 0,  # noqa: E712
            "open_claims": db.query(func.count(Claim.id)).filter(Claim.status == "open").scalar() or 0,
            "support_tickets": db.query(func.count(SupportTicket.id)).filter(SupportTicket.status == "open").scalar() or 0,
            "open_exceptions": db.query(func.count(OrderException.id)).filter(OrderException.status == "open").scalar() or 0,
        }

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _merchant_names(self, db: Session) -> dict[str, str]:
        from porterchain_api.merchant_models import Merchant

        return {m.id: m.company_name for m in db.query(Merchant).all()}

    def _driver_names(self, db: Session) -> dict[str, str]:
        return {d.id: d.full_name for d in db.query(Driver).all()}

    def _sla_status(self, order: Order, now: datetime) -> str:
        if order.state in DONE_STATES:
            return "met"
        if not order.scheduled_at:
            return "ok"
        sched = order.scheduled_at.replace(tzinfo=None) if order.scheduled_at.tzinfo else order.scheduled_at
        if now > sched:
            return "breached"
        if (sched - now) <= timedelta(minutes=30):
            return "at_risk"
        return "ok"

    def _order_card(self, o: Order, merchants: dict, drivers: dict, now: datetime) -> dict:
        return {
            "id": o.id,
            "order_number": o.order_number,
            "tracking_number": o.tracking_number,
            "state": o.state,
            "amount_cents": o.amount_cents,
            "merchant": merchants.get(o.merchant_id) if o.merchant_id else None,
            "driver": drivers.get(o.assigned_driver_id) if o.assigned_driver_id else None,
            "driver_id": o.assigned_driver_id,
            "pickup": (o.pickup or {}).get("formatted") or (o.pickup or {}).get("city"),
            "dropoff": (o.dropoff or {}).get("formatted") or (o.dropoff or {}).get("city"),
            "eta": o.scheduled_at.isoformat() if o.scheduled_at else None,
            "sla": self._sla_status(o, now),
            "high_priority": o.amount_cents >= HIGH_PRIORITY_CENTS,
            "created_at": o.created_at.isoformat() if o.created_at else None,
        }

    # ------------------------------------------------------------------ #
    # Board / active orders / queue
    # ------------------------------------------------------------------ #
    def board(self, db: Session) -> list[dict]:
        now = _now()
        merchants = self._merchant_names(db)
        drivers = self._driver_names(db)
        columns = []
        for key, states in BOARD_COLUMNS:
            q = db.query(Order).filter(Order.state.in_(states)).order_by(Order.scheduled_at.asc())
            total = q.count()
            cards = [self._order_card(o, merchants, drivers, now) for o in q.limit(CARD_CAP).all()]
            columns.append(
                {
                    "key": key,
                    "count": total,
                    "hidden": max(0, total - len(cards)),
                    "value_cents": sum(c["amount_cents"] for c in cards),
                    "orders": cards,
                }
            )
        return columns

    def active_orders(self, db: Session, *, search: str | None = None, limit: int = 500) -> list[dict]:
        now = _now()
        merchants = self._merchant_names(db)
        drivers = self._driver_names(db)
        q = db.query(Order).filter(Order.state.in_(WAITING + IN_FLIGHT))
        if search:
            like = f"%{search}%"
            q = q.filter(Order.tracking_number.ilike(like) | Order.order_number.ilike(like))
        rows = q.order_by(Order.scheduled_at.asc()).limit(limit).all()
        return [self._order_card(o, merchants, drivers, now) for o in rows]

    def queue(self, db: Session, *, limit: int = 100) -> list[dict]:
        now = _now()
        merchants = self._merchant_names(db)
        drivers = self._driver_names(db)
        rows = (
            db.query(Order)
            .filter(Order.state.in_(WAITING))
            .order_by(Order.scheduled_at.asc())
            .limit(limit)
            .all()
        )
        return [self._order_card(o, merchants, drivers, now) for o in rows]

    def assignable_drivers(self, db: Session) -> list[dict]:
        rows = (
            db.query(Driver)
            .filter(Driver.status == "APPROVED")
            .order_by(Driver.is_online.desc(), Driver.rating.desc().nullslast())
            .limit(100)
            .all()
        )
        return [
            {"id": d.id, "name": d.full_name, "online": d.is_online, "availability": d.availability, "rating": d.rating}
            for d in rows
        ]

    # ------------------------------------------------------------------ #
    # Exceptions / SLA / activity / AI
    # ------------------------------------------------------------------ #
    def exceptions(self, db: Session, *, limit: int = 100) -> list[dict]:
        merchants = self._merchant_names(db)
        rows = (
            db.query(OrderException, Order)
            .join(Order, Order.id == OrderException.order_id)
            .filter(OrderException.status == "open")
            .order_by(OrderException.created_at.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "id": e.id,
                "type": e.type,
                "status": e.status,
                "order_id": e.order_id,
                "tracking_number": o.tracking_number,
                "merchant": merchants.get(o.merchant_id) if o.merchant_id else None,
                "reported_by": e.reported_by_type,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e, o in rows
        ]

    def sla_monitor(self, db: Session, *, limit: int = 200) -> dict:
        now = _now()
        merchants = self._merchant_names(db)
        drivers = self._driver_names(db)
        rows = db.query(Order).filter(Order.state.in_(WAITING + IN_FLIGHT)).all()
        at_risk: list[dict] = []
        breached: list[dict] = []
        for o in rows:
            status = self._sla_status(o, now)
            card = self._order_card(o, merchants, drivers, now)
            if status == "breached":
                breached.append(card)
            elif status == "at_risk":
                at_risk.append(card)
        breached.sort(key=lambda c: c["eta"] or "")
        at_risk.sort(key=lambda c: c["eta"] or "")
        return {"breached": breached[:limit], "at_risk": at_risk[:limit], "breached_count": len(breached), "at_risk_count": len(at_risk)}

    def live_activity(self, db: Session, *, limit: int = 60) -> list[dict]:
        rows = db.query(DomainEvent).order_by(DomainEvent.occurred_at.desc()).limit(limit).all()
        return [
            {
                "id": e.id,
                "event_type": e.event_type,
                "aggregate_type": e.aggregate_type,
                "aggregate_id": e.aggregate_id,
                "actor_type": e.actor_type,
                "occurred_at": e.occurred_at.isoformat() if e.occurred_at else None,
            }
            for e in rows
        ]

    def ai_ops(self, db: Session) -> dict:
        now = _now()
        merchants = self._merchant_names(db)
        drivers = self._driver_names(db)
        rows = db.query(Order).filter(Order.state.in_(WAITING + IN_FLIGHT)).all()
        risk_orders: list[dict] = []
        for o in rows:
            sla = self._sla_status(o, now)
            score = 0
            reasons = []
            if sla == "breached":
                score += 60
                reasons.append("SLA breached")
            elif sla == "at_risk":
                score += 35
                reasons.append("Approaching SLA")
            if o.amount_cents >= HIGH_PRIORITY_CENTS:
                score += 20
                reasons.append("High-value order")
            if o.state in WAITING:
                score += 15
                reasons.append("Awaiting dispatch")
            if not o.assigned_driver_id and o.state not in WAITING:
                score += 10
                reasons.append("No driver assigned")
            if score >= 35:
                card = self._order_card(o, merchants, drivers, now)
                card["risk_score"] = min(100, score)
                card["reasons"] = reasons
                risk_orders.append(card)
        risk_orders.sort(key=lambda c: c["risk_score"], reverse=True)
        # Suggested drivers for dispatch (online, approved, top rated).
        suggested = self.assignable_drivers(db)
        online_suggested = [d for d in suggested if d["online"]][:5]
        return {
            "risk_orders": risk_orders[:25],
            "suggested_drivers": online_suggested,
            "recommendation": (
                f"{len(risk_orders)} orders need attention. Prioritise SLA-breached and high-value first."
                if risk_orders
                else "All in-flight orders are on track."
            ),
        }
