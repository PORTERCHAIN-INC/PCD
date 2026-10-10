"""Failed-delivery policy: count attempts, offer a re-attempt, return to sender after N.

Off by default (``reattempt.enabled``); while off we only count attempts so the
tracking page can show them and ops keep handling FAILED orders exactly as today.
Every re-attempt / return leg is priced by the existing pricing engine (the
merchant's own pricing config, contract schedule included). Contract schedules
do not model failed-delivery or return fees yet, so we flag that instead of
inventing a fee.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.booking_models import Order, OrderEvent
from porterchain_api.customer_experience.context import (
    cx_meta,
    merchant_for,
    update_cx_meta,
)
from porterchain_api.customer_experience.settings import cx_for_merchant

logger = logging.getLogger(__name__)

DELIVERY_ATTEMPT_FROM_STATES = frozenset({"IN_TRANSIT", "AT_DESTINATION"})
CONTRACT_FLAG = "contract_failed_delivery_rules_not_modelled"


def price_leg(db: Session, order: Order, merchant: Any, *, leg: str) -> dict[str, Any]:
    """Quote a re-attempt (pickup -> drop-off again) or return (drop-off -> pickup)."""
    try:
        from porterchain_api.merchant_engine.booking_service import (
            MerchantBookingService,
        )
        from porterchain_api.merchant_engine.return_service import return_body
        from porterchain_api.pricing_engine import get_pricing_service

        body = return_body(order)  # drop-off -> original pickup, cargo from meta
        if leg == "reattempt":
            body = body.model_copy(update={"pickup": body.dropoff, "dropoff": body.pickup})
        ctx = SimpleNamespace(merchant=merchant)
        request = MerchantBookingService().build_pricing_request(ctx, body)
        breakdown = get_pricing_service(db).calculate_merchant(request)
        return {
            "leg": leg,
            "subtotal_cents": int(breakdown.subtotal_cents),
            "final_cents": int(breakdown.final_cents),
            "currency": "cad",
            "priced_at": datetime.now(UTC).isoformat(),
        }
    except Exception as exc:  # noqa: BLE001 — quote is advisory; never block the policy
        logger.warning("cx price_leg failed: %s", exc)
        return {"leg": leg, "error": "pricing_unavailable"}


def _latest_failure(db: Session, order: Order) -> OrderEvent | None:
    return (
        db.query(OrderEvent)
        .filter(OrderEvent.order_id == order.id, OrderEvent.to_state == "FAILED")
        .order_by(OrderEvent.occurred_at.desc())
        .first()
    )


def record_failure(db: Session, order: Order) -> dict[str, Any] | None:
    """Idempotent per FAILED transition. Returns the decision stored in meta ``cx.reattempt``."""
    if order.state != "FAILED":
        return None
    failure = _latest_failure(db, order)
    meta = cx_meta(order)
    if failure is not None and meta.get("last_failure_event") == failure.id:
        return meta.get("reattempt")
    from_state = str(getattr(failure, "from_state", "") or "")
    counted = from_state in DELIVERY_ATTEMPT_FROM_STATES or failure is None
    attempts = int(meta.get("attempts") or 0) + (1 if counted else 0)

    merchant = merchant_for(db, order)
    policy = cx_for_merchant(merchant)["reattempt"]
    decision: dict[str, Any] = {
        "attempts": attempts,
        "max_attempts": policy["max_attempts"],
        "return_to_sender_after": policy["return_to_sender_after"],
        "policy_enabled": policy["enabled"],
        "action": "manual",
        "flags": [],
        "decided_at": datetime.now(UTC).isoformat(),
    }
    from porterchain_api.merchant_engine.return_service import has_contract_schedule

    if has_contract_schedule(merchant):
        decision["flags"].append(CONTRACT_FLAG)

    if policy["enabled"] and counted:
        if attempts >= policy["return_to_sender_after"]:
            decision["action"] = "return_to_sender"
            decision["quote"] = price_leg(db, order, merchant, leg="return_to_sender")
        elif attempts < policy["max_attempts"]:
            decision["action"] = "reattempt"
            decision["quote"] = price_leg(db, order, merchant, leg="reattempt")

    update_cx_meta(
        order,
        attempts=attempts,
        reattempt=decision,
        last_failure_event=failure.id if failure is not None else None,
    )
    db.flush()
    if decision["action"] == "return_to_sender":
        from porterchain_api.booking_engine.order_transitions import (
            transition_order_state,
        )
        from porterchain_api.domain.states import OrderState

        transition_order_state(
            db,
            order,
            OrderState.RETURN_TO_SENDER,
            event_type="order.return_to_sender",
            actor_type="system",
            payload={"reason": "max_delivery_attempts", "attempts": attempts},
        )
    return decision


def reattempt_allowed(order: Order) -> bool:
    """Recipient may pick a new window for a FAILED order when the policy says re-attempt."""
    decision = cx_meta(order).get("reattempt")
    return order.state == "FAILED" and isinstance(decision, dict) and decision.get("action") == "reattempt"
