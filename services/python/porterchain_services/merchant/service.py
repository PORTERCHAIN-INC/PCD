"""Merchant service — B2B lifecycle (infrastructure stub)."""

from porterchain_services.base import BaseService
from porterchain_shared.events.catalog import DomainEventType
from porterchain_shared.events.envelope import EventActor, EventEnvelope


class MerchantService(BaseService):
    service_name = "merchant"

    def record_lead(self, lead_id: str, payload: dict) -> None:
        self.ctx.events.publish(
            EventEnvelope(
                event_type=DomainEventType.MERCHANT_LEAD_CREATED,
                aggregate_type="lead",
                aggregate_id=lead_id,
                payload=payload,
            )
        )

    def approve(self, merchant_id: str, actor_id: str) -> None:
        self.ctx.events.publish(
            EventEnvelope(
                event_type=DomainEventType.MERCHANT_APPROVED,
                aggregate_type="merchant",
                aggregate_id=merchant_id,
                actor=EventActor(type="admin", id=actor_id),
                payload={},
            )
        )

    def activate(self, merchant_id: str) -> None:
        self.ctx.events.publish(
            EventEnvelope(
                event_type=DomainEventType.MERCHANT_ACTIVATED,
                aggregate_type="merchant",
                aggregate_id=merchant_id,
                payload={},
            )
        )
