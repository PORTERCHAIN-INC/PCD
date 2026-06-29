"""Dispatch operations — queue, assignment via Fleetbase bridge."""

from sqlalchemy.orm import Session

from porterchain_api.admin_engine.rbac import AdminContext
from porterchain_api.admin_models import AdminAuditLog, Driver
from porterchain_api.booking_engine._core import emit_event
from porterchain_api.admin_engine import events as E
from porterchain_api.booking_engine.order_transitions import transition_order_state
from porterchain_api.config import Settings
from porterchain_api.domain.states import OrderState
from porterchain_api.models import Order, OrderException


class AdminOperationsService:
    def dispatch_queue(self, db: Session, *, limit: int = 50) -> list[Order]:
        return (
            db.query(Order)
            .filter(Order.state == OrderState.DISPATCH_READY.value)
            .order_by(Order.scheduled_at.asc())
            .limit(limit)
            .all()
        )

    def exception_queue(self, db: Session, *, limit: int = 50) -> list[OrderException]:
        return (
            db.query(OrderException)
            .filter(OrderException.status == "open")
            .order_by(OrderException.created_at.desc())
            .limit(limit)
            .all()
        )

    def assign_driver(
        self,
        db: Session,
        settings: Settings,
        ctx: AdminContext,
        order_id: str,
        driver_id: str,
    ) -> Order:
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            raise LookupError("order_not_found")
        transition_order_state(
            db,
            order,
            OrderState.DRIVER_ASSIGNED,
            event_type="order.driver_assigned",
            actor_type="admin",
            actor_id=ctx.user.id,
            payload={"driver_id": driver_id},
        )
        order.assigned_driver_id = driver_id
        db.flush()
        db.add(
            AdminAuditLog(
                actor_user_id=ctx.user.id,
                action="dispatch.assigned",
                resource_type="order",
                resource_id=order_id,
                payload={"driver_id": driver_id},
            )
        )
        emit_event(
            db,
            event_type=E.DISPATCH_ASSIGNED,
            aggregate_type="order",
            aggregate_id=order_id,
            actor_type="admin",
            actor_id=ctx.user.id,
            payload={"driver_id": driver_id},
        )
        db.commit()
        db.refresh(order)
        return order

    def live_map_snapshot(self, db: Session) -> dict:
        orders_in_flight = (
            db.query(Order)
            .filter(
                Order.state.in_(
                    [
                        OrderState.DRIVER_ASSIGNED.value,
                        OrderState.DRIVER_EN_ROUTE.value,
                        OrderState.AT_PICKUP.value,
                        OrderState.PICKED_UP.value,
                        OrderState.IN_TRANSIT.value,
                        OrderState.AT_DESTINATION.value,
                    ]
                )
            )
            .limit(100)
            .all()
        )
        from porterchain_api.admin_models import Driver

        online_drivers = db.query(Driver).filter(Driver.is_online.is_(True)).limit(100).all()
        return {
            "drivers": [
                {"id": d.id, "name": d.full_name, "status": d.availability, "online": d.is_online}
                for d in online_drivers
            ],
            "orders": [
                {
                    "order_id": o.id,
                    "tracking": o.tracking_number,
                    "state": o.state,
                    "pickup": o.pickup,
                    "dropoff": o.dropoff,
                }
                for o in orders_in_flight
            ],
            "fleetbase_note": "GPS positions synced via Porterchain API bridge — not Fleetbase UI",
        }
