"""Recipient self-scheduling, reschedule, delivery instructions and the bulky gate."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.booking_models import Order
from porterchain_api.config import Settings
from porterchain_api.customer_experience.context import (
    TERMINAL_STATES,
    cx_meta,
    dest_fsa,
    is_bulky,
    merchant_for,
    update_cx_meta,
)
from porterchain_api.customer_experience.reattempt import reattempt_allowed
from porterchain_api.customer_experience.settings import cx_for_merchant

RESCHEDULABLE_STATES = frozenset({"BOOKED", "DISPATCH_READY"})
INSTRUCTION_FIELDS = ("gate_code", "buzzer", "safe_place", "notes")
_RECIPIENT_TAG = "[Recipient]"


def available(db: Session, order: Order, cfg: dict[str, Any], *, now: datetime | None = None) -> list[dict[str, Any]]:
    from porterchain_api.platform.delivery_promise import load_delivery_promise_config
    from porterchain_pricing.delivery_promise import available_windows

    return available_windows(
        load_delivery_promise_config(db),
        now=now or datetime.now(UTC),
        days=cfg["self_service"]["schedule_days"],
        dest_fsa=dest_fsa(order),
    )


def can_reschedule(order: Order, cfg: dict[str, Any]) -> bool:
    if not (cfg["self_service"]["enabled"] and cfg["self_service"]["allow_reschedule"]):
        return False
    return order.state in RESCHEDULABLE_STATES or reattempt_allowed(order)


def can_edit_instructions(order: Order, cfg: dict[str, Any]) -> bool:
    return (
        cfg["self_service"]["enabled"]
        and cfg["self_service"]["allow_instructions"]
        and order.state not in TERMINAL_STATES
    )


def options(db: Session, order: Order, *, now: datetime | None = None) -> dict[str, Any]:
    cfg = cx_for_merchant(merchant_for(db, order))
    if not cfg["self_service"]["enabled"]:
        raise ValueError("self_service_disabled")
    meta = cx_meta(order)
    resched = can_reschedule(order, cfg)
    rules = cfg["delivery_rules"]
    return {
        "tracking_number": order.tracking_number,
        "state": order.state,
        "can_reschedule": resched,
        "can_edit_instructions": can_edit_instructions(order, cfg),
        "awaiting_schedule": bool(meta.get("awaiting_schedule")),
        "windows": available(db, order, cfg, now=now) if resched else [],
        "schedule": meta.get("schedule"),
        "instructions": meta.get("instructions") or {},
        "rules": {
            "safe_place_allowed": rules["safe_place_allowed"],
            "id_required": rules["id_required"],
            "signature_required": rules["signature_required"],
        },
        "attempts": int(meta.get("attempts") or 0),
    }


def _history(order: Order, code: str, now: datetime) -> list[dict[str, Any]]:
    rows = [r for r in cx_meta(order).get("history") or [] if isinstance(r, dict)]
    rows.append({"code": code, "at": now.isoformat()})
    return rows[-20:]


def choose_window(db: Session, order: Order, code: str, *, now: datetime | None = None) -> dict[str, Any]:
    now = now or datetime.now(UTC)
    cfg = cx_for_merchant(merchant_for(db, order))
    if not cfg["self_service"]["enabled"]:
        raise ValueError("self_service_disabled")
    if not can_reschedule(order, cfg):
        raise ValueError("reschedule_closed")
    window = next((w for w in available(db, order, cfg, now=now) if w["code"] == code), None)
    if window is None:
        raise ValueError("window_unavailable")
    meta = cx_meta(order)
    was_awaiting = bool(meta.get("awaiting_schedule"))
    was_failed = order.state == "FAILED"
    update_cx_meta(
        order,
        schedule={**window, "chosen_at": now.isoformat(), "source": "recipient"},
        history=_history(order, "rescheduled", now),
        awaiting_schedule=None,
    )
    order.scheduled_at = datetime.fromisoformat(window["window_start"])
    db.commit()
    from porterchain_api.booking_engine.order_transitions import transition_order_state, transition_to_dispatch_ready
    from porterchain_api.domain.states import OrderState

    if was_failed:
        transition_order_state(
            db,
            order,
            OrderState.DISPATCH_READY,
            event_type="order.reattempt_scheduled",
            actor_type="consignee",
            payload={"window": window["code"]},
        )
    elif was_awaiting and order.state == "BOOKED":
        transition_to_dispatch_ready(
            db,
            order,
            event_type="order.dispatch_ready",
            actor_type="consignee",
            payload={"window": window["code"], "reason": "recipient_scheduled"},
        )
    _emit_rescheduled(db, order, window, was_failed=was_failed)
    db.commit()
    db.refresh(order)
    return options(db, order, now=now)


def _emit_rescheduled(db: Session, order: Order, window: dict[str, Any], *, was_failed: bool) -> None:
    """One event every persona's notice hangs off (receiver, merchant, admin, driver)."""
    from porterchain_api.booking_engine._core import emit_event

    emit_event(
        db,
        event_type="order.rescheduled",
        aggregate_type="order",
        aggregate_id=order.id,
        payload={
            "order_id": order.id,
            "order_number": order.order_number,
            "tracking_number": order.tracking_number,
            "merchant_id": order.merchant_id,
            "customer_id": order.customer_id,
            "driver_id": order.assigned_driver_id,
            "window_code": window.get("code"),
            "window_label": window.get("label"),
            "after_failed_attempt": was_failed,
            "actor_type": "consignee",
        },
    )


