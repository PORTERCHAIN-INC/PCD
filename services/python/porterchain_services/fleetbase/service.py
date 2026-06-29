"""Fleetbase integration — delegates to porterchain_fleetbase package."""

import logging
from typing import Any

from porterchain_fleetbase import FleetbaseIntegrationService
from porterchain_fleetbase.config import FleetbaseSettings
from porterchain_services.base import BaseService
from porterchain_shared.events.catalog import DomainEventType
from porterchain_shared.events.envelope import EventActor, EventEnvelope
from porterchain_shared.queue.names import QueueName

logger = logging.getLogger(__name__)


class FleetbaseService(BaseService):
    service_name = "fleetbase"

    def _integration(self) -> FleetbaseIntegrationService:
        return FleetbaseIntegrationService(
            FleetbaseSettings(
                api_url=self.settings.fleetbase_api_url,
                api_key=self.settings.fleetbase_api_key,
                company_uuid=self.settings.fleetbase_default_company_uuid,
                dispatch_bridge=self.settings.fleetbase_dispatch_bridge,
            )
        )

    @property
    def is_configured(self) -> bool:
        return bool(self.settings.fleetbase_dispatch_bridge)

    def sync_order(self, order_payload: dict[str, Any]) -> str | None:
        if not self.is_configured:
            logger.info("Fleetbase bridge disabled")
            return None

        try:
            fleetbase_id = self._integration().sync_order(order_payload)
        except Exception as exc:
            self._emit_sync_failed(order_payload, str(exc))
            return None

        if not fleetbase_id:
            self._emit_sync_failed(order_payload, "fleetbase_order_sync_failed")
            return None

        self.ctx.events.publish(
            EventEnvelope(
                event_type=DomainEventType.FLEETBASE_ORDER_CREATED,
                aggregate_type="order",
                aggregate_id=order_payload.get("porterchain_order_id", ""),
                correlation_id=order_payload.get("tracking_number"),
                actor=EventActor(type="system"),
                payload={"fleetbase_order_id": fleetbase_id},
            )
        )
        return fleetbase_id

    def sync_driver(self, driver_payload: dict[str, Any]) -> str | None:
        if not self.is_configured:
            return None
        return self._integration().sync_driver(driver_payload)

    def sync_vehicle(self, vehicle_payload: dict[str, Any]) -> str | None:
        if not self.is_configured:
            return None
        return self._integration().sync_vehicle(vehicle_payload)

    def fetch_tracking(self, fleetbase_order_id: str) -> dict[str, Any] | None:
        if not self.is_configured:
            return None
        return self._integration().fetch_tracking(fleetbase_order_id)

    def enqueue_dispatch(self, order_id: str) -> None:
        self.ctx.queues.enqueue(QueueName.DISPATCH, {"order_id": order_id, "action": "dispatch_ready"})

    def _emit_sync_failed(self, payload: dict[str, Any], error: str) -> None:
        self.ctx.events.publish(
            EventEnvelope(
                event_type=DomainEventType.FLEETBASE_SYNC_FAILED,
                aggregate_type="order",
                aggregate_id=payload.get("porterchain_order_id", ""),
                payload={"error": error},
            )
        )
        self.ctx.queues.enqueue(
            QueueName.DISPATCH,
            {"order_id": payload.get("porterchain_order_id"), "action": "retry_sync", "error": error},
        )
