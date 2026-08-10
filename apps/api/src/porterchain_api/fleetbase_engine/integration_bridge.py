"""Low-level Fleetbase adapter calls — outbound only, no domain transitions.

All Porterchain → Fleetbase HTTP traffic flows through this bridge and
`services/fleetbase_integration`. Higher-level orchestration (retry, audit)
lives in `BookingSyncService`.
"""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from porterchain_api.admin_models import Driver, Vehicle
from porterchain_api.booking_engine import events as E
from porterchain_api.booking_engine._core import emit_event
from porterchain_api.config import Settings
from porterchain_api.models import Order
from porterchain_api.services.fleetbase_integration import get_fleetbase_integration

logger = logging.getLogger(__name__)


class FleetbaseIntegrationBridge:
    """Thin wrapper around the Fleetbase integration adapter."""

    def _integration(self, settings: Settings):
        return get_fleetbase_integration(settings)

    def sync_order(self, db: Session, settings: Settings, order: Order) -> str | None:
        if not settings.fleetbase_dispatch_bridge:
            logger.info("Fleetbase dispatch bridge disabled; skipping order %s", order.id)
            return None

        compliance = order.compliance_metadata if isinstance(order.compliance_metadata, dict) else {}
        additional_stops = compliance.get("additional_stops") or []
        payload = {
            "porterchain_order_id": order.id,
            "fleetbase_order_id": order.fleetbase_order_id,
            "order_number": order.order_number,
            "tracking_number": order.tracking_number,
            "merchant_id": order.merchant_id,
            "pickup": order.pickup,
            "dropoff": order.dropoff,
            "additional_stops": additional_stops,
            "scheduled_at": order.scheduled_at.isoformat(),
            "special_instructions": order.special_instructions,
        }
        # Rich typed/sequenced stops (hub-spoke, multi-pickup) take precedence
        # over the legacy address-only additional_stops when present.
        stops = compliance.get("stops")
        if isinstance(stops, list) and stops:
            payload["stops"] = stops

        fleetbase_id = self._integration(settings).sync_order(payload)

        if fleetbase_id:
            order.fleetbase_order_id = fleetbase_id
            emit_event(
                db,
                event_type=E.FLEETBASE_ORDER_CREATED,
                aggregate_type="order",
                aggregate_id=order.id,
                correlation_id=order.quote_id,
                payload={"fleetbase_order_id": fleetbase_id},
            )
            db.commit()
            db.refresh(order)

        return fleetbase_id

    def sync_driver(self, db: Session, settings: Settings, driver: Driver) -> str | None:
        if not settings.fleetbase_dispatch_bridge:
            return None

        vehicle = next((v for v in driver.vehicles if v.is_active), None)
        payload = {
            "id": driver.id,
            "porterchain_driver_id": driver.id,
            "fleetbase_driver_id": driver.fleetbase_driver_id,
            "full_name": driver.full_name,
            "email": driver.email,
            "phone": driver.phone,
            "fleetbase_vehicle_id": vehicle.fleetbase_vehicle_id if vehicle else None,
        }

        fleetbase_id = self._integration(settings).sync_driver(payload)
        if fleetbase_id:
            driver.fleetbase_driver_id = fleetbase_id
            db.commit()
            db.refresh(driver)
        return fleetbase_id

    def sync_vehicle(self, db: Session, settings: Settings, vehicle: Vehicle) -> str | None:
        if not settings.fleetbase_dispatch_bridge:
            return None

        payload = {
            "id": vehicle.id,
            "porterchain_vehicle_id": vehicle.id,
            "fleetbase_vehicle_id": vehicle.fleetbase_vehicle_id,
            "plate_number": vehicle.plate_number,
            "make_model": vehicle.make_model,
            "vehicle_class": vehicle.vehicle_class,
            "capacity_kg": vehicle.capacity_kg,
            "is_active": bool(vehicle.is_active),
            "driver_id": vehicle.driver_id,
        }

        fleetbase_id = self._integration(settings).sync_vehicle(payload)
        if fleetbase_id:
            vehicle.fleetbase_vehicle_id = fleetbase_id
            db.commit()
            db.refresh(vehicle)
        return fleetbase_id

    def fetch_tracking(self, settings: Settings, order: Order) -> dict | None:
        if not order.fleetbase_order_id or not settings.fleetbase_dispatch_bridge:
            return None
        return self._integration(settings).fetch_tracking(order.fleetbase_order_id)

    def sync_dispatch(
        self,
        settings: Settings,
        order: Order,
        *,
        fleetbase_driver_id: str | None = None,
    ) -> dict | None:
        if not order.fleetbase_order_id:
            return None
        return self._integration(settings).sync_dispatch(
            order.fleetbase_order_id,
            driver_id=fleetbase_driver_id,
        )

    def sync_proofs(self, settings: Settings, order: Order) -> list[dict]:
        if not order.fleetbase_order_id:
            return []
        return self._integration(settings).sync_proofs(order.fleetbase_order_id)

    def sync_status_from_fleetbase(self, settings: Settings, order: Order) -> dict | None:
        """Poll Fleetbase order status (+ proofs) for PC↔FB diff / POD gallery."""
        if not order.fleetbase_order_id or not settings.fleetbase_dispatch_bridge:
            return None
        return self._integration(settings).sync_status_from_fleetbase(order.fleetbase_order_id)

    def cancel_order(self, settings: Settings, order: Order) -> bool:
        if not order.fleetbase_order_id or not settings.fleetbase_dispatch_bridge:
            return False
        return self._integration(settings).cancel_order(order.fleetbase_order_id)
