"""Merchant tracking — orchestrates Fleetbase tracking, OSRM ETA, Valhalla routes (masterrule §3).

Google Maps renders only on the client. Fleetbase provides live GPS/status/POD.
OSRM provides ETA. Valhalla provides optimized route geometry.
"""

from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.order_engine.buckets import IN_FLIGHT
from porterchain_api.admin_models import Driver, PricingZone, Vehicle
from porterchain_api.config import Settings
from porterchain_api.fleetbase_engine.tracking_facade import TrackingFacade
from porterchain_api.merchant_engine.rbac import MerchantContext
from porterchain_api.models import Order, OrderEvent
from porterchain_services.maps.route_helpers import optimized_route_from_valhalla
from porterchain_services.maps.service import MapsService

IN_FLIGHT_STATES = IN_FLIGHT
_ETA_CACHE_TTL_SECONDS = 90
_eta_cache: dict[str, tuple[float, dict[str, Any]]] = {}


def _coords_from_address(addr: dict[str, Any] | None) -> tuple[float, float] | None:
    if not addr or not isinstance(addr, dict):
        return None
    lat = addr.get("lat")
    lng = addr.get("lng")
    if lat is None or lng is None:
        return None
    try:
        return float(lat), float(lng)
    except (TypeError, ValueError):
        return None


def _normalize_pod(proofs: list[dict[str, Any]]) -> dict[str, Any]:
    photos: list[dict[str, Any]] = []
    signatures: list[dict[str, Any]] = []
    otps: list[dict[str, Any]] = []
    other: list[dict[str, Any]] = []

    for proof in proofs:
        raw_type = str(proof.get("type") or proof.get("proof_type") or "").lower()
        normalized = {
            "id": proof.get("id") or proof.get("uuid") or proof.get("fleetbase_proof_id"),
            "type": raw_type,
            "url": proof.get("url") or proof.get("file_url"),
            "captured_at": proof.get("captured_at") or proof.get("created_at"),
            "signature": proof.get("signature"),
            "notes": proof.get("notes") or proof.get("comment"),
            "otp": proof.get("otp") or proof.get("barcode") or proof.get("code"),
        }
        if raw_type in ("photo", "image", "picture"):
            photos.append(normalized)
        elif raw_type in ("signature", "sign"):
            signatures.append(normalized)
        elif raw_type in ("otp", "barcode", "pin", "code"):
            otps.append(normalized)
        else:
            other.append(normalized)

    return {
        "photos": photos,
        "signatures": signatures,
        "otp": otps,
        "other": other,
        "complete": bool(photos or signatures or otps),
    }


