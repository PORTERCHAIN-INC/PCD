"""Public, privacy-safe tracking "experience" payload for /track/{number}.

Never returns parcel contents, street addresses, driver surname/phone or the
receiver's identity. Proof photos are only exposed with a valid signed link and
when the merchant enables ``tracking.show_pod_photo``.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.booking_models import Order, OrderEvent
from porterchain_api.customer_experience.context import (
    DELIVERED_STATES,
    PRE_DISPATCH_STATES,
    TERMINAL_STATES,
    cx_meta,
    dest_fsa,
    mask_initials,
    mask_name,
    merchant_for,
)
from porterchain_api.customer_experience.settings import brand_colours, cx_for_merchant

STEPS: tuple[str, ...] = ("booked", "picked_up", "out_for_delivery", "delivered")
_STEP_FOR_STATE: dict[str, str] = {
    "BOOKED": "booked",
    "DISPATCH_READY": "booked",
    "PICKED_UP": "picked_up",
    "IN_TRANSIT": "out_for_delivery",
    "AT_DESTINATION": "nearby",
    "DELIVERED": "delivered",
    "POD_COMPLETED": "delivered",
    "FAILED": "attempted",
    "RETURN_TO_SENDER": "returning",
    "CANCELLED": "cancelled",
}
_LABELS: dict[str, str] = {
    "booked": "Order received",
    "picked_up": "Picked up",
    "out_for_delivery": "Out for delivery",
    "nearby": "Driver has arrived",
    "delivered": "Delivered",
    "attempted": "Delivery attempted",
    "returning": "Returning to sender",
    "cancelled": "Cancelled",
    "rescheduled": "Delivery rescheduled",
    "instructions": "Delivery instructions updated",
}
_REPEATABLE = {"attempted", "rescheduled", "instructions"}


def _iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return (dt if dt.tzinfo else dt.replace(tzinfo=UTC)).isoformat()


def build_timeline(db: Session, order: Order) -> list[dict[str, Any]]:
    events = (
        db.query(OrderEvent)
        .filter(OrderEvent.order_id == order.id)
        .order_by(OrderEvent.occurred_at.asc())
        .all()
    )
    items: list[dict[str, Any]] = []
    seen: set[str] = set()
    for ev in events:
        code = _STEP_FOR_STATE.get(str(ev.to_state or ""))
        if not code or (code in seen and code not in _REPEATABLE):
            continue
        seen.add(code)
        items.append({"code": code, "label": _LABELS[code], "at": _iso(ev.occurred_at)})
    if "booked" not in seen:
        items.insert(0, {"code": "booked", "label": _LABELS["booked"], "at": _iso(order.created_at)})
    for entry in cx_meta(order).get("history") or []:
        if isinstance(entry, dict) and entry.get("code") in _LABELS:
            items.append({"code": entry["code"], "label": _LABELS[entry["code"]], "at": entry.get("at")})
    items.sort(key=lambda i: i.get("at") or "")
    return items


def _progress(order: Order) -> list[dict[str, Any]]:
    state = order.state
    if state in DELIVERED_STATES:
        reached = 3
    elif state in {"IN_TRANSIT", "AT_DESTINATION"}:
        reached = 2
    elif state == "PICKED_UP":
        reached = 1
    else:
        reached = 0
    return [{"code": s, "label": _LABELS[s], "done": i <= reached} for i, s in enumerate(STEPS)]


def eta_window(db: Session, order: Order) -> dict[str, Any] | None:
    chosen = cx_meta(order).get("schedule")
    if isinstance(chosen, dict) and chosen.get("window_start"):
        return {
            "start": chosen.get("window_start"),
            "end": chosen.get("window_end"),
            "label": chosen.get("label"),
            "source": "customer",
        }
    if order.state in DELIVERED_STATES or order.state in TERMINAL_STATES:
        return None
    from porterchain_api.platform.delivery_promise import checkout_promise

    promise = checkout_promise(db, dest_fsa=dest_fsa(order), now=order.created_at or datetime.now(UTC))
    if promise is not None:
        data = promise.as_dict()
        return {
            "start": data["window_start"],
            "end": data["window_end"],
            "label": data["description"],
            "source": "promise",
        }
    if order.scheduled_at:
        return {"start": _iso(order.scheduled_at), "end": None, "label": None, "source": "booking"}
    return None


def _driver(db: Session, order: Order, cfg: dict[str, Any]) -> dict[str, Any] | None:
    if not order.assigned_driver_id or order.state in PRE_DISPATCH_STATES or order.state in TERMINAL_STATES:
        return None
    if not cfg["tracking"]["show_driver_first_name"]:
        return {"name": None}
    from porterchain_api.admin_models import Driver

    driver = db.get(Driver, order.assigned_driver_id)
    return {"name": mask_name(getattr(driver, "full_name", None))}


def _stop_meta(db: Session, order: Order) -> dict[str, Any]:
    from porterchain_api.driver_models import DriverStopMeta

    row = db.query(DriverStopMeta).filter(DriverStopMeta.order_id == order.id).first()
    return row.meta if row is not None and isinstance(row.meta, dict) else {}


def proof_of_delivery(db: Session, order: Order, cfg: dict[str, Any], *, with_photos: bool) -> dict[str, Any] | None:
    if order.state not in DELIVERED_STATES:
        return None
    delivered = (
        db.query(OrderEvent)
        .filter(OrderEvent.order_id == order.id, OrderEvent.to_state == "DELIVERED")
        .order_by(OrderEvent.occurred_at.asc())
        .first()
    )
    meta = _stop_meta(db, order)
    proofs = [p for p in meta.get("proofs") or [] if isinstance(p, dict)]
    kinds = sorted({str(p.get("type") or "") for p in proofs} - {""})
    out: dict[str, Any] = {
        "delivered_at": _iso(delivered.occurred_at) if delivered else None,
        "proof_types": kinds,
        "received_by": mask_initials(meta.get("received_by") or meta.get("recipient_name")),
        "photos": [],
    }
    if with_photos and cfg["tracking"]["show_pod_photo"]:
        out["photos"] = [
            str(p.get("value"))
            for p in proofs
            if p.get("type") == "photo" and str(p.get("value") or "").startswith("https://")
        ][:4]
    return out


def build_experience(db: Session, order: Order, *, with_photos: bool = False) -> dict[str, Any]:
    merchant = merchant_for(db, order)
    cfg = cx_for_merchant(merchant)
    if not cfg["tracking"]["branded_page"]:
        # Off by default: the public page keeps rendering exactly as before.
        return {"enhanced": False, "tracking_number": order.tracking_number}
    from porterchain_api.customer_experience.route_position import stops_ahead
    from porterchain_api.merchant_engine.organization_sync import public_shipper_branding

    meta = cx_meta(order)
    rules = cfg["delivery_rules"]
    branding = {**public_shipper_branding(merchant), **brand_colours(merchant)}
    return {
        "enhanced": True,
        "tracking_number": order.tracking_number,
        "state": order.state,
        "branding": branding,
        "progress": _progress(order),
        "timeline": build_timeline(db, order),
        "eta_window": eta_window(db, order),
        "stops_away": stops_ahead(db, order) if cfg["tracking"]["show_stops_away"] else None,
        "driver": _driver(db, order, cfg),
        "proof_of_delivery": proof_of_delivery(db, order, cfg, with_photos=with_photos),
        "attempts": int(meta.get("attempts") or 0),
        "awaiting_schedule": bool(meta.get("awaiting_schedule")),
        "returning_to_sender": order.state == "RETURN_TO_SENDER",
        "help": {
            "email": cfg["tracking"]["support_email"],
            "phone": cfg["tracking"]["support_phone"],
            "url": cfg["tracking"]["help_url"],
        },
        "self_service": {
            "available": bool(cfg["self_service"]["enabled"]) and order.state not in TERMINAL_STATES,
        },
        "rules": {
            "id_required": rules["id_required"],
            "signature_required": rules["signature_required"],
            "safe_place_allowed": rules["safe_place_allowed"],
        },
        "generated_at": datetime.now(UTC).isoformat(),
    }