def _clean(value: Any, limit: int) -> str | None:
    text = " ".join(str(value or "").split())[:limit]
    return text or None


def set_instructions(db: Session, order: Order, body: dict[str, Any], *, now: datetime | None = None) -> dict[str, Any]:
    now = now or datetime.now(UTC)
    cfg = cx_for_merchant(merchant_for(db, order))
    if not cfg["self_service"]["enabled"]:
        raise ValueError("self_service_disabled")
    if not can_edit_instructions(order, cfg):
        raise ValueError("instructions_closed")
    clean = {
        "gate_code": _clean(body.get("gate_code"), 32),
        "buzzer": _clean(body.get("buzzer"), 32),
        "safe_place": _clean(body.get("safe_place"), 120),
        "notes": _clean(body.get("notes"), 280),
    }
    if clean["safe_place"] and not cfg["delivery_rules"]["safe_place_allowed"]:
        raise ValueError("safe_place_not_allowed")
    stored = {k: v for k, v in clean.items() if v}
    update_cx_meta(
        order,
        instructions={**stored, "updated_at": now.isoformat()} if stored else None,
        history=_history(order, "instructions", now),
    )
    # Drivers read special_instructions: keep one recipient line, replaced on every edit.
    lines = [ln for ln in str(order.special_instructions or "").splitlines() if not ln.startswith(_RECIPIENT_TAG)]
    if stored:
        parts = []
        if stored.get("gate_code"):
            parts.append(f"gate code {stored['gate_code']}")
        if stored.get("buzzer"):
            parts.append(f"buzzer {stored['buzzer']}")
        if stored.get("safe_place"):
            parts.append(f"safe place: {stored['safe_place']}")
        if stored.get("notes"):
            parts.append(stored["notes"])
        lines.append(f"{_RECIPIENT_TAG} " + "; ".join(parts))
    order.special_instructions = "\n".join(lines) or None
    db.commit()
    db.refresh(order)
    return options(db, order, now=now)


def hold_for_schedule(db: Session, settings: Settings, order: Order) -> bool:
    """Bulky gate at booking: keep the order at BOOKED until the recipient picks a window."""
    cfg = cx_for_merchant(merchant_for(db, order))
    rules = cfg["delivery_rules"]
    if not (rules["require_schedule_for_bulky"] and cfg["self_service"]["enabled"]):
        return False
    if order.is_sandbox or order.state != "BOOKED" or not is_bulky(order, rules):
        return False
    if isinstance(cx_meta(order).get("schedule"), dict):
        return False
    update_cx_meta(order, awaiting_schedule=True)
    db.commit()
    from porterchain_api.customer_experience.notifications import notify

    notify(db, settings, order, "schedule_request")
    db.commit()
    return True
