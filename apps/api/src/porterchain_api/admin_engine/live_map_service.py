"""Live Operations Map — Application Service.

Aggregates Porterchain operational mirror + driver location pings.
GPS/route execution data originates from Fleetbase and is mirrored here;
this service never calls Fleetbase HTTP directly (masterrule §3, §7).
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.admin_engine.control_tower_service import ControlTowerService
from porterchain_api.admin_engine.live_map_builders import LiveMapBuildersMixin
from porterchain_api.admin_engine.live_map_entities import LiveMapEntitiesMixin
from porterchain_api.admin_engine.live_map_helpers import DEFAULT_CENTER, _now
from porterchain_api.admin_engine.live_map_location import LiveMapLocationMixin
from porterchain_api.admin_engine.live_map_overlays import LiveMapOverlaysMixin
from porterchain_api.admin_engine.live_map_playback import LiveMapPlaybackMixin
from porterchain_api.merchant_models import Merchant
from porterchain_api.models import Customer
from porterchain_api.schemas_live_map import LiveMapFilters


class LiveMapService(
    LiveMapLocationMixin,
    LiveMapBuildersMixin,
    LiveMapOverlaysMixin,
    LiveMapEntitiesMixin,
    LiveMapPlaybackMixin,
):
    def __init__(self) -> None:
        self._tower = ControlTowerService()

    def snapshot(self, db: Session, *, filters: LiveMapFilters | None = None) -> dict[str, Any]:
        f = filters or LiveMapFilters()
        now = _now()
        pings = self._latest_pings(db)
        vehicle_by_driver = self._driver_vehicle_map(db)
        active_orders = self._active_order_by_driver(db)
        merchants = {m.id: m for m in db.query(Merchant).all()}
        customers = {c.id: c for c in db.query(Customer).all()}

        drivers = self._build_drivers(db, pings, vehicle_by_driver, active_orders, f)
        vehicles = self._build_vehicles(db, pings, vehicle_by_driver, f)
        orders = self._build_order_stops(db, merchants, customers, f)
        merchant_pins = self._build_merchants(db, merchants, f)
        customer_pins = self._build_customers(db, customers, orders)
        warehouses = self._build_warehouses(db, merchants)
        geofences = self._build_geofences(db)
        alerts = self._build_alerts(db, now)
        events = self._build_events(db)
        support_tickets = self._build_support_tickets(db)
        claims = self._build_claims_panel(db)
        incidents = self._build_incidents_panel(db)
        command_center = self._command_center(db)
        heat_maps = self._heat_maps(orders, drivers)
        smart = self._smart_insights(db, drivers, orders, now)
        weather = self._weather_stub()

        return {
            "generated_at": now.isoformat(),
            "default_center": DEFAULT_CENTER,
            "drivers": drivers,
            "vehicles": vehicles,
            "orders": orders,
            "merchants": merchant_pins,
            "customers": customer_pins,
            "warehouses": warehouses,
            "geofences": geofences,
            "alerts": alerts,
            "events": events,
            "support_tickets": support_tickets,
            "claims": claims,
            "incidents": incidents,
            "command_center": command_center,
            "heat_maps": heat_maps,
            "smart": smart,
            "weather": weather,
        }


__all__ = ["LiveMapService"]
