"""Fleetbase sync service — Porterchain API bridge to logistics engine."""

import logging

from sqlalchemy.orm import Session

from porterchain_api.admin_models import Driver, Vehicle
from porterchain_api.booking_engine import events as E
from porterchain_api.booking_engine._core import emit_event
from porterchain_api.booking_engine.order_transitions import transition_order_state
from porterchain_api.config import Settings
from porterchain_api.domain.states import OrderState
from porterchain_api.models import Order
from porterchain_api.services.fleetbase_integration import get_fleetbase_integration

logger = logging.getLogger(__name__)


class FleetbaseSyncService:
    """All Fleetbase communication flows through this service."""

    def _integration(self, settings: Settings):
        return get_fleetbase_integration(settings)

    def sync_order(self, db: Session, settings: Settings, order: Order) -> str | None:
        if not settings.fleetbase_dispatch_bridge:
            logger.info("Fleetbase dispatch bridge disabled; skipping order %s", order.id)
            return None

        payload = {
            "porterchain_order_id": order.id,
            "fleetbase_order_id": order.fleetbase_order_id,
            "order_number": order.order_number,
            "tracking_number": order.tracking_number,
            "merchant_id": order.merchant_id,
            "pickup": order.pickup,
            "dropoff": order.dropoff,
            "scheduled_at": order.scheduled_at.isoformat(),
            "special_instructions": order.special_instructions,
        }

        integration = self._integration(settings)
        fleetbase_id = integration.sync_order(payload)

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

    def apply_webhook_update(self, db: Session, settings: Settings, update: dict) -> Order | None:
        """Apply Fleetbase webhook status to Porterchain order."""
        order_id = update.get("porterchain_order_id")
        fleetbase_id = update.get("fleetbase_order_id")
        order: Order | None = None

        if order_id:
            order = db.query(Order).filter(Order.id == order_id).first()
        if not order and fleetbase_id:
            order = db.query(Order).filter(Order.fleetbase_order_id == fleetbase_id).first()
        if not order:
            logger.warning("Fleetbase webhook: order not found pc=%s fb=%s", order_id, fleetbase_id)
            return None

        target_state = update.get("target_state")
        if target_state:
            try:
                new_state = OrderState(target_state)
                current = OrderState(order.state)
                if new_state != current:
                    transition_order_state(
                        db,
                        order,
                        new_state,
                        event_type=update.get("domain_event") or f"fleetbase.{update.get('event')}",
                        actor_type="fleetbase",
                        payload={"fleetbase_event": update.get("event")},
                    )
            except ValueError as exc:
                logger.warning("Invalid state transition from webhook: %s", exc)

        if update.get("event") == "order.completed":
            proofs = self.sync_proofs(settings, order)
            if proofs and order.state == OrderState.DELIVERED.value:
                transition_order_state(
                    db,
                    order,
                    OrderState.POD_COMPLETED,
                    event_type="order.pod_completed",
                    actor_type="fleetbase",
                    payload={"proof_count": len(proofs)},
                )

        db.refresh(order)
        return order
