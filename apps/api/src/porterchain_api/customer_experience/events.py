"""Domain-event hook: drives recipient notifications and the failed-delivery policy.

Called from ``notification_engine.event_router.handle_domain_event`` (event-bus
consumer). Never raises; sandbox orders are ignored. Queue-only (see notifications).
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.booking_models import Order
from porterchain_api.customer_experience.context import DELIVERED_STATES

logger = logging.getLogger(__name__)

#: Events after which the driver's remaining stops should be re-counted.
RUN_EVENTS = frozenset(
    {
        "order.in_transit",
        "order.stop_completed",
        "order.delivered",
        "order.pod_completed",
        "order.failed",
        "order.delivery_failed",
    }
)
ETA_EVENTS = frozenset({"order.near_delivery", "order.tracking_updated"})
RESCHEDULE_EVENTS = frozenset({"order.rescheduled"})
CX_EVENTS = RUN_EVENTS | ETA_EVENTS | RESCHEDULE_EVENTS


def _eta_minutes(payload: dict[str, Any]) -> float | None:
    for key, scale in (("eta_minutes", 1.0), ("eta_seconds", 1 / 60), ("duration_seconds", 1 / 60)):
        value = payload.get(key)
        if value is None and isinstance(payload.get("eta"), dict):
            value = payload["eta"].get(key)
        try:
            if value is not None:
                return float(value) * scale
        except (TypeError, ValueError):
            continue
    return None


def eta_payload_is_close(payload: dict[str, Any], limit_minutes: int = 120) -> bool:
    """Cheap pre-check (no DB) so frequent GPS pings are dropped early."""
    minutes = _eta_minutes(payload)
    return minutes is not None and minutes <= limit_minutes


def process_order_event(db: Session, settings: Any, event_type: str, payload: dict[str, Any]) -> list[dict[str, Any]]:
    from porterchain_api.customer_experience.notifications import notify
    from porterchain_api.customer_experience.reattempt import record_failure
    from porterchain_api.customer_experience.route_position import driver_run, stops_ahead
    from porterchain_api.customer_experience.settings import cx_for_merchant
    from porterchain_api.customer_experience.context import merchant_for

    order_id = payload.get("order_id")
    if event_type not in CX_EVENTS or not order_id:
        return []
    order = db.get(Order, order_id)
    if order is None or order.is_sandbox:
        return []
    results: list[dict[str, Any]] = []
    cfg = cx_for_merchant(merchant_for(db, order))

    if event_type in RESCHEDULE_EVENTS:
        label = str(payload.get("window_label") or "")
        stamp = f"rescheduled:{payload.get('window_code') or label}"
        results.append(notify(db, settings, order, "rescheduled", extra={"window_label": label}, dedupe_key=stamp))
        db.commit()
        return results

    if event_type in ETA_EVENTS:
        minutes = _eta_minutes(payload)
        limit = cfg["notifications"]["eta_minutes"]
        if event_type == "order.near_delivery" or (minutes is not None and minutes <= limit):
            extra = {"eta_minutes": int(round(minutes)) if minutes is not None else limit}
            results.append(notify(db, settings, order, "eta_20", extra=extra))
        db.commit()
        return results

    just_out = False
    if order.state == "IN_TRANSIT" and event_type == "order.in_transit":
        res = notify(db, settings, order, "out_for_delivery")
        just_out = bool(res["queued"])
        results.append(res)
    elif order.state in DELIVERED_STATES:
        results.append(notify(db, settings, order, "delivered"))
    elif order.state == "FAILED":
        decision = record_failure(db, order) or {}
        db.refresh(order)
        attempts = int(decision.get("attempts") or 0)
        results.append(notify(db, settings, order, "attempted", dedupe_key=f"attempted:{attempts}"))
    db.commit()

    if order.assigned_driver_id:
        threshold = cfg["notifications"]["next_stop_threshold"]
        run = driver_run(db, order.assigned_driver_id)
        for other in run:
            # The order that just went out gets "out for delivery", never also "next stop"
            # (a redelivered in_transit event used to send a stray next-stop email).
            if (just_out or event_type == "order.in_transit") and other.id == order.id:
                continue
            ahead = stops_ahead(db, other, run=run)
            if ahead is not None and ahead <= threshold:
                results.append(notify(db, settings, other, "next_stop", extra={"stops_away": ahead}))
        db.commit()
    return results


def run_cx_hooks(db: Session, event_type: str, payload: dict[str, Any]) -> None:
    if event_type not in CX_EVENTS or payload.get("is_sandbox") is True:
        return
    try:
        from porterchain_api.config import get_settings

        process_order_event(db, get_settings(), event_type, payload)
    except Exception as exc:  # noqa: BLE001 — never break the notification router
        logger.warning("customer-experience hook failed for %s: %s", event_type, exc)
        db.rollback()
