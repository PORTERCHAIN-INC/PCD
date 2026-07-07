"""Admin order management — extends shared OrderPlatformService (masterrule §3)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from porterchain_api.admin_engine.rbac import AdminContext
from porterchain_api.booking_engine.order_transitions import transition_order_state
from porterchain_api.config import Settings
from porterchain_api.domain.states import OrderState
from porterchain_api.models import Order
from porterchain_api.order_engine.filters import AdminOrderFilters, OrderFilters
from porterchain_api.order_engine.platform_service import OrderPlatformService

__all__ = ["AdminOrderFilters", "AdminOrdersService", "OrderFilters"]


class AdminOrdersService(OrderPlatformService):
    """Admin-scoped order platform — RBAC-gated overrides and bulk ops."""

    def force_transition(
        self,
        db: Session,
        ctx: AdminContext,
        order_id: str,
        to_state: str,
    ) -> Order:
        order = self.get_order(db, order_id)
        if not order:
            raise LookupError("order_not_found")
        return transition_order_state(
            db,
            order,
            OrderState(to_state),
            event_type="order.admin_override",
            actor_type="admin",
            actor_id=ctx.user.id,
            payload={"forced": True},
        )

    def bulk_action(
        self,
        db: Session,
        settings: Settings,
        ctx: AdminContext,
        order_ids: list[str],
        action: str,
        *,
        driver_id: str | None = None,
    ) -> list[dict[str, str]]:
        from porterchain_api.admin_engine.operations_service import AdminOperationsService

        ops = AdminOperationsService()
        results: list[dict[str, str]] = []
        for oid in order_ids:
            try:
                if action == "assign" and driver_id:
                    ops.assign_driver(db, settings, ctx, oid, driver_id)
                    results.append({"order_id": oid, "status": "assigned"})
                elif action == "cancel":
                    self.force_transition(db, ctx, oid, OrderState.CANCELLED.value)
                    results.append({"order_id": oid, "status": "cancelled"})
                else:
                    results.append({"order_id": oid, "status": "unsupported"})
            except Exception as exc:
                results.append({"order_id": oid, "status": f"error:{exc}"})
        return results
