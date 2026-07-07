"""Dispatch service — assignment and re-assignment (infrastructure stub)."""

from porterchain_services.base import BaseService
from porterchain_shared.events.catalog import DomainEventType
from porterchain_shared.events.envelope import EventActor, EventEnvelope
from porterchain_shared.queue.names import QueueName


class DispatchService(BaseService):
    service_name = "dispatch"

    def enqueue_dispatch_ready(self, order_id: str) -> None:
        self.ctx.queues.enqueue(QueueName.DISPATCH, {"order_id": order_id, "action": "dispatch_ready"})
        self.ctx.events.publish(
            EventEnvelope(
                event_type=DomainEventType.ORDER_DISPATCH_READY,
                aggregate_type="order",
                aggregate_id=order_id,
                payload={},
            )
        )

    def assign_driver(self, order_id: str, driver_id: str, actor_id: str) -> None:
        self.ctx.events.publish(
            EventEnvelope(
                event_type=DomainEventType.DRIVER_ASSIGNED,
                aggregate_type="order",
                aggregate_id=order_id,
                actor=EventActor(type="dispatcher", id=actor_id),
                payload={"driver_id": driver_id},
            )
        )
        self.ctx.queues.enqueue(
            QueueName.DISPATCH,
            {"order_id": order_id, "action": "assign", "driver_id": driver_id},
        )