class MerchantTrackingService:
    def __init__(self) -> None:
        from porterchain_api.booking_engine.repositories.order_repository import OrderRepository

        self._tracking = TrackingFacade()
        self._maps = MapsService()
        self._order_repo = OrderRepository()

    def dashboard(self, db: Session, settings: Settings, ctx: MerchantContext) -> dict[str, Any]:
        orders = (
            db.query(Order)
            .filter(Order.merchant_id == ctx.merchant.id, Order.state.in_(IN_FLIGHT_STATES))
            .order_by(Order.scheduled_at.asc())
            .limit(100)
            .all()
        )
        active: list[dict[str, Any]] = []
        for order in orders:
            snapshot = self._lightweight_snapshot(db, settings, order)
            active.append(snapshot)

        return {
            "active_count": len(active),
            "orders": active,
            "geofences": self._merchant_geofences(db, ctx),
            "updated_at": datetime.now(UTC).isoformat(),
        }

    def live_tracking(
        self,
        db: Session,
        settings: Settings,
        ctx: MerchantContext,
        order_id: str,
    ) -> dict[str, Any]:
        order = self._order_repo.get_for_merchant(db, ctx.merchant.id, order_id)
        if not order:
            raise LookupError("order_not_found")
        return self._full_snapshot(db, settings, ctx, order)

    def track_by_number(
        self,
        db: Session,
        settings: Settings,
        ctx: MerchantContext,
        tracking_number: str,
    ) -> dict[str, Any]:
        order = self._order_repo.get_by_tracking_for_merchant(db, ctx.merchant.id, tracking_number)
        if not order:
            raise LookupError("order_not_found")
        return self._full_snapshot(db, settings, ctx, order)

    def _lightweight_snapshot(self, db: Session, settings: Settings, order: Order) -> dict[str, Any]:
        live_raw = self._fetch_live(db, settings, order)
        translated = self._translate_live(live_raw)
        driver_loc = translated.get("location")
        dropoff = _coords_from_address(order.dropoff if isinstance(order.dropoff, dict) else None)
        eta = self._osrm_eta(driver_loc, dropoff, order_id=order.id) if driver_loc and dropoff else None

        driver = self._driver_info(db, order, live_raw)
        vehicle = self._vehicle_info(db, order, live_raw)

        return {
            "order_id": order.id,
            "tracking_number": order.tracking_number,
            "state": order.state,
            "scheduled_at": order.scheduled_at.isoformat() if order.scheduled_at else None,
            "pickup": order.pickup,
            "dropoff": order.dropoff,
            "driver": driver,
            "vehicle": vehicle,
            "driver_location": driver_loc,
            "eta": eta,
            "delivery_status": self._delivery_status(order.state, translated),
            "last_updated": translated.get("last_updated"),
        }

    def _full_snapshot(
        self,
        db: Session,
        settings: Settings,
        ctx: MerchantContext,
        order: Order,
    ) -> dict[str, Any]:
        live_raw = self._fetch_live(db, settings, order)
        translated = self._translate_live(live_raw)
        pickup = _coords_from_address(order.pickup if isinstance(order.pickup, dict) else None)
        dropoff = _coords_from_address(order.dropoff if isinstance(order.dropoff, dict) else None)
        driver_loc = translated.get("location")

        eta_origin = driver_loc or pickup
        eta = self._osrm_eta(eta_origin, dropoff, order_id=order.id) if eta_origin and dropoff else None
        optimized_route = self._valhalla_route(pickup, dropoff) if pickup and dropoff else None

        proofs = self._extract_proofs(live_raw)
        history = self._tracking_history(db, order.id)
        pod = _normalize_pod(proofs)
        pod_events = [ev for ev in history if "pod" in str(ev.get("event_type", "")).lower()]
        if not pod["complete"] and pod_events:
            last_payload = pod_events[-1].get("payload")
            if isinstance(last_payload, dict):
                pod = {**pod, **last_payload}

        replay = self._build_replay(history, translated.get("activity") or [], live_raw)
        notifications = self._order_notifications(db, ctx.merchant.id, order.id)

        return {
            "order_id": order.id,
            "tracking_number": order.tracking_number,
            "order_number": order.order_number,
            "state": order.state,
            "scheduled_at": order.scheduled_at.isoformat() if order.scheduled_at else None,
            "pickup": order.pickup,
            "dropoff": order.dropoff,
            "fleetbase_order_id": order.fleetbase_order_id,
            "driver": self._driver_info(db, order, live_raw),
            "vehicle": self._vehicle_info(db, order, live_raw),
            "driver_location": driver_loc,
            "live": translated,
            "fleetbase": live_raw,
            "eta": eta,
            "optimized_route": optimized_route,
            "delivery_status": self._delivery_status(order.state, translated),
            "timeline": history,
            "tracking_history": history,
            "replay": replay,
            "proof_of_delivery": pod,
            "geofences": self._merchant_geofences(db, ctx, order=order),
            "notifications": notifications,
            "last_updated": translated.get("last_updated") or datetime.now(UTC).isoformat(),
        }

    def _fetch_live(self, db: Session, settings: Settings, order: Order) -> dict[str, Any] | None:
        if not order.fleetbase_order_id:
            return None
        try:
            return self._tracking.fetch_raw(settings, order)
        except Exception:
            return None

    def _translate_live(self, live_raw: dict[str, Any] | None) -> dict[str, Any]:
        return TrackingFacade.translate_live(live_raw)

    def _extract_proofs(self, live_raw: dict[str, Any] | None) -> list[dict[str, Any]]:
        if not live_raw:
            return []
        proofs = live_raw.get("proofs")
        if isinstance(proofs, list):
            return proofs
        return []

    def _osrm_eta(
        self,
        origin: dict[str, float] | tuple[float, float] | None,
        destination: tuple[float, float] | None,
        *,
        order_id: str | None = None,
    ) -> dict[str, Any] | None:
        if not origin or not destination:
            return None
        if isinstance(origin, dict):
            o_lat, o_lng = origin.get("lat"), origin.get("lng")
            if o_lat is None or o_lng is None:
                return None
            origin_pt = (float(o_lat), float(o_lng))
        else:
            origin_pt = origin

        cache_key = (
            f"{order_id}:{origin_pt[0]:.4f},{origin_pt[1]:.4f}:"
            f"{destination[0]:.4f},{destination[1]:.4f}"
            if order_id
            else None
        )
        if cache_key:
            cached = _get_cached_eta(cache_key)
            if cached is not None:
                return cached

        result = self._maps._osrm_route(origin_pt, destination)
        if not result or result.get("code") != "Ok" or not result.get("routes"):
            return None
        route = result["routes"][0]
        duration = int(route.get("duration", 0))
        distance = int(route.get("distance", 0))
        arrives_at = (datetime.now(UTC) + timedelta(seconds=duration)).isoformat()
        eta = {
            "source": "osrm",
            "duration_seconds": duration,
            "distance_meters": distance,
            "polyline": route.get("geometry"),
            "arrives_at": arrives_at,
            "label": self._format_eta_label(duration),
        }
        if cache_key:
            _set_cached_eta(cache_key, eta)
        return eta

    def _valhalla_route(
        self,
        origin: tuple[float, float] | None,
        destination: tuple[float, float] | None,
    ) -> dict[str, Any] | None:
        if not origin or not destination:
            return None
        result = self._maps._valhalla_route(origin, destination)
        return optimized_route_from_valhalla(result)

    def _driver_info(
        self,
        db: Session,
        order: Order,
        live_raw: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        fb_driver = None
        if live_raw:
            tracker = live_raw.get("tracker") if isinstance(live_raw.get("tracker"), dict) else live_raw
            fb_driver = live_raw.get("driver") or tracker.get("driver") if isinstance(tracker, dict) else None

        driver = None
        if order.assigned_driver_id:
            driver = db.query(Driver).filter(Driver.id == order.assigned_driver_id).first()

        if driver:
            return {
                "id": driver.id,
                "name": driver.full_name,
                "phone": driver.phone,
                "is_online": fb_driver.get("online") if isinstance(fb_driver, dict) else None,
                "rating": driver.rating,
                "fleetbase": fb_driver,
            }
        if isinstance(fb_driver, dict):
            return {
                "id": fb_driver.get("id"),
                "name": fb_driver.get("name"),
                "phone": fb_driver.get("phone"),
                "fleetbase": fb_driver,
            }
        return None

    def _vehicle_info(
        self,
        db: Session,
        order: Order,
        live_raw: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        fb_vehicle = None
        if live_raw and isinstance(live_raw.get("tracker"), dict):
            tracker = live_raw["tracker"]
            fb_vehicle = tracker.get("vehicle") or tracker.get("order", {}).get("vehicle")

        vehicle = None
        if order.assigned_driver_id:
            driver = db.query(Driver).filter(Driver.id == order.assigned_driver_id).first()
            if driver and driver.vehicles:
                vehicle = next((v for v in driver.vehicles if v.is_active), driver.vehicles[0])

        if vehicle:
            return {
                "id": vehicle.id,
                "label": f"{vehicle.make_model or vehicle.vehicle_class} ({vehicle.plate_number})",
                "vehicle_class": vehicle.vehicle_class,
                "plate_number": vehicle.plate_number,
                "fleetbase": fb_vehicle,
            }
        if isinstance(fb_vehicle, dict):
            return {
                "id": fb_vehicle.get("id"),
                "label": fb_vehicle.get("name") or fb_vehicle.get("plate_number"),
                "vehicle_class": fb_vehicle.get("vehicle_class"),
                "plate_number": fb_vehicle.get("plate_number"),
                "fleetbase": fb_vehicle,
            }
        return None

    def _tracking_history(self, db: Session, order_id: str) -> list[dict[str, Any]]:
        events = (
            db.query(OrderEvent)
            .filter(OrderEvent.order_id == order_id)
            .order_by(OrderEvent.occurred_at.asc())
            .all()
        )
        return [
            {
                "event_type": ev.event_type,
                "label": ev.event_type.replace(".", " ").replace("_", " ").title(),
                "from_state": ev.from_state,
                "to_state": ev.to_state,
                "occurred_at": ev.occurred_at.isoformat() if ev.occurred_at else None,
                "payload": ev.payload,
                "location": (ev.payload or {}).get("location") if isinstance(ev.payload, dict) else None,
            }
            for ev in events
        ]

    def _build_replay(
        self,
        history: list[dict[str, Any]],
        activity: list[dict[str, Any]],
        live_raw: dict[str, Any] | None,
    ) -> list[dict[str, Any]]:
        frames: list[dict[str, Any]] = []
        seen: set[str] = set()

        def add_frame(lat: float, lng: float, at: str | None, source: str) -> None:
            key = f"{lat:.5f},{lng:.5f},{at}"
            if key in seen:
                return
            seen.add(key)
            frames.append({"lat": lat, "lng": lng, "at": at, "source": source})

        for item in activity:
            loc = item.get("location")
            if isinstance(loc, dict) and loc.get("lat") is not None and loc.get("lng") is not None:
                add_frame(float(loc["lat"]), float(loc["lng"]), item.get("at"), "fleetbase_activity")

        for ev in history:
            loc = ev.get("location")
            if isinstance(loc, dict) and loc.get("lat") is not None and loc.get("lng") is not None:
                add_frame(float(loc["lat"]), float(loc["lng"]), ev.get("occurred_at"), "order_event")

        if live_raw:
            tracker = live_raw.get("tracker") if isinstance(live_raw.get("tracker"), dict) else live_raw
            for key in ("coordinates", "position", "location"):
                loc = live_raw.get(key) or (tracker.get(key) if isinstance(tracker, dict) else None)
                if isinstance(loc, dict) and loc.get("lat") is not None and loc.get("lng") is not None:
                    add_frame(
                        float(loc["lat"]),
                        float(loc["lng"]),
                        live_raw.get("last_updated") or live_raw.get("updated_at"),
                        "fleetbase_live",
                    )

        frames.sort(key=lambda f: str(f.get("at") or ""))
        return frames

    def _merchant_geofences(
        self,
        db: Session,
        ctx: MerchantContext,
        *,
        order: Order | None = None,
    ) -> list[dict[str, Any]]:
        zones: list[dict[str, Any]] = []
        codes = list(ctx.merchant.delivery_zones or [])
        if codes:
            rows = (
                db.query(PricingZone)
                .filter(PricingZone.is_active.is_(True), PricingZone.code.in_(codes))
                .all()
            )
            for z in rows:
                zones.append(
                    {
                        "id": z.id,
                        "code": z.code,
                        "name": z.name,
                        "geofence_type": "delivery_zone",
                        "bounds": z.bounds or {},
                    }
                )
            for code in codes:
                if not any(z["code"] == code for z in zones):
                    zones.append(
                        {
                            "id": code,
                            "code": code,
                            "name": code,
                            "geofence_type": "delivery_zone",
                            "bounds": {},
                        }
                    )

        if order:
            for label, addr in (("pickup", order.pickup), ("dropoff", order.dropoff)):
                coords = _coords_from_address(addr if isinstance(addr, dict) else None)
                if coords:
                    zones.append(
                        {
                            "id": f"{order.id}-{label}",
                            "name": f"{label.title()} — {order.tracking_number}",
                            "geofence_type": label,
                            "center": {"lat": coords[0], "lng": coords[1]},
                            "radius_m": 150,
                        }
                    )
        return zones

    def _order_notifications(self, db: Session, merchant_id: str, order_id: str) -> list[dict[str, Any]]:
        try:
            from porterchain_api.notification_engine.models import NotificationRecord

            rows = (
                db.query(NotificationRecord)
                .filter(
                    NotificationRecord.recipient_type == "merchant",
                    NotificationRecord.recipient_id == merchant_id,
                )
                .order_by(NotificationRecord.created_at.desc())
                .limit(50)
                .all()
            )
            matched = []
            for r in rows:
                ctx = r.context if isinstance(r.context, dict) else {}
                if ctx.get("order_id") == order_id or order_id in (r.deep_link or ""):
                    matched.append(r)
            return [
                {
                    "id": r.id,
                    "title": r.title,
                    "body": r.body,
                    "category": r.category,
                    "is_read": r.is_read,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in matched[:20]
            ]
        except Exception:
            return []

    def _delivery_status(self, order_state: str, translated: dict[str, Any]) -> dict[str, Any]:
        fb_status = translated.get("fleetbase_status")
        return {
            "order_state": order_state,
            "fleetbase_status": fb_status,
            "label": order_state.replace("_", " ").title(),
            "in_transit": order_state in IN_FLIGHT_STATES,
            "delivered": order_state in ("DELIVERED", "POD_COMPLETED", "INVOICED", "CLOSED"),
        }

    @staticmethod
    def _format_eta_label(seconds: int) -> str:
        if seconds < 60:
            return "< 1 min"
        minutes = seconds // 60
        if minutes < 60:
            return f"{minutes} min"
        hours, rem = divmod(minutes, 60)
        return f"{hours}h {rem}m"


def _get_cached_eta(cache_key: str) -> dict[str, Any] | None:
    entry = _eta_cache.get(cache_key)
    if not entry:
        return None
    expires_at, eta = entry
    if time.time() > expires_at:
        _eta_cache.pop(cache_key, None)
        return None
    return eta


def _set_cached_eta(cache_key: str, eta: dict[str, Any]) -> None:
    _eta_cache[cache_key] = (time.time() + _ETA_CACHE_TTL_SECONDS, eta)
