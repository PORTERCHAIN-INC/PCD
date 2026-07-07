"""Live Operations Map — Application Service.

Aggregates Porterchain operational mirror + driver location pings.
GPS/route execution data originates from Fleetbase and is mirrored here;
this service never calls Fleetbase HTTP directly (masterrule §3, §7).
"""

from __future__ import annotations

import math
from datetime import UTC, date, datetime, time, timedelta
from typing import Any

from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from porterchain_api.admin_engine.control_tower_service import (
    HIGH_PRIORITY_CENTS,
    IN_FLIGHT,
    WAITING,
    ControlTowerService,
)
from porterchain_api.admin_models import Claim, Driver, PricingZone, SupportTicket, Vehicle
from porterchain_api.driver_models import DriverIncident, DriverLocationPing
from porterchain_api.merchant_models import Merchant, SavedAddress
from porterchain_api.models import Customer, DomainEvent, Order, OrderException
from porterchain_api.schemas_live_map import LiveMapFilters

# GTA default viewport when no markers present.
DEFAULT_CENTER = {"lat": 43.6532, "lng": -79.3832}

VEHICLE_STATUS_MAP = {
    "available": "available",
    "idle": "available",
    "online": "assigned",
    "busy": "busy",
    "on_trip": "busy",
    "break": "busy",
    "offline": "offline",
    "maintenance": "maintenance",
}


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _parse_iso_naive(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is not None:
        return parsed.astimezone(UTC).replace(tzinfo=None)
    return parsed


def _coords(addr: dict | None) -> tuple[float, float] | None:
    if not addr:
        return None
    lat = addr.get("lat") or addr.get("latitude")
    lng = addr.get("lng") or addr.get("longitude")
    if lat is None or lng is None:
        return None
    try:
        return float(lat), float(lng)
    except (TypeError, ValueError):
        return None


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 6371.0
    d_lat = math.radians(lat2 - lat1)
    d_lng = math.radians(lng2 - lng1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(d_lng / 2) ** 2
    )
    return 2 * r * math.asin(math.sqrt(a))


def _driver_ref(driver_id: str) -> str:
    return f"PCD-{driver_id[:6].upper()}"


def _vehicle_ref(vehicle_id: str) -> str:
    return f"PCV-{vehicle_id[:6].upper()}"


def _merchant_ref(merchant_id: str) -> str:
    return f"PCM-{merchant_id[:6].upper()}"


def _order_vehicle_class(order: Order) -> str | None:
    quote = order.quote
    return quote.vehicle_class if quote else None


class LiveMapService:
    def __init__(self) -> None:
        self._tower = ControlTowerService()

    # ------------------------------------------------------------------ #
    # Location helpers
    # ------------------------------------------------------------------ #
    def _latest_pings(self, db: Session) -> dict[str, DriverLocationPing]:
        subq = (
            db.query(
                DriverLocationPing.driver_id,
                func.max(DriverLocationPing.created_at).label("max_at"),
            )
            .group_by(DriverLocationPing.driver_id)
            .subquery()
        )
        rows = (
            db.query(DriverLocationPing)
            .join(
                subq,
                (DriverLocationPing.driver_id == subq.c.driver_id)
                & (DriverLocationPing.created_at == subq.c.max_at),
            )
            .all()
        )
        return {p.driver_id: p for p in rows}

    def _driver_vehicle_map(self, db: Session) -> dict[str, Vehicle]:
        vehicles = db.query(Vehicle).filter(Vehicle.is_active.is_(True)).all()
        out: dict[str, Vehicle] = {}
        for v in vehicles:
            if v.driver_id and v.driver_id not in out:
                out[v.driver_id] = v
        return out

    def _active_order_by_driver(self, db: Session) -> dict[str, Order]:
        rows = db.query(Order).filter(Order.state.in_(IN_FLIGHT), Order.assigned_driver_id.isnot(None)).all()
        return {o.assigned_driver_id: o for o in rows if o.assigned_driver_id}

    # ------------------------------------------------------------------ #
    # Snapshot
    # ------------------------------------------------------------------ #
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
            "command_center": command_center,
            "heat_maps": heat_maps,
            "smart": smart,
            "weather": weather,
        }

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

    def _build_alerts(self, db: Session, now: datetime) -> list[dict]:
        alerts: list[dict] = []
        # Late deliveries
        late_orders = (
            db.query(Order)
            .filter(Order.state.in_(IN_FLIGHT), Order.scheduled_at < now)
            .limit(50)
            .all()
        )
        for o in late_orders:
            coords = _coords(o.dropoff) or _coords(o.pickup)
            alerts.append(
                {
                    "id": f"late-{o.id}",
                    "alert_type": "late_delivery",
                    "severity": "critical",
                    "title": "Late delivery",
                    "message": f"{o.tracking_number} is past scheduled ETA",
                    "entity_type": "order",
                    "entity_id": o.id,
                    "location": {"lat": coords[0], "lng": coords[1]} if coords else None,
                    "created_at": o.scheduled_at.isoformat() if o.scheduled_at else None,
                }
            )
        # Offline drivers with active orders — one alert per driver (not per order)
        active = db.query(Order).filter(Order.state.in_(IN_FLIGHT), Order.assigned_driver_id.isnot(None)).all()
        driver_ids = {o.assigned_driver_id for o in active if o.assigned_driver_id}
        drivers = (
            {d.id: d for d in db.query(Driver).filter(Driver.id.in_(driver_ids)).all()}
            if driver_ids
            else {}
        )
        offline_orders_by_driver: dict[str, tuple[Driver, list[Order]]] = {}
        for o in active:
            if not o.assigned_driver_id:
                continue
            drv = drivers.get(o.assigned_driver_id)
            if drv and not drv.is_online:
                entry = offline_orders_by_driver.get(drv.id)
                if entry is None:
                    offline_orders_by_driver[drv.id] = (drv, [o])
                else:
                    entry[1].append(o)
        for drv_id, (drv, orders) in offline_orders_by_driver.items():
            tracking = ", ".join(o.tracking_number for o in orders[:3] if o.tracking_number)
            if len(orders) > 3:
                tracking = f"{tracking} (+{len(orders) - 3} more)" if tracking else f"{len(orders)} active orders"
            alerts.append(
                {
                    "id": f"offline-driver-{drv_id}",
                    "alert_type": "driver_offline",
                    "severity": "warning",
                    "title": "Driver offline",
                    "message": (
                        f"{drv.full_name} is offline with active order {tracking}"
                        if len(orders) == 1
                        else f"{drv.full_name} is offline with active orders: {tracking}"
                    ),
                    "entity_type": "driver",
                    "entity_id": drv_id,
                    "location": None,
                    "created_at": now.isoformat(),
                }
            )
        # Open exceptions
        for e, order in (
            db.query(OrderException, Order)
            .join(Order, Order.id == OrderException.order_id)
            .filter(OrderException.status == "open")
            .limit(20)
            .all()
        ):
            coords = _coords(order.dropoff) or _coords(order.pickup)
            alerts.append(
                {
                    "id": f"exception-{e.id}",
                    "alert_type": "incident",
                    "severity": "warning",
                    "title": f"Exception: {e.type}",
                    "message": f"Order {order.tracking_number}",
                    "entity_type": "order",
                    "entity_id": order.id,
                    "location": {"lat": coords[0], "lng": coords[1]} if coords else None,
                    "created_at": e.created_at.isoformat() if e.created_at else None,
                }
            )
        # Open claims
        for c in db.query(Claim).filter(Claim.status == "open").limit(10).all():
            alerts.append(
                {
                    "id": f"claim-{c.id}",
                    "alert_type": "claim",
                    "severity": "info",
                    "title": f"Open claim: {c.claim_type}",
                    "message": c.description or "Claim requires review",
                    "entity_type": "order",
                    "entity_id": c.order_id,
                    "location": None,
                    "created_at": c.created_at.isoformat() if c.created_at else None,
                }
            )
        # High priority in-flight
        for o in db.query(Order).filter(Order.state.in_(IN_FLIGHT), Order.amount_cents >= HIGH_PRIORITY_CENTS).limit(10).all():
            coords = _coords(o.pickup)
            alerts.append(
                {
                    "id": f"priority-{o.id}",
                    "alert_type": "high_priority",
                    "severity": "warning",
                    "title": "High priority order",
                    "message": o.tracking_number,
                    "entity_type": "order",
                    "entity_id": o.id,
                    "location": {"lat": coords[0], "lng": coords[1]} if coords else None,
                    "created_at": o.created_at.isoformat() if o.created_at else None,
                }
            )
        seen_ids: set[str] = set()
        unique_alerts: list[dict] = []
        for alert in alerts:
            aid = alert["id"]
            if aid in seen_ids:
                continue
            seen_ids.add(aid)
            unique_alerts.append(alert)
        return unique_alerts[:100]

    def _build_events(self, db: Session, *, limit: int = 40) -> list[dict]:
        rows = db.query(DomainEvent).order_by(DomainEvent.occurred_at.desc()).limit(limit).all()
        events: list[dict] = []
        for e in rows:
            events.append(
                {
                    "id": e.id,
                    "event_type": e.event_type,
                    "source": "porterchain",
                    "title": e.event_type.replace(".", " ").replace("_", " ").title(),
                    "aggregate_type": e.aggregate_type,
                    "aggregate_id": e.aggregate_id,
                    "occurred_at": e.occurred_at.isoformat() if e.occurred_at else None,
                }
            )
        return events

    def _command_center(self, db: Session) -> dict[str, int]:
        stats = self._tower.stats(db)
        delayed_drivers = (
            db.query(func.count(Driver.id))
            .filter(Driver.is_online.is_(False), Driver.availability == "busy")
            .scalar()
            or 0
        )
        return {
            "orders_today": stats["orders_today"],
            "drivers_online": stats["drivers_online"],
            "vehicles_active": stats["vehicles_active"],
            "orders_waiting": stats["waiting_dispatch"],
            "late_orders": stats["delayed_orders"],
            "delayed_drivers": int(delayed_drivers),
            "support_tickets": stats["support_tickets"],
            "revenue_today_cents": stats["revenue_today_cents"],
            "open_claims": stats["open_claims"],
            "open_exceptions": stats["open_exceptions"],
        }

    def _heat_maps(self, orders: list[dict], drivers: list[dict]) -> dict[str, list[dict]]:
        pickups = [o["location"] for o in orders if o["stop_type"] == "pickup"]
        deliveries = [o["location"] for o in orders if o["stop_type"] == "delivery"]
        driver_pts = [d["location"] for d in drivers if d.get("location")]
        return {
            "orders": [{**p, "weight": 1.0} for p in pickups + deliveries],
            "pickups": [{**p, "weight": 1.0} for p in pickups],
            "deliveries": [{**p, "weight": 1.0} for p in deliveries],
            "drivers": [{**p, "weight": 1.0} for p in driver_pts],
            "revenue": [
                {**o["location"], "weight": max(1.0, o.get("amount_cents", 0) / 10000)}
                for o in orders
                if o.get("amount_cents")
            ],
        }

    def _smart_insights(
        self, db: Session, drivers: list[dict], orders: list[dict], now: datetime
    ) -> dict[str, Any]:
        online_with_loc = [d for d in drivers if d.get("online") and d.get("location")]
        waiting = [o for o in orders if o["state"] in WAITING and o["stop_type"] == "pickup"]
        nearest: list[dict] = []
        if waiting and online_with_loc:
            target = waiting[0]["location"]
            ranked = sorted(
                online_with_loc,
                key=lambda d: _haversine_km(target["lat"], target["lng"], d["location"]["lat"], d["location"]["lng"]),
            )
            nearest = ranked[:5]

        ai = self._tower.ai_ops(db)
        suggested_ids = {d["id"] for d in ai["suggested_drivers"]}
        suggested = [d for d in drivers if d["id"] in suggested_ids]

        delay_predictions = []
        for o in orders:
            if o["state"] not in IN_FLIGHT or not o.get("eta"):
                continue
            try:
                eta = _parse_iso_naive(o["eta"])
                if eta < now:
                    delay_predictions.append(
                        {
                            "order_id": o["order_id"],
                            "tracking_number": o["tracking_number"],
                            "minutes_late": int((now - eta).total_seconds() / 60),
                        }
                    )
            except ValueError:
                pass

        return {
            "nearest_drivers": nearest,
            "suggested_drivers": suggested,
            "delay_predictions": delay_predictions[:25],
            "traffic_warnings": ["Monitor Gardiner Expressway — typical afternoon congestion"] if delay_predictions else [],
            "route_risks": ai["risk_orders"][:10],
            "merchant_health": [],
            "driver_health": [
                {"driver_id": d["id"], "name": d["name"], "status": "offline_with_job"}
                for d in drivers
                if not d["online"] and d.get("current_order_id")
            ][:10],
        }

    def _weather_stub(self) -> dict[str, Any]:
        return {
            "temperature_c": 18,
            "conditions": "partly_cloudy",
            "wind_kmh": 12,
            "visibility_km": 16,
            "precipitation": "none",
            "note": "Weather overlay uses Porterchain ops feed — connect external provider via adapter when enabled",
        }

    # ------------------------------------------------------------------ #
    # Search
    # ------------------------------------------------------------------ #
    def search(self, db: Session, query: str, *, limit: int = 30) -> list[dict]:
        q = query.strip()
        if len(q) < 2:
            return []
        like = f"%{q}%"
        results: list[dict] = []

        for d in db.query(Driver).filter(or_(Driver.full_name.ilike(like), Driver.phone.ilike(like), Driver.email.ilike(like))).limit(limit).all():
            results.append({"type": "driver", "id": d.id, "label": d.full_name, "subtitle": d.phone, "location": None})

        for v in db.query(Vehicle).filter(Vehicle.plate_number.ilike(like)).limit(limit).all():
            results.append({"type": "vehicle", "id": v.id, "label": v.plate_number, "subtitle": v.vehicle_class, "location": None})

        for m in db.query(Merchant).filter(or_(Merchant.company_name.ilike(like), Merchant.email.ilike(like), Merchant.phone.ilike(like))).limit(limit).all():
            results.append({"type": "merchant", "id": m.id, "label": m.company_name, "subtitle": m.email, "location": None})

        for c in db.query(Customer).filter(or_(Customer.email.ilike(like), Customer.phone.ilike(like))).limit(limit).all():
            results.append({"type": "customer", "id": c.id, "label": c.email, "subtitle": c.phone, "location": None})

        for o in db.query(Order).filter(
            or_(Order.tracking_number.ilike(like), Order.order_number.ilike(like))
        ).limit(limit).all():
            coords = _coords(o.pickup) or _coords(o.dropoff)
            results.append(
                {
                    "type": "order",
                    "id": o.id,
                    "label": o.tracking_number,
                    "subtitle": o.state,
                    "location": {"lat": coords[0], "lng": coords[1]} if coords else None,
                }
            )

        return results[:limit]

    # ------------------------------------------------------------------ #
    # Entity detail (drawer)
    # ------------------------------------------------------------------ #
    def entity_detail(self, db: Session, entity_type: str, entity_id: str) -> dict[str, Any]:
        if entity_type == "driver":
            return self._driver_detail(db, entity_id)
        if entity_type == "vehicle":
            return self._vehicle_detail(db, entity_id)
        if entity_type == "merchant":
            return self._merchant_detail(db, entity_id)
        if entity_type == "customer":
            return self._customer_detail(db, entity_id)
        if entity_type == "order":
            return self._order_detail(db, entity_id)
        raise LookupError("entity_not_found")

    def _driver_detail(self, db: Session, driver_id: str) -> dict:
        d = db.query(Driver).filter(Driver.id == driver_id).first()
        if not d:
            raise LookupError("entity_not_found")
        pings = self._latest_pings(db)
        ping = pings.get(d.id)
        active = (
            db.query(Order)
            .filter(Order.assigned_driver_id == d.id, Order.state.in_(IN_FLIGHT))
            .first()
        )
        vehicle = db.query(Vehicle).filter(Vehicle.driver_id == d.id, Vehicle.is_active.is_(True)).first()
        timeline = [
            {
                "label": "Driver registered",
                "at": d.created_at.isoformat() if d.created_at else None,
            }
        ]
        if active:
            timeline.append({"label": f"Active order {active.tracking_number}", "at": active.updated_at.isoformat() if active.updated_at else None})
        return {
            "entity_type": "driver",
            "entity_id": d.id,
            "title": d.full_name,
            "subtitle": _driver_ref(d.id),
            "status": d.availability,
            "location": {"lat": ping.lat, "lng": ping.lng} if ping else None,
            "contact": {"phone": d.phone, "email": d.email},
            "current_job": {
                "order_id": active.id,
                "tracking_number": active.tracking_number,
                "state": active.state,
            }
            if active
            else None,
            "timeline": timeline,
            "eta": active.scheduled_at.isoformat() if active and active.scheduled_at else None,
            "notes": [],
            "actions": [
                {"key": "open_driver", "label": "Open Driver", "href": f"/drivers/{d.id}"},
                {"key": "call", "label": "Call Driver", "href": f"tel:{d.phone}" if d.phone else "#"},
            ],
            "meta": {
                "rating": d.rating,
                "vehicle": vehicle.vehicle_class if vehicle else None,
                "online": d.is_online,
            },
        }

    def _vehicle_detail(self, db: Session, vehicle_id: str) -> dict:
        v = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
        if not v:
            raise LookupError("entity_not_found")
        driver = db.query(Driver).filter(Driver.id == v.driver_id).first() if v.driver_id else None
        return {
            "entity_type": "vehicle",
            "entity_id": v.id,
            "title": v.plate_number,
            "subtitle": v.make_model or v.vehicle_class,
            "status": "active" if v.is_active else "inactive",
            "location": None,
            "contact": {},
            "current_job": None,
            "timeline": [],
            "eta": None,
            "notes": [],
            "actions": [
                {"key": "open_vehicle", "label": "Open Vehicle", "href": f"/drivers/{v.driver_id}" if v.driver_id else "#"},
            ],
            "meta": {"vehicle_class": v.vehicle_class, "driver_name": driver.full_name if driver else None},
        }

    def _merchant_detail(self, db: Session, merchant_id: str) -> dict:
        m = db.query(Merchant).filter(Merchant.id == merchant_id).first()
        if not m:
            raise LookupError("entity_not_found")
        addr = db.query(SavedAddress).filter(SavedAddress.merchant_id == m.id).first()
        loc = {"lat": addr.lat, "lng": addr.lng} if addr and addr.lat and addr.lng else None
        return {
            "entity_type": "merchant",
            "entity_id": m.id,
            "title": m.company_name,
            "subtitle": _merchant_ref(m.id),
            "status": m.status,
            "location": loc,
            "contact": {"phone": m.phone, "email": m.email},
            "current_job": None,
            "timeline": [],
            "eta": None,
            "notes": [],
            "actions": [
                {"key": "open_merchant", "label": "Open Merchant", "href": f"/merchants/{m.id}"},
                {"key": "email", "label": "Email Merchant", "href": f"mailto:{m.email}"},
            ],
            "meta": {},
        }

    def _customer_detail(self, db: Session, customer_id: str) -> dict:
        c = db.query(Customer).filter(Customer.id == customer_id).first()
        if not c:
            raise LookupError("entity_not_found")
        return {
            "entity_type": "customer",
            "entity_id": c.id,
            "title": c.email,
            "subtitle": c.phone,
            "status": "active",
            "location": None,
            "contact": {"phone": c.phone, "email": c.email},
            "current_job": None,
            "timeline": [],
            "eta": None,
            "notes": [],
            "actions": [],
            "meta": {},
        }

    def _order_detail(self, db: Session, order_id: str) -> dict:
        o = db.query(Order).filter(Order.id == order_id).first()
        if not o:
            raise LookupError("entity_not_found")
        merchant = db.query(Merchant).filter(Merchant.id == o.merchant_id).first() if o.merchant_id else None
        driver = db.query(Driver).filter(Driver.id == o.assigned_driver_id).first() if o.assigned_driver_id else None
        events = (
            db.query(DomainEvent)
            .filter(DomainEvent.aggregate_type == "order", DomainEvent.aggregate_id == o.id)
            .order_by(DomainEvent.occurred_at.asc())
            .limit(30)
            .all()
        )
        coords = _coords(o.dropoff) or _coords(o.pickup)
        return {
            "entity_type": "order",
            "entity_id": o.id,
            "title": o.tracking_number,
            "subtitle": o.order_number,
            "status": o.state,
            "location": {"lat": coords[0], "lng": coords[1]} if coords else None,
            "contact": {},
            "current_job": {
                "driver": driver.full_name if driver else None,
                "merchant": merchant.company_name if merchant else None,
                "pickup": (o.pickup or {}).get("formatted"),
                "dropoff": (o.dropoff or {}).get("formatted"),
            },
            "timeline": [
                {"label": e.event_type, "at": e.occurred_at.isoformat() if e.occurred_at else None}
                for e in events
            ],
            "eta": o.scheduled_at.isoformat() if o.scheduled_at else None,
            "notes": [],
            "actions": [
                {"key": "open_order", "label": "Open Order", "href": f"/orders?search={o.tracking_number}"},
                {"key": "timeline", "label": "Open Timeline", "href": f"/orders?search={o.tracking_number}"},
            ],
            "meta": {
                "amount_cents": o.amount_cents,
                "vehicle_class": _order_vehicle_class(o),
                "priority": "high" if o.amount_cents >= HIGH_PRIORITY_CENTS else "normal",
            },
        }

    # ------------------------------------------------------------------ #
    # Playback
    # ------------------------------------------------------------------ #
    def playback(self, db: Session, *, day: str, driver_id: str | None = None) -> dict[str, Any]:
        try:
            target = date.fromisoformat(day)
        except ValueError as exc:
            raise ValueError("invalid_date") from exc
        sod = datetime.combine(target, time.min)
        eod = datetime.combine(target, time.max)
        q = db.query(DriverLocationPing).filter(
            DriverLocationPing.created_at >= sod, DriverLocationPing.created_at <= eod
        )
        if driver_id:
            q = q.filter(DriverLocationPing.driver_id == driver_id)
        pings = q.order_by(DriverLocationPing.created_at.asc()).limit(2000).all()
        frames = [
            {
                "ts": p.created_at.isoformat() if p.created_at else None,
                "driver_id": p.driver_id,
                "lat": p.lat,
                "lng": p.lng,
                "heading": p.heading,
                "speed_kmh": round(p.speed_mps * 3.6, 1) if p.speed_mps else None,
            }
            for p in pings
        ]
        stops: list[dict] = []
        orders_q = db.query(Order).filter(Order.updated_at >= sod, Order.updated_at <= eod)
        if driver_id:
            orders_q = orders_q.filter(Order.assigned_driver_id == driver_id)
        for o in orders_q.limit(200).all():
            pickup = _coords(o.pickup)
            dropoff = _coords(o.dropoff)
            if pickup:
                stops.append({"order_id": o.id, "stop_type": "pickup", "location": {"lat": pickup[0], "lng": pickup[1]}, "at": o.updated_at.isoformat() if o.updated_at else None})
            if dropoff:
                stops.append({"order_id": o.id, "stop_type": "delivery", "location": {"lat": dropoff[0], "lng": dropoff[1]}, "at": o.updated_at.isoformat() if o.updated_at else None})
        incidents_q = db.query(DriverIncident).filter(DriverIncident.created_at >= sod, DriverIncident.created_at <= eod)
        if driver_id:
            incidents_q = incidents_q.filter(DriverIncident.driver_id == driver_id)
        incidents = [
            {
                "id": i.id,
                "type": i.incident_type,
                "driver_id": i.driver_id,
                "order_id": i.order_id,
                "at": i.created_at.isoformat() if i.created_at else None,
            }
            for i in incidents_q.limit(50).all()
        ]
        return {"date": day, "driver_id": driver_id, "frames": frames, "stops": stops, "incidents": incidents}

    def nearest_drivers(self, db: Session, *, lat: float, lng: float, limit: int = 5) -> list[dict]:
        snapshot = self.snapshot(db)
        ranked = []
        for d in snapshot["drivers"]:
            if not d.get("location") or not d.get("online"):
                continue
            dist = _haversine_km(lat, lng, d["location"]["lat"], d["location"]["lng"])
            ranked.append({**d, "distance_km": round(dist, 2)})
        ranked.sort(key=lambda x: x["distance_km"])
        return ranked[:limit]
