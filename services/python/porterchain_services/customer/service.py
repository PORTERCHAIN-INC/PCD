"""Customer service — retail customer lifecycle (infrastructure stub)."""

from porterchain_services.base import BaseService
from porterchain_shared.events.catalog import DomainEventType
from porterchain_shared.events.envelope import EventActor, EventEnvelope


class CustomerService(BaseService):
    service_name = "customer"

    def register(self, customer_id: str, clerk_user_id: str, email: str) -> None:
        self.ctx.events.publish(
            EventEnvelope(
                event_type=DomainEventType.CUSTOMER_REGISTERED,
                aggregate_type="customer",
                aggregate_id=customer_id,
                actor=EventActor(type="customer", id=clerk_user_id),
                payload={"email": email, "clerk_user_id": clerk_user_id},
            )
        )

    def on_payment_succeeded(self, customer_id: str, order_id: str) -> None:
        # Booking/payment confirmation is owned by notification_engine via
        # DomainEventType.PAYMENT_SUCCEEDED / ORDER_BOOKED fanout — do not
        # enqueue legacy gateway notifications here.
        self.ctx.events.publish(
            EventEnvelope(
                event_type=DomainEventType.PAYMENT_SUCCEEDED,
                aggregate_type="order",
                aggregate_id=order_id,
                actor=EventActor(type="customer", id=customer_id),
                payload={"customer_id": customer_id, "order_id": order_id},
            )
        )
