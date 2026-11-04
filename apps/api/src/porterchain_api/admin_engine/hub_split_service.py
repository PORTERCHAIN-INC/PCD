"""Split an order at a partner warehouse (hub) and release its delivery leg — admin side.

Split from ``logistics_partners_service`` (ENG-G2 ≤500 LOC).
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session


# ---------------------------------------------------------------- split at warehouse
# Before pickup (any driver state) or picked up but not yet out for delivery.
SPLITTABLE = frozenset({
    "BOOKED", "DISPATCH_READY", "DRIVER_REJECTED", "DRIVER_ASSIGNED", "DRIVER_ACCEPTED",
    "DRIVER_EN_ROUTE", "AT_PICKUP", "PICKED_UP",
})


class HubSplitService:
    def split(
        self,
        db: Session,
        settings: Any,
        ctx: Any,
        order_id: str,
        *,
        hub_partner_id: str,
        pickup_driver_id: str | None = None,
        delivery_driver_id: str | None = None,
    ) -> dict[str, Any]:
        from porterchain_api.admin_engine.operations_service import AdminOperationsService
        from porterchain_api.admin_models import AdminAuditLog
        from porterchain_api.booking_models import Order, OrderEvent
        from porterchain_api.platform.engine_ports.dispatch_engine__hub_legs import hub_leg
        from porterchain_api.platform.engine_ports.dispatch_engine__models import LogisticsPartner, OrderLeg
        from porterchain_api.domain.sandbox import order_is_sandbox

        order = db.get(Order, order_id)
        if order is None:
            raise LookupError("order_not_found")
        if order_is_sandbox(order):
            raise ValueError("sandbox_orders_block_live_assign")
        if order.state not in SPLITTABLE:
            raise ValueError("split_not_allowed_in_state")
        if hub_leg(db, order.id) is not None:
            raise ValueError("already_split")
        hub = db.get(LogisticsPartner, hub_partner_id)
        if hub is None or hub.kind != "warehouse" or not hub.active:
            raise LookupError("hub_not_found")
        if hub.lat is None or hub.lng is None:
            raise ValueError("hub_not_geocoded")

        # Replace any still-planned local legs (rules planner output) with the split.
        db.query(OrderLeg).filter(
            OrderLeg.order_id == order.id, OrderLeg.status == "planned", OrderLeg.mode == "local"
        ).delete(synchronize_session=False)
        picked = order.state == "PICKED_UP"
        first_driver = pickup_driver_id or (order.assigned_driver_id if picked else None)
        db.add(OrderLeg(
            order_id=order.id, seq=0, mode="local", partner_id=hub.id, from_label="pickup",
            to_label=hub.name[:64], status="picked_up" if picked else "planned",
            meta={"hub_split": True, "stop_kind": "hub", "to_lat": hub.lat, "to_lng": hub.lng,
                  "hub_formatted": hub.name, "driver_id": first_driver},
        ))
        db.add(OrderLeg(
            order_id=order.id, seq=1, mode="local", partner_id=hub.id, from_label=hub.name[:64],
            to_label="customer", status="planned",
            meta={"hub_split": True, "from_lat": hub.lat, "from_lng": hub.lng,
                  "driver_id": delivery_driver_id},
        ))
        db.add(OrderEvent(order_id=order.id, event_type="order.hub_split", from_state=order.state,
                          to_state=order.state, actor_type="admin", actor_id=ctx.user.id,
                          payload={"hub_partner_id": hub.id, "pickup_driver_id": first_driver,
                                   "delivery_driver_id": delivery_driver_id}))
        db.add(AdminAuditLog(actor_user_id=ctx.user.id, action="dispatch.hub_split", resource_type="order",
                             resource_id=order.id,
                             payload={"hub_partner_id": hub.id, "state": order.state,
                                      "pickup_driver_id": first_driver,
                                      "delivery_driver_id": delivery_driver_id}))
        db.commit()
        if pickup_driver_id and pickup_driver_id != order.assigned_driver_id:
            AdminOperationsService().assign_driver(db, settings, ctx, order.id, pickup_driver_id)
        return self.view(db, order.id)

    def release_delivery_leg(self, db: Session, settings: Any, ctx: Any, order_id: str, *,
                             driver_id: str | None = None) -> dict[str, Any]:
        """Collect-only / warehouse parcel: create (unhold) the delivery leg so Plan the day sees it.

        With ``driver_id`` the van is assigned now (parcel at the hub) or booked for after the drop.
        """
        import copy

        from porterchain_api.admin_engine.operations_service import AdminOperationsService
        from porterchain_api.admin_models import AdminAuditLog
        from porterchain_api.booking_models import Order, OrderEvent
        from porterchain_api.platform.engine_ports.dispatch_engine__hub_legs import hub_leg, set_delivery_driver
        from porterchain_api.services import collect_only as co

        order = db.get(Order, order_id)
        if order is None:
            raise LookupError("order_not_found")
        leg = co.delivery_leg(db, order_id)
        if leg is None or not (leg.meta or {}).get("hub_split"):
            raise ValueError("not_a_warehouse_order")
        if leg.status not in ("planned", "requested", "accepted"):
            raise ValueError("delivery_leg_closed")
        meta = copy.deepcopy(leg.meta or {})
        was_held = bool(meta.pop("held", False))
        leg.meta = meta
        db.add(OrderEvent(order_id=order.id, event_type="order.delivery_leg_released", from_state=order.state,
                          to_state=order.state, actor_type="admin", actor_id=ctx.user.id,
                          payload={"driver_id": driver_id, "was_held": was_held}))
        db.add(AdminAuditLog(actor_user_id=ctx.user.id, action="dispatch.delivery_leg_release",
                             resource_type="order", resource_id=order.id,
                             payload={"driver_id": driver_id, "state": order.state}))
        db.commit()
        if driver_id and co.awaiting_delivery(db, order):
            AdminOperationsService().assign_driver(db, settings, ctx, order.id, driver_id)
        elif driver_id and (hl := hub_leg(db, order.id)) is not None:
            set_delivery_driver(hl, driver_id)  # still on the way to the hub
            db.commit()
        return {"order_id": order.id, "released": True, "held": False}

    def view(self, db: Session, order_id: str) -> dict[str, Any]:
        from porterchain_api.platform.engine_ports.dispatch_engine__hub_legs import hub_leg

        leg = hub_leg(db, order_id)
        if leg is None:
            return {"order_id": order_id, "split": False}
        from porterchain_api.booking_models import Order
        from porterchain_api.services import collect_only as co

        order = db.get(Order, order_id)
        held = co.is_held(db, order_id)
        waiting = order is not None and co.awaiting_delivery(db, order)
        return {
            "order_id": order_id,
            "split": True,
            "collect_only": bool(order is not None and co.is_collect_only(order)),
            "delivery_held": held,
            "awaiting_delivery": waiting,
            "status_label": co.AWAITING_LABEL if waiting else None,
            "stage": leg.stage,
            "hub": leg.hub,
            "pickup_driver_id": (leg.first.meta or {}).get("driver_id"),
            "delivery_driver_id": leg.delivery_driver_id,
            "arrived_at_hub": leg.arrived_at_hub,
        }
