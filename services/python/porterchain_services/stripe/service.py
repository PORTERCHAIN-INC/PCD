"""Stripe payment service — all payment rails through Porterchain."""

import logging
from typing import Any

from porterchain_services.base import BaseService
from porterchain_shared.events.catalog import DomainEventType
from porterchain_shared.events.envelope import EventEnvelope
from porterchain_shared.queue.names import QueueName

logger = logging.getLogger(__name__)


class StripeService(BaseService):
    service_name = "stripe"

    @property
    def is_configured(self) -> bool:
        return bool(self.settings.stripe_secret) and not self.settings.stripe_mock

    def create_checkout_session(
        self,
        *,
        quote_id: str,
        amount_cents: int,
        currency: str,
        customer_email: str,
        success_url: str,
        cancel_url: str,
        metadata: dict[str, str] | None = None,
    ) -> str | None:
        if not self.is_configured:
            logger.info("Stripe mock mode — no checkout session")
            return None

        from porterchain_services.stripe import sdk as stripe_sdk

        stripe_sdk.configure(self.settings.stripe_secret)
        session = stripe_sdk.create_checkout_session(
            mode="payment",
            customer_email=customer_email,
            line_items=[
                {
                    "price_data": {
                        "currency": currency.lower(),
                        "unit_amount": amount_cents,
                        "product_data": {"name": "Porterchain Delivery"},
                    },
                    "quantity": 1,
                }
            ],
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={"quote_id": quote_id, **(metadata or {})},
        )
        self.ctx.events.publish(
            EventEnvelope(
                event_type=DomainEventType.CHECKOUT_STARTED,
                aggregate_type="quote",
                aggregate_id=quote_id,
                payload={"stripe_session_id": session.id},
            )
        )
        return session.url

    def handle_webhook_event(self, event_type: str, data: dict[str, Any]) -> None:
        if event_type == "checkout.session.completed":
            self.ctx.events.publish(
                EventEnvelope(
                    event_type=DomainEventType.PAYMENT_SUCCEEDED,
                    aggregate_type="payment",
                    aggregate_id=data.get("id", ""),
                    payload=data,
                )
            )
            self.ctx.queues.enqueue(QueueName.BILLING, {"action": "payment_succeeded", "data": data})
        elif event_type == "payment_intent.payment_failed":
            self.ctx.events.publish(
                EventEnvelope(
                    event_type=DomainEventType.PAYMENT_FAILED,
                    aggregate_type="payment",
                    aggregate_id=data.get("id", ""),
                    payload=data,
                )
            )
