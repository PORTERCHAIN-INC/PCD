"""Super-admin stand-in for driver field actions on one order."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.admin_engine.audit import commit_admin_audit
from porterchain_api.admin_engine.rbac import AdminContext
from porterchain_api.admin_models import Driver
from porterchain_api.booking_models import Order
from porterchain_api.config import Settings
from porterchain_api.domain.admin_states import AdminRole
from porterchain_driver.field_admin import PARCEL_STATUSES, parcel_rows, perform, set_parcel_status

_ROUTE_STATES = {
    "DRIVER_ASSIGNED",
    "DRIVER_ACCEPTED",
    "DRIVER_EN_ROUTE",
    "AT_PICKUP",
    "PICKED_UP",
    "IN_TRANSIT",
    "AT_DESTINATION",
}


def driver_actions_for(state: str, *, has_driver: bool) -> list[dict[str, str]]:
    if not has_driver:
        return []
    current = (state or "").upper()
    items: list[tuple[str, str]] = []
    if current == "DRIVER_ASSIGNED":
        items.extend((("accept", "Accept order"), ("decline", "Decline order")))
    if current in _ROUTE_STATES:
        items.append(("start_route", "Start route"))
    if current in {"DRIVER_ACCEPTED", "DRIVER_EN_ROUTE"}:
        items.append(("arrive_pickup", "Arrive at pickup"))
    if current in {"DRIVER_ACCEPTED", "DRIVER_EN_ROUTE", "AT_PICKUP"}:
        items.append(("complete_pickup", "Complete pickup"))
    if current in {"PICKED_UP", "IN_TRANSIT"}:
        items.append(("arrive_delivery", "Arrive at delivery"))
    if current in {"PICKED_UP", "IN_TRANSIT", "AT_DESTINATION"}:
        items.append(("complete_delivery", "Complete delivery"))
    return [{"id": action_id, "label": label} for action_id, label in items]


class AdminDriverOpsService:
    def snapshot(self, db: Session, ctx: AdminContext, order_id: str) -> dict[str, Any]:
        self._require_super_admin(ctx)
        order = self._order(db, order_id)
        return {
            "order_id": order.id,
            "state": order.state,
            "driver_assigned": bool(order.assigned_driver_id),
            "actions": driver_actions_for(order.state, has_driver=bool(order.assigned_driver_id)),
            "parcels": parcel_rows(db, order),
            "parcel_statuses": list(PARCEL_STATUSES),
        }

    def run(
        self,
        db: Session,
        settings: Settings,
        ctx: AdminContext,
        order_id: str,
        action: str,
    ) -> dict[str, Any]:
        self._require_super_admin(ctx)
        order = self._order(db, order_id)
        allowed = {
            item["id"]
            for item in driver_actions_for(order.state, has_driver=bool(order.assigned_driver_id))
        }
        if action not in allowed:
            raise ValueError("That step is not available for this order.")
        driver = self._driver(db, order)
        perform(db, settings, driver, order, action)
        db.refresh(order)
        commit_admin_audit(
            db,
            ctx,
            action="ops.admin.driver_action",
            resource_type="order",
            resource_id=order.id,
            payload={"action": action, "order_state": order.state},
        )
        return {"ok": True, "order_id": order.id, "state": order.state, "action": action}

    def set_parcel_status(
        self,
        db: Session,
        ctx: AdminContext,
        order_id: str,
        parcel_id: str,
        status: str,
    ) -> dict[str, Any]:
        self._require_super_admin(ctx)
        order = self._order(db, order_id)
        parcel, previous = set_parcel_status(db, order, parcel_id, status)
        commit_admin_audit(
            db,
            ctx,
            action="ops.admin.parcel_status",
            resource_type="order",
            resource_id=order.id,
            payload={"parcel_id": parcel.id, "from": previous, "to": status},
        )
        return {
            "ok": True,
            "order_id": order.id,
            "parcel_id": parcel.id,
            "status": parcel.status,
            "previous_status": previous,
        }

    @staticmethod
    def _require_super_admin(ctx: AdminContext) -> None:
        if ctx.role != AdminRole.SUPER_ADMIN:
            raise PermissionError("super_admin_required")

    @staticmethod
    def _order(db: Session, order_id: str) -> Order:
        order = db.query(Order).filter(Order.id == order_id).first()
        if order is None:
            raise LookupError("order_not_found")
        return order

    @staticmethod
    def _driver(db: Session, order: Order) -> Driver:
        if not order.assigned_driver_id:
            raise ValueError("Assign a driver before running driver steps.")
        driver = db.query(Driver).filter(Driver.id == order.assigned_driver_id).first()
        if driver is None:
            raise LookupError("driver_not_found")
        return driver
