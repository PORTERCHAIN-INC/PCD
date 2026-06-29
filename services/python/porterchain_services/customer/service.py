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
        from porterchain_services.gateway.registry import get_service_registry

        registry = get_service_registry()
        registry.notifications.send_booking_confirmed(
            email="", phone="", tracking_number=order_id
        )
