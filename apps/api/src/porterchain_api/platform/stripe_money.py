"""Stripe money façade (refunds/disputes/payouts) for the webhook and admin routers."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

REFUND_EVENTS = frozenset({"charge.refunded", "charge.refund.updated"})
DISPUTE_EVENTS = frozenset(
    {
        "charge.dispute.created",
        "charge.dispute.updated",
        "charge.dispute.closed",
        "charge.dispute.funds_withdrawn",
        "charge.dispute.funds_reinstated",
    }
)
PAYOUT_EVENTS = frozenset({"payout.created", "payout.updated", "payout.paid", "payout.failed", "payout.canceled"})
HANDLED_EVENTS = REFUND_EVENTS | DISPUTE_EVENTS | PAYOUT_EVENTS


def handle_stripe_money_event(db: Session, settings: Any, event_type: str, obj: dict[str, Any]) -> dict[str, Any]:
    from porterchain_api.billing_engine import stripe_money as sm

    if event_type == "charge.refunded":
        return sm.apply_charge_refunds(db, obj)
    if event_type == "charge.refund.updated":
        # The object is a single refund; wrap it like a charge's refund list.
        return sm.apply_charge_refunds(db, {"payment_intent": obj.get("payment_intent"), "refunds": {"data": [obj]}})
    if event_type in DISPUTE_EVENTS:
        return sm.apply_dispute(db, obj)
    if event_type in PAYOUT_EVENTS:
        from porterchain_api.services.stripe_service import list_payout_balance_transactions

        return sm.handle_payout_event(
            db, obj, fetch=lambda pid: list_payout_balance_transactions(settings, pid)
        )
    return {"status": "ignored"}


def stripe_overview(db: Session) -> dict[str, Any]:
    from porterchain_api.billing_engine.stripe_money import disputes_payload, payouts_payload

    payouts = payouts_payload(db)
    disputes = disputes_payload(db)
    return {
        "payouts": payouts,
        "disputes": disputes,
        "open_disputes": sum(1 for d in disputes if d["open"]),
        "open_dispute_cents": sum(int(d["amount_cents"] or 0) for d in disputes if d["open"]),
        "unreconciled": sum(1 for p in payouts if p["status"] == "paid" and not p["reconciled"]),
        "fees_cents_30d": sum(int(p["fee_cents"] or 0) for p in payouts[:30]),
    }
