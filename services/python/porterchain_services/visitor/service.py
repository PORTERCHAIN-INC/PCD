"""Visitor tracking — anonymous sessions, leads, abandoned checkout, session merge."""

from porterchain_services.base import BaseService
from porterchain_shared.events.catalog import DomainEventType
from porterchain_shared.events.envelope import EventActor, EventEnvelope
from porterchain_shared.queue.names import QueueName


class VisitorService(BaseService):
    service_name = "visitor"

    def start_session(self, anonymous_session_id: str) -> None:
        self.ctx.events.publish(
            EventEnvelope(
                event_type=DomainEventType.VISITOR_SESSION_STARTED,
                aggregate_type="visitor",
                aggregate_id=anonymous_session_id,
                actor=EventActor(type="visitor", id=anonymous_session_id),
                payload={},
            )
        )

    def create_lead(self, lead_id: str, anonymous_session_id: str | None, payload: dict) -> None:
        self.ctx.events.publish(
            EventEnvelope(
                event_type=DomainEventType.LEAD_CREATED,
                aggregate_type="lead",
                aggregate_id=lead_id,
                correlation_id=anonymous_session_id,
                payload=payload,
            )
        )

    def record_abandoned_checkout(self, quote_id: str, email: str, phone: str) -> None:
        self.ctx.events.publish(
            EventEnvelope(
                event_type=DomainEventType.CHECKOUT_ABANDONED,
                aggregate_type="quote",
                aggregate_id=quote_id,
                payload={"email": email, "phone": phone},
            )
        )
        self.ctx.queues.enqueue(
            QueueName.EMAILS,
            {
                "channel": "email",
                "template": "checkout_recovery",
                "recipient": email,
                "context": {"quote_id": quote_id},
            },
        )

    def merge_session(self, anonymous_session_id: str, customer_id: str, clerk_user_id: str) -> None:
        self.ctx.events.publish(
            EventEnvelope(
                event_type=DomainEventType.SESSION_MERGED,
                aggregate_type="visitor",
                aggregate_id=anonymous_session_id,
                actor=EventActor(type="customer", id=clerk_user_id),
                payload={"customer_id": customer_id},
            )
        )
