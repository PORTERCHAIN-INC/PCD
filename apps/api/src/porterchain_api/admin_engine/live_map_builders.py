"""Snapshot entity builders for the live operations map."""

from __future__ import annotations

from datetime import date, datetime, time

from sqlalchemy.orm import Session, joinedload

from porterchain_api.admin_engine.control_tower_service import HIGH_PRIORITY_CENTS, IN_FLIGHT, WAITING
from porterchain_api.admin_engine.live_map_helpers import (
    VEHICLE_STATUS_MAP,
    _coords,
    _driver_ref,
    _merchant_ref,
    _order_vehicle_class,
    _vehicle_ref,
)
from porterchain_api.admin_models import Driver, PricingZone, Vehicle
from porterchain_api.driver_models import DriverLocationPing
from porterchain_api.merchant_models import Merchant, SavedAddress
from porterchain_api.models import Customer, Order
from porterchain_api.schemas_live_map import LiveMapFilters


class LiveMapBuildersMixin:
    def _build_drivers(
        self,
        db: Session,
        pings: dict[str, DriverLocationPing],
        vehicle_by_driver: dict[str, Vehicle],
        active_orders: dict[str, Order],
        f: LiveMapFilters,
    ) -> list[dict]:
        q = db.query(Driver)
        if f.driver_status:
            q = q.filter(Driver.availability.in_(f.driver_status))
        if f.online_only:
            q = q.filter(Driver.is_online.is_(True))
        rows = q.limit(5000).all()
        out: list[dict] = []
        for d in rows:
            if f.vehicle_type:
                v = vehicle_by_driver.get(d.id)
                if not v or v.vehicle_class not in f.vehicle_type:
                    continue
            ping = pings.get(d.id)
            loc = None
            heading = None
            speed_kmh = None
            updated_at = None
            if ping:
                loc = {"lat": ping.lat, "lng": ping.lng}
                heading = ping.heading
                speed_kmh = round(ping.speed_mps * 3.6, 1) if ping.speed_mps else None
                updated_at = ping.created_at.isoformat() if ping.created_at else None
            vehicle = vehicle_by_driver.get(d.id)
            active = active_orders.get(d.id)
            docs = d.documents or {}
            out.append(
                {
                    "id": d.id,
                    "reference": _driver_ref(d.id),
                    "name": d.full_name,
                    "photo_url": docs.get("photo_url"),
                    "phone": d.phone,
                    "email": d.email,
                    "status": d.status,
                    "availability": d.availability,
                    "online": d.is_online,
                    "vehicle_type": vehicle.vehicle_class if vehicle else None,
                    "vehicle_id": vehicle.id if vehicle else None,
                    "vehicle_plate": vehicle.plate_number if vehicle else None,
                    "location": loc,
                    "heading": heading,
                    "speed_kmh": speed_kmh,
                    "battery_percent": None,
                    "rating": d.rating,
                    "current_order_id": active.id if active else None,
                    "updated_at": updated_at,
                }
            )
        return out

    def _build_vehicles(
        self,
        db: Session,
        pings: dict[str, DriverLocationPing],
        vehicle_by_driver: dict[str, Vehicle],
        f: LiveMapFilters,
    ) -> list[dict]:
        q = db.query(Vehicle).filter(Vehicle.is_active.is_(True))
        if f.vehicle_type:
            q = q.filter(Vehicle.vehicle_class.in_(f.vehicle_type))
        if f.vehicle_capacity_min_kg:
            q = q.filter(Vehicle.capacity_kg >= f.vehicle_capacity_min_kg)
        rows = q.limit(5000).all()
        driver_names = {d.id: d.full_name for d in db.query(Driver).all()}
        out: list[dict] = []
        for v in rows:
            driver = None
            ping = None
            if v.driver_id:
                ping = pings.get(v.driver_id)
                driver = driver_names.get(v.driver_id)
            status = "offline"
            if v.driver_id:
                drv = db.query(Driver).filter(Driver.id == v.driver_id).first()
                if drv:
                    status = VEHICLE_STATUS_MAP.get(drv.availability, "assigned" if drv.is_online else "offline")
            loc = None
            heading = None
            if ping:
                loc = {"lat": ping.lat, "lng": ping.lng}
                heading = ping.heading
            out.append(
                {
                    "id": v.id,
                    "reference": _vehicle_ref(v.id),
                    "driver_id": v.driver_id,
                    "driver_name": driver,
                    "vehicle_class": v.vehicle_class,
                    "plate_number": v.plate_number,
                    "make_model": v.make_model,
                    "capacity_kg": v.capacity_kg,
                    "status": status,
                    "location": loc,
                    "heading": heading,
                }
            )
        return out

    def _build_order_stops(
        self,
        db: Session,
        merchants: dict[str, Merchant],
        customers: dict[str, Customer],
        f: LiveMapFilters,
    ) -> list[dict]:
        states = list(WAITING + IN_FLIGHT)
        if f.delivery_status:
            states = [s for s in f.delivery_status if s in states] or states
        q = db.query(Order).options(joinedload(Order.quote)).filter(Order.state.in_(states))
        if f.merchant_id:
            q = q.filter(Order.merchant_id == f.merchant_id)
        if f.priority == "high":
            q = q.filter(Order.amount_cents >= HIGH_PRIORITY_CENTS)
        elif f.priority == "normal":
            q = q.filter(Order.amount_cents < HIGH_PRIORITY_CENTS)
        if f.date:
            try:
                day = date.fromisoformat(f.date)
                sod = datetime.combine(day, time.min)
                eod = datetime.combine(day, time.max)
                q = q.filter(Order.scheduled_at >= sod, Order.scheduled_at <= eod)
            except ValueError:
                pass
        rows = q.order_by(Order.scheduled_at.asc()).limit(5000).all()
        out: list[dict] = []
        for o in rows:
            merchant = merchants.get(o.merchant_id) if o.merchant_id else None
            customer = customers.get(o.customer_id) if o.customer_id else None
            pickup_city = (o.pickup or {}).get("city") or ""
            dropoff_city = (o.dropoff or {}).get("city") or ""
            if f.city and f.city.lower() not in pickup_city.lower() and f.city.lower() not in dropoff_city.lower():
                continue
            if f.region:
                region = (o.pickup or {}).get("region") or (o.dropoff or {}).get("region") or ""
                if f.region.lower() not in str(region).lower():
                    continue
            priority = "high" if o.amount_cents >= HIGH_PRIORITY_CENTS else "normal"
            pkg = (o.pickup or {}).get("package_count") or 1
            base = {
                "order_id": o.id,
                "tracking_number": o.tracking_number,
                "order_number": o.order_number,
                "state": o.state,
                "priority": priority,
                "eta": o.scheduled_at.isoformat() if o.scheduled_at else None,
                "merchant": merchant.company_name if merchant else None,
                "merchant_id": o.merchant_id,
                "customer_name": customer.email if customer else (o.dropoff or {}).get("name"),
                "package_count": int(pkg) if pkg else 1,
                "vehicle_required": _order_vehicle_class(o),
                "amount_cents": o.amount_cents,
            }
            pickup_coords = _coords(o.pickup)
            if pickup_coords:
                out.append({**base, "stop_type": "pickup", "location": {"lat": pickup_coords[0], "lng": pickup_coords[1]}})
            drop_coords = _coords(o.dropoff)
            if drop_coords:
                out.append({**base, "stop_type": "delivery", "location": {"lat": drop_coords[0], "lng": drop_coords[1]}})
        return out

    def _build_merchants(self, db: Session, merchants: dict[str, Merchant], f: LiveMapFilters) -> list[dict]:
        if f.merchant_id:
            merchants = {k: v for k, v in merchants.items() if k == f.merchant_id}
        out: list[dict] = []
        addresses = db.query(SavedAddress).filter(SavedAddress.lat.isnot(None), SavedAddress.lng.isnot(None)).all()
        seen: set[str] = set()
        for a in addresses:
            if a.merchant_id in seen:
                continue
            m = merchants.get(a.merchant_id)
            if not m:
                continue
            seen.add(a.merchant_id)
            out.append(
                {
                    "id": m.id,
                    "reference": _merchant_ref(m.id),
                    "name": m.company_name,
                    "email": m.email,
                    "phone": m.phone,
                    "location": {"lat": a.lat, "lng": a.lng},
                    "city": (m.billing_address or {}).get("city"),
                    "status": m.status,
                }
            )
        return out

    def _build_customers(self, db: Session, customers: dict[str, Customer], orders: list[dict]) -> list[dict]:
        seen: set[str] = set()
        out: list[dict] = []
        for stop in orders:
            if stop["stop_type"] != "delivery":
                continue
            order = db.query(Order).filter(Order.id == stop["order_id"]).first()
            if not order or not order.customer_id or order.customer_id in seen:
                continue
            c = customers.get(order.customer_id)
            if not c:
                continue
            seen.add(order.customer_id)
            out.append(
                {
                    "id": c.id,
                    "name": c.email,
                    "email": c.email,
                    "phone": c.phone,
                    "location": stop["location"],
                }
            )
        return out

    def _build_warehouses(self, db: Session, merchants: dict[str, Merchant]) -> list[dict]:
        rows = (
            db.query(SavedAddress)
            .filter(SavedAddress.address_type.in_(["warehouse", "pickup", "hub"]))
            .filter(SavedAddress.lat.isnot(None), SavedAddress.lng.isnot(None))
            .limit(500)
            .all()
        )
        out: list[dict] = []
        for a in rows:
            m = merchants.get(a.merchant_id)
            out.append(
                {
                    "id": a.id,
                    "label": a.label,
                    "merchant_id": a.merchant_id,
                    "merchant_name": m.company_name if m else None,
                    "address_type": a.address_type,
                    "location": {"lat": a.lat, "lng": a.lng},
                }
            )
        return out

    def _build_geofences(self, db: Session) -> list[dict]:
        zones = db.query(PricingZone).filter(PricingZone.is_active.is_(True)).all()
        return [
            {
                "id": z.id,
                "name": z.name,
                "geofence_type": "service_area",
                "bounds": z.bounds or {},
                "is_active": z.is_active,
            }
            for z in zones
        ]
