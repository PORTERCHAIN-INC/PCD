"""Low-level Fleetbase adapter calls — outbound only, no domain transitions.

All Porterchain → Fleetbase HTTP traffic flows through this bridge and
`services/fleetbase_integration`. Higher-level orchestration (retry, audit)
lives in `BookingSyncService`.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.booking_engine import events as E
from porterchain_api.booking_engine._core import emit_event
from porterchain_api.config import Settings
from porterchain_api.booking_models import Order
from porterchain_api.services.fleetbase_integration import get_fleetbase_integration

logger = logging.getLogger(__name__)


def _packages_for_fleetbase(order: Order) -> list[dict[str, Any]]:
    """Serialize Package rows (or compliance packages) for adapter Entity mapping."""
    rows = getattr(order, "packages", None) or []
    out: list[dict[str, Any]] = []
    for pkg in rows:
        dims = pkg.dimensions if isinstance(getattr(pkg, "dimensions", None), dict) else {}
        out.append(
            {
                "id": getattr(pkg, "id", None),
                "name": f"Parcel {getattr(pkg, 'parcel_index', '')}".strip() or "Parcel",
                "weight_kg": float(pkg.weight_kg) if pkg.weight_kg is not None else None,
                "quantity": 1,
                "length_cm": dims.get("length_cm"),
                "width_cm": dims.get("width_cm"),
                "height_cm": dims.get("height_cm"),
                "dimensions": dims or None,
                "dimensions_unit": "cm",
            }
        )
    if out:
        return out
    compliance = order.compliance_metadata if isinstance(order.compliance_metadata, dict) else {}
    raw = compliance.get("packages")
    if isinstance(raw, list):
        return [p for p in raw if isinstance(p, dict)]
    return []


def _order_weight_kg(order: Order, packages: list[dict[str, Any]]) -> float | None:
    total = 0.0
    found = False
    for pkg in packages:
        w = pkg.get("weight_kg") or pkg.get("weight")
        if w is None:
            continue
        try:
            total += float(w) * float(pkg.get("quantity") or 1)
            found = True
        except (TypeError, ValueError):
            continue
    if found:
        return total
    quote = getattr(order, "quote", None)
    if quote is not None and getattr(quote, "weight_kg", None) is not None:
        return float(quote.weight_kg)
    return None


def _order_volume_m3(packages: list[dict[str, Any]]) -> float | None:
    total = 0.0
    found = False
    for pkg in packages:
        dims = pkg.get("dimensions") if isinstance(pkg.get("dimensions"), dict) else {}
        try:
            l = float(pkg.get("length_cm") or dims.get("length_cm") or 0)
            w = float(pkg.get("width_cm") or dims.get("width_cm") or 0)
            h = float(pkg.get("height_cm") or dims.get("height_cm") or 0)
        except (TypeError, ValueError):
            continue
        if l > 0 and w > 0 and h > 0:
            qty = float(pkg.get("quantity") or 1)
            total += (l * w * h) / 1_000_000.0 * qty  # cm³ → m³
            found = True
    return total if found else None


class FleetbaseIntegrationBridge:
    """Thin wrapper around the Fleetbase integration adapter."""

    def __init__(self, *, max_retries: int | None = None) -> None:
        # Drain path passes max_retries=0; request/GET paths keep adapter default (3).
        self._max_retries = max_retries

    def _integration(self, settings: Settings):
        return get_fleetbase_integration(settings, max_retries=self._max_retries)

    def sync_order(self, db: Session, settings: Settings, order: Order) -> str | None:
        if not settings.fleetbase_dispatch_bridge:
            logger.info("Fleetbase dispatch bridge disabled; skipping order %s", order.id)
            return None

        compliance = order.compliance_metadata if isinstance(order.compliance_metadata, dict) else {}
        additional_stops = compliance.get("additional_stops") or []
        payload: dict[str, Any] = {
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

        # Capacity feed for Fleetbase VROOM — Entity weight/dims + order meta fallback.
        packages = _packages_for_fleetbase(order)
        if packages:
            payload["packages"] = packages
        weight_kg = _order_weight_kg(order, packages)
        if weight_kg is not None:
            payload["weight_kg"] = weight_kg
        volume_m3 = _order_volume_m3(packages)
        if volume_m3 is not None:
            payload["volume_m3"] = volume_m3
        if packages:
            payload["parcels"] = len(packages)

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

    def sync_driver(self, db: Session, settings: Settings, driver: Any) -> str | None:
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
            from porterchain_api.admin_engine.fleetbase_ids import persist_driver_fleetbase_id

            persist_driver_fleetbase_id(db, driver, fleetbase_id)
        return fleetbase_id

    def sync_vehicle(self, db: Session, settings: Settings, vehicle: Any) -> str | None:
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
            "fleetbase_driver_id": (
                vehicle.driver.fleetbase_driver_id if vehicle.driver else None
            ),
        }

        fleetbase_id = self._integration(settings).sync_vehicle(payload)
        if fleetbase_id:
            from porterchain_api.admin_engine.fleetbase_ids import persist_vehicle_fleetbase_id

            persist_vehicle_fleetbase_id(db, vehicle, fleetbase_id)
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
