"""Historical playback and nearest-driver queries for the live operations map."""

from __future__ import annotations

from datetime import date, datetime, time
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.admin_engine.live_map_helpers import _coords, _haversine_km
from porterchain_api.driver_models import DriverIncident, DriverLocationPing
from porterchain_api.models import Order


class LiveMapPlaybackMixin:
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
