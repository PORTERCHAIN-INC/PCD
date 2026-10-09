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
        items.append(("complete_delivery_without_proof", "Finish without proof"))
    return [{"id": action_id, "label": label} for action_id, label in items]


class AdminDriverOpsService:
    def snapshot(self, db: Session, ctx: AdminContext, order_id: str) -> dict[str, Any]:
        self._require_super_admin(ctx)
        order = self._order(db, order_id)
        payload = {
            "order_id": order.id,
            "state": order.state,
            "driver_assigned": bool(order.assigned_driver_id),
            "actions": driver_actions_for(order.state, has_driver=bool(order.assigned_driver_id)),
            "parcels": parcel_rows(db, order),
            "parcel_statuses": list(PARCEL_STATUSES),
            "extra_stops": list((order.compliance_metadata or {}).get("admin_extra_stops") or [])
            if isinstance(order.compliance_metadata, dict)
            else [],
        }
        from porterchain_api.admin_engine.audit import commit_admin_write

        # package_rows may insert Package rows. get_db does not commit, so those
        # ids would vanish and the next status change would be parcel_not_found.
        commit_admin_write(db)
        return payload

    def run(
        self,
        db: Session,
        settings: Settings,
        ctx: AdminContext,
        order_id: str,
        action: str,
        reason: str | None = None,
    ) -> dict[str, Any]:
        self._require_super_admin(ctx)
        order = self._order(db, order_id)
        override = action == "complete_delivery_without_proof"
        clean_reason = (reason or "").strip()
        if override and len(clean_reason) < 5:
            raise ValueError("Give a reason (at least 5 characters) to finish without proof.")
        allowed = {
            item["id"]
            for item in driver_actions_for(order.state, has_driver=bool(order.assigned_driver_id))
        }
        if action not in allowed:
            raise ValueError("That step is not available for this order.")
        driver = self._driver(db, order)
        override_context: dict[str, Any] = {}
        if override:
            from porterchain_driver.pod_policy import is_on_duty, missing_for

            override_context = {
                "reason": clean_reason[:500],
                "pod_missing": missing_for(db, order),
                "driver_on_duty": is_on_duty(db, driver),
                "driver_id": driver.id,
            }
        perform(db, settings, driver, order, action)
        db.refresh(order)
        if override:
            from porterchain_api.platform.delivery_override_events import emit_delivery_override

            emit_delivery_override(
                db, order_id=order.id, admin_user_id=str(ctx.user.id), context=override_context
            )
        commit_admin_audit(
            db,
            ctx,
            action="ops.admin.delivery_override" if override else "ops.admin.driver_action",
            resource_type="order",
            resource_id=order.id,
            payload={"action": action, "order_state": order.state, **override_context},
        )
        return {"ok": True, "order_id": order.id, "state": order.state, "action": action}

    def set_parcel_status(
        self,
        db: Session,
        ctx: AdminContext,
        order_id: str,
        parcel_id: str,
        status: str,
        tracking_suffix: str | None = None,
    ) -> dict[str, Any]:
        self._require_super_admin(ctx)
        order = self._order(db, order_id)
        parcel, previous = set_parcel_status(
            db, order, parcel_id, status, tracking_suffix=tracking_suffix
        )
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

    def add_proof(
        self, db: Session, settings: Settings, ctx: AdminContext, order_id: str, file_url: str
    ) -> dict[str, Any]:
        self._require_super_admin(ctx)
        order = self._order(db, order_id)
        driver = self._driver(db, order)
        from porterchain_driver.field_admin import record_proof_url

        record_proof_url(db, settings, driver, order, file_url)
        commit_admin_audit(
            db,
            ctx,
            action="ops.admin.proof_photo",
            resource_type="order",
            resource_id=order.id,
            payload={"file_url": file_url[:500]},
        )
        return {"ok": True, "order_id": order.id}

    def add_extra_stop(
        self,
        db: Session,
        settings: Settings,
        ctx: AdminContext,
        order_id: str,
        *,
        kind: str,
        formatted: str,
        amount_cents: int,
    ) -> dict[str, Any]:
        self._require_super_admin(ctx)
        order = self._order(db, order_id)
        state = (order.state or "").upper()
        if state not in _ROUTE_STATES:
            raise ValueError("Extra stops can be added only while the order is still on the road.")
        from porterchain_driver.field_admin import add_extra_stop as create_stop

        result = create_stop(
            db, settings, order, kind=kind, formatted=formatted, amount_cents=amount_cents
        )
        commit_admin_audit(
            db,
            ctx,
            action="ops.admin.extra_stop",
            resource_type="order",
            resource_id=order.id,
            payload=result,
        )
        return {"ok": True, **result}

    def resend_extra_stop(
        self, db: Session, ctx: AdminContext, order_id: str, leg: str
    ) -> dict[str, Any]:
        self._require_super_admin(ctx)
        order = self._order(db, order_id)
        from porterchain_driver.field_admin import resend_extra_stop_link

        result = resend_extra_stop_link(db, order, leg)
        commit_admin_audit(
            db,
            ctx,
            action="ops.admin.resend_stop_link",
            resource_type="order",
            resource_id=order.id,
            payload=result,
        )
        return {"ok": True, **result}

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
