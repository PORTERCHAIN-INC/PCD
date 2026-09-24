"""Operations Control Tower aggregation — KPIs, board, order cards.

Per masterrule.md: order state machine, exceptions, claims, support, SLA and
notifications are Porterchain business logic. Dispatch/GPS/routes are executed
in Fleetbase and reached only via the Porterchain API + Fleetbase adapter.
This service reads the Porterchain order mirror; it never calls Fleetbase.
"""

from __future__ import annotations

from datetime import UTC, datetime, time, timedelta
from typing import Any

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from porterchain_api.admin_engine.control_tower._helpers import (
    BOARD_COLUMN_TARGET,
    BOARD_EXECUTION_COLUMNS,
    CARD_CAP,
    column_for_state,
    has_coords,
    now_utc,
    transition_path,
)
from porterchain_api.admin_engine.control_tower.assignment import AssignmentMixin
from porterchain_api.admin_engine.control_tower.events import EventsMixin
from porterchain_api.admin_engine.control_tower.exceptions import ExceptionsMixin
from porterchain_api.admin_engine.control_tower.sla import SlaMixin
from porterchain_api.admin_engine.rbac import AdminContext
from porterchain_api.admin_models import Claim, SupportTicket, Vehicle
from porterchain_api.booking_engine.order_sla import (
    AT_RISK_MINUTES,
    DEFAULT_INSTANT_SLA_HOURS,
    resolve_sla_deadline,
)
from porterchain_api.booking_engine.order_transitions import transition_order_state
from porterchain_api.domain.states import OrderState
from porterchain_api.booking_models import Order, OrderException
from porterchain_api.order_engine.buckets import (
    BOARD_COLUMNS,
    DELIVERY_LEG,
    DONE_STATES,
    FAILED_STATES,
    HIGH_PRIORITY_CENTS,
    IN_FLIGHT,
    PICKUP_LEG,
    WAITING,
)


