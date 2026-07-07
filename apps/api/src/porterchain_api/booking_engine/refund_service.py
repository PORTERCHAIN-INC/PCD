"""Refund handling for cancelled orders.

Issues a refund for the captured payment on an order (real Stripe in
production, a simulated refund in local/dev mock mode), marks the payment
``REFUNDED``, and records a ``payment.refunded`` domain event. Designed to be
reused by any cancel path (customer today; merchant/admin can adopt it next).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy.orm import Session

from porterchain_api.booking_engine import events as E
from porterchain_api.booking_engine._core import emit_event
from porterchain_api.config import Settings
from porterchain_api.domain.states import PaymentStatus
from porterchain_api.models import Order, Payment
from porterchain_api.services import stripe_service

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RefundOutcome:
    """Result of a refund attempt.

    ``refunded`` is True when the payment was refunded (real or mock).
    ``reason`` is one of: ``refunded``, ``mock_refunded``, ``no_payment``,
    ``manual_required`` (payment exists but Stripe refund could not be issued).
    """

    refunded: bool
    refund_id: str | None
    amount_cents: int
    reason: str

    @property
    def pending(self) -> bool:
        """True when a human/finance follow-up is still required."""
        return self.reason == "manual_required"


class PaymentRefundService:
    def _succeeded_payment(self, db: Session, order: Order) -> Payment | None:
        return (
            db.query(Payment)
            .filter(
                Payment.order_id == order.id,
                Payment.status == PaymentStatus.SUCCEEDED.value,
            )
            .order_by(Payment.created_at.desc())
            .first()
        )

    def refund_order(
        self,
        db: Session,
        settings: Settings,
        order: Order,
        *,
        actor_type: str = "system",
        actor_id: str | None = None,
    ) -> RefundOutcome:
        payment = self._succeeded_payment(db, order)
        if payment is None:
            # Nothing captured (e.g. unpaid/mock order without a payment row).
            return RefundOutcome(refunded=False, refund_id=None, amount_cents=0, reason="no_payment")

        amount = payment.amount_cents

        if settings.allow_stripe_mock:
            # Local/dev: simulate the refund without calling Stripe.
            refund_id: str | None = f"mock_refund_{payment.id}"
            reason = "mock_refunded"
            refunded = True
        else:
            try:
                refund_id = stripe_service.create_refund(settings, order, amount)
            except Exception as exc:  # noqa: BLE001 - never let a refund error mask the cancel
                logger.exception("stripe refund failed for order %s: %s", order.id, exc)
                refund_id = None
            refunded = refund_id is not None
            reason = "refunded" if refunded else "manual_required"

        if refunded:
            payment.status = PaymentStatus.REFUNDED.value
            db.add(payment)
            emit_event(
                db,
                event_type=E.PAYMENT_REFUNDED,
                aggregate_type="payment",
                aggregate_id=payment.id,
                correlation_id=order.quote_id,
                actor_type=actor_type,
                actor_id=actor_id,
                payload={
                    "order_id": order.id,
                    "refund_id": refund_id,
                    "amount_cents": amount,
                    "mock": settings.allow_stripe_mock,
                },
            )
            db.commit()

        return RefundOutcome(refunded=refunded, refund_id=refund_id, amount_cents=amount, reason=reason)
