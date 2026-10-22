"""Collect-only jobs: pick up and bring the parcel to OUR warehouse; delivery comes later.

Built on the warehouse split (``hub_legs``): at booking we write leg 0 (pickup -> hub) and a
*held* leg 1 (hub -> customer). The driver finishes leg 0 with the normal hub drop (GPS check,
no receiver code/photo, no out-for-delivery message). The order then sits PICKED_UP with no
driver at the hub: "At warehouse – awaiting delivery". It stays out of Plan the day until an
admin releases the delivery leg (``HubSplitService.release_delivery_leg``).

Pricing is the pickup leg only: the pricing engine quotes pickup -> warehouse, so contract
rates still win and HST stays extra (both inside the engine).
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

COLLECT_ONLY = "collect_only"
SERVICE_MODES = frozenset({"standard", COLLECT_ONLY})
AWAITING_LABEL = "At warehouse – awaiting delivery"


def is_collect_only(order: Any) -> bool:
    meta = order.compliance_metadata if isinstance(getattr(order, "compliance_metadata", None), dict) else {}
    return meta.get("service_mode") == COLLECT_ONLY


def warehouse(db: Session, hub_partner_id: str | None = None) -> Any:
    """The warehouse the parcel goes to: the one asked for, else the first active geocoded one."""
    from porterchain_api.dispatch_engine.models import LogisticsPartner

    q = db.query(LogisticsPartner).filter(
        LogisticsPartner.kind == "warehouse",
        LogisticsPartner.active.is_(True),
        LogisticsPartner.lat.isnot(None),
        LogisticsPartner.lng.isnot(None),
    )
    if hub_partner_id:
        q = q.filter(LogisticsPartner.id == hub_partner_id)
    hub = q.order_by(LogisticsPartner.name).first()
    if hub is None:
        raise ValueError("no_warehouse_for_collect_only")
    return hub


def pricing_dropoff(db: Session | None, body: Any) -> Any:
    """Collect-only quotes and bookings are priced pickup -> our warehouse; else None."""
    hub = for_booking(db, body) if db is not None else None
    return hub_geo(hub) if hub is not None else None


def for_booking(db: Session, body: Any) -> Any:
    """Warehouse for a collect-only booking, or None for a standard one."""
    if getattr(body, "service_mode", None) != COLLECT_ONLY:
        return None
    if getattr(body, "additional_stops", None):
        raise ValueError("collect_only_single_pickup")
    return warehouse(db)


def hub_geo(hub: Any) -> Any:
    from porterchain_pricing import GeoPoint

    return GeoPoint(lat=hub.lat, lng=hub.lng, formatted=hub.name)


def mark(compliance: dict[str, Any], hub: Any) -> dict[str, Any]:
    """Tag a collect-only order (no-op for a standard booking, ``hub=None``)."""
    if hub is None:
        return compliance
    compliance["service_mode"] = COLLECT_ONLY
    compliance["collect_only"] = {"hub_partner_id": hub.id, "hub_name": hub.name, "priced_to": "warehouse"}
    return compliance


def attach_legs(db: Session, order: Any, hub: Any, *, actor_type: str, actor_id: str | None) -> None:
    """Write leg 0 (pickup -> hub) and the held leg 1 (hub -> customer). No-op without a hub."""
    if hub is None:
        return
    from porterchain_api.booking_models import OrderEvent
    from porterchain_api.dispatch_engine.models import OrderLeg

    db.add(OrderLeg(
        order_id=order.id, seq=0, mode="local", partner_id=hub.id, from_label="pickup",
        to_label=hub.name[:64], status="planned",
        meta={"hub_split": True, "stop_kind": "hub", "to_lat": hub.lat, "to_lng": hub.lng,
              "hub_formatted": hub.name, "driver_id": None, "collect_only": True},
    ))
    db.add(OrderLeg(
        order_id=order.id, seq=1, mode="local", partner_id=hub.id, from_label=hub.name[:64],
        to_label="customer", status="planned",
        meta={"hub_split": True, "from_lat": hub.lat, "from_lng": hub.lng, "driver_id": None,
              "collect_only": True, "held": True},
    ))
    db.add(OrderEvent(order_id=order.id, event_type="order.collect_only_booked", from_state=order.state,
                      to_state=order.state, actor_type=actor_type, actor_id=actor_id,
                      payload={"hub_partner_id": hub.id}))


def delivery_leg(db: Session, order_id: str) -> Any:
    from porterchain_api.dispatch_engine.models import OrderLeg

    return (
        db.query(OrderLeg)
        .filter(OrderLeg.order_id == order_id, OrderLeg.mode == "local", OrderLeg.seq == 1)
        .first()
    )


def is_held(db: Session, order_id: str) -> bool:
    leg = delivery_leg(db, order_id)
    return bool(leg is not None and (leg.meta or {}).get("held"))


def awaiting_delivery(db: Session, order: Any) -> bool:
    """Parcel is in our warehouse and no delivery driver has it yet."""
    from porterchain_api.dispatch_engine.hub_legs import AT_HUB, hub_leg

    leg = hub_leg(db, order.id)
    return bool(leg is not None and leg.stage == AT_HUB and not order.assigned_driver_id)
