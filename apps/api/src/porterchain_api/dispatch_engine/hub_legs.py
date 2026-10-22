"""Hub split: an order's pickup and delivery as two local legs with a warehouse in between.

Leg 0 (``seq=0``): pickup address -> hub, own driver ("pickup only to our warehouse").
Leg 1 (``seq=1``): hub -> customer, own driver ("delivery only from our warehouse").

Stored on the existing ``order_legs`` table (mode ``local``, ``meta.hub_split=True``): no schema
change. The order state machine is untouched: the parcel is PICKED_UP from the first scan at the
pickup until the final delivery; ``stage`` says where it is in between.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

TO_HUB = "to_hub"  # leg 0 open: the van drops at the hub, not at the customer
AT_HUB = "at_hub"  # leg 0 done, leg 1 open: parcel waits at / leaves from the hub
OPEN = ("planned", "requested", "accepted", "picked_up")


@dataclass
class HubLeg:
    stage: str
    hub: dict[str, Any]  # {formatted, lat, lng, name, partner_id}
    first: Any
    second: Any

    @property
    def arrived_at_hub(self) -> bool:
        return bool((self.first.meta or {}).get("hub_arrived_at"))

    @property
    def delivery_driver_id(self) -> str | None:
        return (self.second.meta or {}).get("driver_id") or None


def _hub_point(leg: Any) -> dict[str, Any]:
    m = leg.meta or {}
    return {
        "formatted": m.get("hub_formatted") or leg.to_label,
        "lat": m.get("to_lat"),
        "lng": m.get("to_lng"),
        "name": leg.to_label,
        "partner_id": leg.partner_id,
        "hub": True,
    }


def hub_leg(db: Session | None, order_id: str) -> HubLeg | None:
    """The order's open hub split, or None (no split, or both legs finished/cancelled)."""
    if db is None:
        return None
    from porterchain_api.dispatch_engine.models import OrderLeg

    rows = (
        db.query(OrderLeg)
        .filter(OrderLeg.order_id == order_id, OrderLeg.mode == "local")
        .order_by(OrderLeg.seq)
        .all()
    )
    rows = [r for r in rows if (r.meta or {}).get("hub_split")]
    if len(rows) < 2:
        return None
    first, second = rows[0], rows[1]
    if first.status in OPEN:
        return HubLeg(TO_HUB, _hub_point(first), first, second)
    if first.status == "delivered" and second.status in OPEN:
        return HubLeg(AT_HUB, _hub_point(first), first, second)
    return None


def _touch(leg: Any, **meta: Any) -> None:
    data = copy.deepcopy(leg.meta or {})
    data.update({k: v for k, v in meta.items()})
    leg.meta = data  # copy-on-write so SQLAlchemy sees the JSON change


def mark_hub_arrived(leg: HubLeg, driver_id: str) -> None:
    _touch(leg.first, hub_arrived_at=datetime.now(UTC).isoformat(), hub_arrived_by=driver_id)


def mark_hub_received(leg: HubLeg, driver_id: str) -> None:
    now = datetime.now(UTC).isoformat()
    leg.first.status = "delivered"
    _touch(leg.first, hub_received_at=now, hub_received_by=driver_id)


def mark_delivered(leg: HubLeg) -> None:
    leg.second.status = "delivered"
    _touch(leg.second, delivered_at=datetime.now(UTC).isoformat())


def set_delivery_driver(leg: HubLeg, driver_id: str | None) -> None:
    _touch(leg.second, driver_id=driver_id)


def hub_note(leg: HubLeg) -> str:
    where = leg.hub.get("name") or "hub"
    addr = leg.hub.get("formatted") or ""
    if leg.stage == TO_HUB:
        return f"DROP AT HUB {where} ({addr}) — not to the customer."
    return f"Collect from hub {where} ({addr}) first."


def parcel_position(db: Session, order: Any, *, max_age_h: int = 12) -> dict[str, Any] | None:
    """Where a picked-up parcel is now: last GPS ping of the driver who picked it up.

    Used when a picked-up, unsplit order lost its driver (removed / off shift): Plan the day
    starts from the parcel, not from the original pickup. None when unknown or stale.
    """
    from datetime import timedelta

    from porterchain_api.driver_models import DriverLocationPing, DriverStopMeta

    meta = db.query(DriverStopMeta).filter(DriverStopMeta.order_id == order.id).first()
    if meta is None or not meta.driver_id:
        return None
    since = datetime.now(UTC) - timedelta(hours=max_age_h)
    ping = (
        db.query(DriverLocationPing)
        .filter(DriverLocationPing.driver_id == meta.driver_id, DriverLocationPing.created_at >= since)
        .order_by(DriverLocationPing.created_at.desc())
        .first()
    )
    if ping is None:
        return None
    return {"lat": float(ping.lat), "lng": float(ping.lng), "formatted": "Parcel (last driver position)",
            "kind": "parcel", "driver_id": meta.driver_id}


class _PlanView:  # read-only view; never mutates the ORM row
    pass


def _view(order: Any, **override: Any) -> Any:
    v = _PlanView()
    for attr in ("id", "pickup", "dropoff", "order_type", "state", "compliance_metadata"):
        setattr(v, attr, getattr(order, attr))
    for k, val in override.items():
        setattr(v, k, val)
    return v


def planning_view(db: Session, order: Any, *, awaiting_state: str = "PICKED_UP") -> Any:
    """Order as Plan the day should see it.

    - first open leg ends at a warehouse/partner → drop is that hub;
    - parcel sits at our hub (delivery leg) → pickup is the hub;
    - picked up, not split, no driver now → pickup is the parcel's last known position.
    """
    from porterchain_api.dispatch_engine.models import OrderLeg

    leg = (
        db.query(OrderLeg)
        .filter(OrderLeg.order_id == order.id, OrderLeg.status.in_(("planned", "requested", "accepted")))
        .order_by(OrderLeg.seq)
        .first()
    )
    meta = (leg.meta or {}) if leg is not None else {}
    if leg is None or leg.mode != "local":
        if order.state == awaiting_state and not order.assigned_driver_id:
            here = parcel_position(db, order)
            if here is not None:
                return _view(order, pickup=here)
        return order
    at_hub = meta.get("from_lat") is not None and order.state == awaiting_state
    if meta.get("to_lat") is None and not at_hub:
        return order
    if at_hub:  # delivery leg of a warehouse split: the van collects at the hub
        return _view(order, pickup={"lat": meta["from_lat"], "lng": meta["from_lng"],
                                    "formatted": leg.from_label, "kind": "hub", "partner_id": leg.partner_id})
    return _view(order, dropoff={"lat": meta["to_lat"], "lng": meta["to_lng"], "formatted": leg.to_label,
                                 "kind": meta.get("stop_kind", "hub"), "partner_id": leg.partner_id})
