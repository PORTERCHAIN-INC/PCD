"""Operations Control Tower aggregation.

Per masterrule.md: order state machine, exceptions, claims, support, SLA and
notifications are Porterchain business logic. Dispatch/GPS/routes are executed
in Fleetbase and reached only via the Porterchain API + Fleetbase adapter.
This service reads the Porterchain order mirror; it never calls Fleetbase.
"""

from __future__ import annotations

from collections import deque
from datetime import UTC, datetime, time, timedelta
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from porterchain_api.admin_engine.rbac import AdminContext
from porterchain_api.admin_models import Claim, Driver, SupportTicket, Vehicle
from porterchain_api.booking_engine.order_transitions import transition_order_state
from porterchain_api.domain.states import ORDER_TRANSITIONS, OrderState
from porterchain_api.models import DomainEvent, Order, OrderException

from porterchain_api.order_engine.buckets import (
    BOARD_COLUMNS,
    DELIVERY_LEG,
    DELIVERY_ONLY_POOL,
    DISPATCH_POOL,
    DONE_STATES,
    FAILED_STATES,
    HIGH_PRIORITY_CENTS,
    IN_FLIGHT,
    PICKUP_LEG,
    WAITING,
)
CARD_CAP = 60

# Canonical order state when an order is dropped on a board column.
BOARD_COLUMN_TARGET: dict[str, str] = {
    "waiting_dispatch": "DISPATCH_READY",
    "assigned": "DRIVER_ASSIGNED",
    "accepted": "DRIVER_ACCEPTED",
    "heading_to_pickup": "DRIVER_EN_ROUTE",
    "at_pickup": "AT_PICKUP",
    "picked_up": "PICKED_UP",
    "in_transit": "IN_TRANSIT",
    "near_delivery": "AT_DESTINATION",
    "delivered": "DELIVERED",
    "failed": "FAILED",
    "returned": "RETURN_TO_SENDER",
    "lost": "LOST",
    "damaged": "DAMAGED",
}


def _column_for_state(state: str) -> str | None:
    for key, states in BOARD_COLUMNS:
        if state in states:
            return key
    return None


def _transition_path(from_state: OrderState, to_state: OrderState) -> list[OrderState] | None:
    if from_state == to_state:
        return []
    queue: deque[tuple[OrderState, list[OrderState]]] = deque([(from_state, [])])
    visited = {from_state}
    while queue:
        current, steps = queue.popleft()
        for nxt in ORDER_TRANSITIONS.get(current, set()):
            if nxt == to_state:
                return steps + [nxt]
            if nxt not in visited:
                visited.add(nxt)
                queue.append((nxt, steps + [nxt]))
    return None


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _has_coords(addr: dict | None) -> bool:
    if not addr:
        return False
    lat = addr.get("lat") or addr.get("latitude")
    lng = addr.get("lng") or addr.get("lon") or addr.get("longitude")
    return lat is not None and lng is not None


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
        pickup = o.pickup or {}
        dropoff = o.dropoff or {}
        has_pickup = _has_coords(pickup)
        has_dropoff = _has_coords(dropoff)
        stop_phase = "delivery_only" if o.state in DELIVERY_ONLY_POOL else "full"
        return {
            "id": o.id,
            "order_number": o.order_number,
            "tracking_number": o.tracking_number,
            "state": o.state,
            "amount_cents": o.amount_cents,
            "merchant": merchants.get(o.merchant_id) if o.merchant_id else None,
            "driver": drivers.get(o.assigned_driver_id) if o.assigned_driver_id else None,
            "driver_id": o.assigned_driver_id,
            "pickup": pickup.get("formatted") or pickup.get("city"),
            "dropoff": dropoff.get("formatted") or dropoff.get("city"),
            "has_pickup_coords": has_pickup,
            "has_dropoff_coords": has_dropoff,
            "stop_phase": stop_phase,
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

    def move_board_order(
        self,
        db: Session,
        ctx: AdminContext,
        order_id: str,
        to_column: str,
    ) -> dict:
        """Advance order state by dragging on the dispatch board."""
        target_state_str = BOARD_COLUMN_TARGET.get(to_column)
        if not target_state_str:
            raise ValueError("invalid_board_column")

        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            raise LookupError("order_not_found")

        if _column_for_state(order.state) == to_column:
            now = _now()
            return self._order_card(
                order,
                self._merchant_names(db),
                self._driver_names(db),
                now,
            )

        from_state = OrderState(order.state)
        to_state = OrderState(target_state_str)
        path = _transition_path(from_state, to_state)
        if path is None:
            raise ValueError("invalid_order_transition_path")

        for step in path:
            transition_order_state(
                db,
                order,
                step,
                event_type="order.dispatch_board_move",
                actor_type="admin",
                actor_id=ctx.user.id,
                payload={"to_column": to_column, "target_state": step.value},
            )

        db.commit()
        db.refresh(order)
        now = _now()
        return self._order_card(
            order,
            self._merchant_names(db),
            self._driver_names(db),
            now,
        )

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

    def queue(self, db: Session, *, limit: int = 200) -> list[dict]:
        return self.dispatch_pool(db, limit=limit)

    def dispatch_pool(self, db: Session, *, limit: int = 200) -> list[dict]:
        """Unassigned orders waiting for dispatch (waiting + retryable)."""
        now = _now()
        merchants = self._merchant_names(db)
        drivers = self._driver_names(db)
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