class ControlTowerService(AssignmentMixin, ExceptionsMixin, SlaMixin, EventsMixin):
    # ------------------------------------------------------------------ #
    # KPIs
    # ------------------------------------------------------------------ #
    def stats(self, db: Session) -> dict[str, Any]:
        now = now_utc()
        sod = datetime.combine(now.date(), time.min)
        yesterday_start = sod - timedelta(days=1)

        def count(states: tuple[str, ...]) -> int:
            return (
                db.query(func.count(Order.id))
                .filter(Order.is_sandbox.is_(False), Order.state.in_(states))
                .scalar()
                or 0
            )

        def day_orders(start: datetime, end: datetime) -> int:
            return (
                db.query(func.count(Order.id))
                .filter(
                    Order.is_sandbox.is_(False),
                    Order.created_at >= start,
                    Order.created_at < end,
                )
                .scalar()
                or 0
            )

        def day_revenue(start: datetime, end: datetime) -> int:
            return int(
                db.query(func.coalesce(func.sum(Order.amount_cents), 0))
                .filter(
                    Order.is_sandbox.is_(False),
                    Order.created_at >= start,
                    Order.created_at < end,
                )
                .scalar()
                or 0
            )

        def day_completed(start: datetime, end: datetime) -> int:
            return (
                db.query(func.count(Order.id))
                .filter(
                    Order.is_sandbox.is_(False),
                    Order.state.in_(DONE_STATES),
                    Order.updated_at >= start,
                    Order.updated_at < end,
                )
                .scalar()
                or 0
            )

        orders_today = day_orders(sod, now + timedelta(days=1))
        revenue_today = day_revenue(sod, now + timedelta(days=1))
        completed_today = day_completed(sod, now + timedelta(days=1))
        orders_yesterday = day_orders(yesterday_start, sod)
        revenue_yesterday = day_revenue(yesterday_start, sod)
        completed_yesterday = day_completed(yesterday_start, sod)

        delayed = (
            db.query(func.count(Order.id))
            .filter(
                Order.is_sandbox.is_(False),
                Order.state.in_(IN_FLIGHT),
                Order.scheduled_at < now,
            )
            .scalar()
            or 0
        )
        high_priority = (
            db.query(func.count(Order.id))
            .filter(
                Order.is_sandbox.is_(False),
                Order.state.in_(IN_FLIGHT),
                Order.amount_cents >= HIGH_PRIORITY_CENTS,
            )
            .scalar()
            or 0
        )
        open_exceptions = (
            db.query(func.count(OrderException.id))
            .filter(OrderException.status.in_(["open", "acknowledged"]))
            .scalar()
            or 0
        )
        from porterchain_api.merchant_models import ShopifyIngressDlq

        shopify_dlq_open = (
            db.query(func.count(ShopifyIngressDlq.id))
            .filter(ShopifyIngressDlq.status.in_(("open", "held")))
            .scalar()
            or 0
        )
        open_exceptions = int(open_exceptions) + int(shopify_dlq_open)

        open_states = WAITING + IN_FLIGHT
        risk_end = now + timedelta(minutes=AT_RISK_MINUTES)
        sla_breached = (
            db.query(func.count(Order.id))
            .filter(
                Order.is_sandbox.is_(False),
                Order.state.in_(open_states),
                or_(Order.sla_deadline_at.is_(None), Order.sla_deadline_at < now),
            )
            .scalar()
            or 0
        )
        sla_at_risk = (
            db.query(func.count(Order.id))
            .filter(
                Order.is_sandbox.is_(False),
                Order.state.in_(open_states),
                Order.sla_deadline_at.isnot(None),
                Order.sla_deadline_at >= now,
                Order.sla_deadline_at <= risk_end,
            )
            .scalar()
            or 0
        )

        return {
            "orders_today": orders_today,
            "revenue_today_cents": revenue_today,
            "active_deliveries": count(IN_FLIGHT),
            "waiting_dispatch": count(WAITING),
            "pending_pickups": count(PICKUP_LEG),
            "pending_deliveries": count(DELIVERY_LEG),
            "delayed_orders": delayed,
            "high_priority_orders": high_priority,
            "failed_deliveries": count(FAILED_STATES),
            "completed_today": completed_today,
            # Driver online/GPS state is Fleetbase-owned (fleetbase-first policy).
            "vehicles_active": db.query(func.count(Vehicle.id)).filter(Vehicle.is_active == True).scalar() or 0,  # noqa: E712
            "open_claims": db.query(func.count(Claim.id)).filter(Claim.status == "open").scalar() or 0,
            "support_tickets": db.query(func.count(SupportTicket.id)).filter(SupportTicket.status == "open").scalar() or 0,
            "open_exceptions": open_exceptions,
            "shopify_ingress_dlq_open": shopify_dlq_open,
            "sla_at_risk": sla_at_risk,
            "sla_breached": sla_breached,
            "deltas": {
                "orders_today": orders_today - orders_yesterday,
                "revenue_today_cents": revenue_today - revenue_yesterday,
                "completed_today": completed_today - completed_yesterday,
            },
        }

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _merchant_names(self, db: Session) -> dict[str, str]:
        from porterchain_api.merchant_engine.lookups import company_names

        return company_names(db)

    def _driver_names(self, db: Session) -> dict[str, str]:
        from porterchain_api.admin_engine.repositories import DriverRepository

        return {d.id: d.full_name for d in DriverRepository().list_all(db)}

    @staticmethod
    def _stop_progress(o: Order) -> tuple[int, int]:
        """(stops_done, stop_count) — order-state heuristic until Fleetbase waypoint status syncs."""
        meta = o.compliance_metadata or {}
        rich = meta.get("stops")
        if isinstance(rich, list) and rich:
            stop_count = len([s for s in rich if isinstance(s, dict)])
        else:
            extras = meta.get("additional_stops") or []
            stop_count = 2 + (len(extras) if isinstance(extras, list) else 0)
        stop_count = max(stop_count, 2)

        state = o.state or ""
        if state in DONE_STATES:
            done = stop_count
        elif state in ("AT_DESTINATION",):
            done = max(stop_count - 1, 1)
        elif state in ("PICKED_UP", "IN_TRANSIT"):
            done = 1
        else:
            done = 0
        return min(done, stop_count), stop_count

    def _order_card(
        self,
        o: Order,
        merchants: dict,
        drivers: dict,
        now: datetime,
        *,
        instant_sla_hours: float | None = None,
    ) -> dict:
        from porterchain_api.order_engine.buckets import DELIVERY_ONLY_POOL

        pickup = o.pickup or {}
        dropoff = o.dropoff or {}
        hours = instant_sla_hours if instant_sla_hours is not None else DEFAULT_INSTANT_SLA_HOURS
        stored = getattr(o, "sla_deadline_at", None)
        deadline = stored if stored is not None else resolve_sla_deadline(o, instant_sla_hours=hours)
        sla_minutes: int | None = None
        if deadline is not None and o.state not in DONE_STATES:
            # resolve_sla_deadline / DB columns are naive UTC; now_utc() is aware.
            dl = deadline.astimezone(UTC).replace(tzinfo=None) if deadline.tzinfo else deadline
            ref = now.astimezone(UTC).replace(tzinfo=None) if now.tzinfo else now
            sla_minutes = int((dl - ref).total_seconds() // 60)
        stops_done, stop_count = self._stop_progress(o)
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
            "has_pickup_coords": has_coords(pickup),
            "has_dropoff_coords": has_coords(dropoff),
            "stop_phase": "delivery_only" if o.state in DELIVERY_ONLY_POOL else "full",
            "stop_count": stop_count,
            "stops_done": stops_done,
            "eta": o.scheduled_at.isoformat() if o.scheduled_at else None,
            "sla": self._sla_status(o, now, instant_sla_hours=hours),
            "sla_deadline": deadline.isoformat() if deadline else None,
            "sla_minutes_remaining": sla_minutes,
            "high_priority": o.amount_cents >= HIGH_PRIORITY_CENTS,
            "created_at": o.created_at.isoformat() if o.created_at else None,
        }

    # ------------------------------------------------------------------ #
    # Board / active orders
    # ------------------------------------------------------------------ #
    def board(self, db: Session) -> list[dict]:
        now = now_utc()
        merchants = self._merchant_names(db)
        drivers = self._driver_names(db)
        hours = self._instant_sla_hours(db)
        columns = []
        for key, states in BOARD_COLUMNS:
            q = db.query(Order).filter(Order.state.in_(states)).order_by(Order.scheduled_at.asc())
            total = q.count()
            cards = [
                self._order_card(o, merchants, drivers, now, instant_sla_hours=hours)
                for o in q.limit(CARD_CAP).all()
            ]
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
        *,
        reason: str | None = None,
    ) -> dict:
        """Drag-move on the board: exception columns only; execution moves are Fleetbase-owned."""
        if to_column in BOARD_EXECUTION_COLUMNS:
            raise ValueError(
                "execution_moves_run_in_fleetbase — use the Fleetbase console to "
                "dispatch/advance this order; this board only marks exceptions"
            )
        target_state_str = BOARD_COLUMN_TARGET.get(to_column)
        if not target_state_str:
            raise ValueError("invalid_board_column")

        note = (reason or "").strip()
        if to_column in {"failed", "returned", "lost", "damaged"} and len(note) < 3:
            raise ValueError("exception_reason_required")

        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            raise LookupError("order_not_found")

        if column_for_state(order.state) == to_column:
            now = now_utc()
            return self._order_card(
                order,
                self._merchant_names(db),
                self._driver_names(db),
                now,
                instant_sla_hours=self._instant_sla_hours(db),
            )

        from_state = OrderState(order.state)
        to_state = OrderState(target_state_str)
        path = transition_path(from_state, to_state)
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
                payload={
                    "to_column": to_column,
                    "target_state": step.value,
                    "reason": note or None,
                },
            )

        db.commit()
        db.refresh(order)
        now = now_utc()
        return self._order_card(
            order,
            self._merchant_names(db),
            self._driver_names(db),
            now,
            instant_sla_hours=self._instant_sla_hours(db),
        )

    def active_orders(self, db: Session, *, search: str | None = None, limit: int = 500) -> list[dict]:
        now = now_utc()
        merchants = self._merchant_names(db)
        drivers = self._driver_names(db)
        hours = self._instant_sla_hours(db)
        q = db.query(Order).filter(Order.state.in_(WAITING + IN_FLIGHT))
        if search:
            like = f"%{search}%"
            q = q.filter(Order.tracking_number.ilike(like) | Order.order_number.ilike(like))
        rows = q.order_by(Order.scheduled_at.asc()).limit(limit).all()
        return [self._order_card(o, merchants, drivers, now, instant_sla_hours=hours) for o in rows]

    def ops_search(self, db: Session, *, q: str, limit: int = 12) -> dict[str, Any]:
        """Cmd+K jump targets — orders + drivers (PC mirror only)."""
        from porterchain_api.admin_models import Driver

        needle = q.strip()
        like = f"%{needle}%"
        orders = (
            db.query(Order)
            .filter(
                (Order.tracking_number.ilike(like))
                | (Order.order_number.ilike(like))
                | (Order.id == needle)
            )
            .order_by(Order.created_at.desc())
            .limit(limit)
            .all()
        )
        drivers = (
            db.query(Driver)
            .filter(
                (Driver.full_name.ilike(like))
                | (Driver.email.ilike(like))
                | (Driver.id == needle)
            )
            .limit(limit)
            .all()
        )
        return {
            "q": needle,
            "orders": [
                {
                    "id": o.id,
                    "tracking_number": o.tracking_number,
                    "order_number": o.order_number,
                    "state": o.state,
                    "kind": "order",
                }
                for o in orders
            ],
            "drivers": [
                {
                    "id": d.id,
                    "name": d.full_name,
                    "online": bool(d.is_online) or d.availability == "online",
                    "kind": "driver",
                }
                for d in drivers
            ],
        }
