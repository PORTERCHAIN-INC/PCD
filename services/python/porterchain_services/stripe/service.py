"""Stripe payment service — all payment rails through Porterchain."""

import logging

from porterchain_services.base import BaseService
from porterchain_shared.events.catalog import DomainEventType
from porterchain_shared.events.envelope import EventEnvelope

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
