"""Merchant tracking — PorterChain order + Redis GPS + Valhalla ETA (masterrule §3).

Google Maps renders only on the client. Live pin and status come from PorterChain.
OSRM is a labeled ETA fallback when Valhalla is down. Valhalla provides route geometry.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.order_engine.buckets import IN_FLIGHT
from porterchain_api.config import Settings
from porterchain_api.reporting.pod_normalize import normalize_pod
from porterchain_api.booking_engine.tracking_normalize import TrackingFacade
from porterchain_api.merchant_engine.organization_sync import public_shipper_branding
from porterchain_api.merchant_engine.rbac import MerchantContext
from porterchain_api.merchant_engine.tracking_views import (
    AmbiguousTrackingQuery,
    build_replay,
    coords_from_address,
    delivery_status,
    driver_info,
    format_eta_label,
    get_cached_eta,
    merchant_geofences,
    merchant_snapshot,
    public_track_url,
    set_cached_eta,
    tracking_error_message,
    tracking_history,
    vehicle_info,
)
from porterchain_api.booking_models import Order
from porterchain_services.maps.service import MapsService

IN_FLIGHT_STATES = IN_FLIGHT


#: Tracking and order 360 must show the same POD, with the same download
#: handles, so both read the one normalizer (BR).
_normalize_pod = normalize_pod


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
            snapshot = self._lightweight_snapshot(db, settings, order, ctx)
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
        """Track by tracking number, order number, or PO (BK).

        One PO can cover several drops. Tracking an arbitrary one of them would
        quietly show the wrong van, so an ambiguous PO asks the caller to choose.
        """
        matches = self._order_repo.find_for_merchant_lookup(db, ctx.merchant.id, tracking_number)
        if not matches:
            raise LookupError("tracking_not_found")
        if len(matches) > 1:
            raise AmbiguousTrackingQuery(tracking_number, matches)
        return self._full_snapshot(db, settings, ctx, matches[0])

    def _lightweight_snapshot(
        self, db: Session, settings: Settings, order: Order, ctx: MerchantContext
    ) -> dict[str, Any]:
        live_raw = self._fetch_live(db, settings, order)
        translated = self._translate_live(live_raw)
        driver_loc = self._driver_location(db, order, translated)
        dropoff = coords_from_address(order.dropoff if isinstance(order.dropoff, dict) else None)
        eta = self._eta(driver_loc, dropoff, order_id=order.id) if driver_loc and dropoff else None

        driver = self._driver_info(db, order, live_raw)
        vehicle = self._vehicle_info(db, order, live_raw)

        return self._merchant_snapshot(
            {
                "order_id": order.id,
                "tracking_number": order.tracking_number,
                "order_number": order.order_number,
                "state": order.state,
                "scheduled_at": order.scheduled_at.isoformat() if order.scheduled_at else None,
                "pickup": order.pickup,
                "dropoff": order.dropoff,
                "driver": driver,
                "vehicle": vehicle,
                "driver_location": driver_loc,
                "eta": eta,
                "delivery_status": self._delivery_status(order.state, translated),
                "public_track_url": public_track_url(
                    settings,
                    order.tracking_number,
                    is_sandbox=bool(getattr(order, "is_sandbox", False)),
                ),
                "is_sandbox": bool(getattr(order, "is_sandbox", False)),
                "branding": public_shipper_branding(ctx.merchant),
                "last_updated": translated.get("last_updated"),
            }
        )

    def _full_snapshot(
        self,
        db: Session,
        settings: Settings,
        ctx: MerchantContext,
        order: Order,
    ) -> dict[str, Any]:
        live_raw = self._fetch_live(db, settings, order)
        translated = self._translate_live(live_raw)
        pickup = coords_from_address(order.pickup if isinstance(order.pickup, dict) else None)
        dropoff = coords_from_address(order.dropoff if isinstance(order.dropoff, dict) else None)
        driver_loc = self._driver_location(db, order, translated)

        eta_origin = driver_loc or pickup
        eta = self._eta(eta_origin, dropoff, order_id=order.id) if eta_origin and dropoff else None
        optimized_route = self._route(pickup, dropoff) if pickup and dropoff else None

        proofs = self._extract_proofs(live_raw) + self._local_pod_proofs(db, order)
        history = self._tracking_history(db, order.id)
        pod = _normalize_pod(proofs)
        pod_events = [ev for ev in history if "pod" in str(ev.get("event_type", "")).lower()]
        if not pod["complete"] and pod_events:
            last_payload = pod_events[-1].get("payload")
            if isinstance(last_payload, dict):
                pod = {**pod, **last_payload}

        replay = self._build_replay(history, translated.get("activity") or [], live_raw)
        notifications = self._order_notifications(db, ctx.merchant.id, order.id)

        return self._merchant_snapshot(
            {
                "order_id": order.id,
                "tracking_number": order.tracking_number,
                "order_number": order.order_number,
                "state": order.state,
                "scheduled_at": order.scheduled_at.isoformat() if order.scheduled_at else None,
                "pickup": order.pickup,
                "dropoff": order.dropoff,
                "driver": self._driver_info(db, order, live_raw),
                "vehicle": self._vehicle_info(db, order, live_raw),
                "driver_location": driver_loc,
                "eta": eta,
                "optimized_route": optimized_route,
                "delivery_status": self._delivery_status(order.state, translated),
                "timeline": history,
                "tracking_history": history,
                "replay": replay,
                "proof_of_delivery": pod,
                "geofences": self._merchant_geofences(db, ctx, order=order),
                "notifications": notifications,
                "public_track_url": public_track_url(
                    settings,
                    order.tracking_number,
                    is_sandbox=bool(getattr(order, "is_sandbox", False)),
                ),
                "is_sandbox": bool(getattr(order, "is_sandbox", False)),
                "branding": public_shipper_branding(ctx.merchant),
                "last_updated": translated.get("last_updated") or datetime.now(UTC).isoformat(),
            }
        )

    @staticmethod
    def _merchant_snapshot(payload: dict[str, Any]) -> dict[str, Any]:
        return merchant_snapshot(payload)

    def _fetch_live(self, db: Session, settings: Settings, order: Order) -> dict[str, Any] | None:
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

    def _local_pod_proofs(self, db: Session, order: Order) -> list[dict[str, Any]]:
        from porterchain_api.driver_models import DriverStopMeta

        meta_row = db.query(DriverStopMeta).filter(DriverStopMeta.order_id == order.id).first()
        if not meta_row:
            return []
        mapped: list[dict[str, Any]] = []
        for item in list((meta_row.meta or {}).get("proofs", [])):
            if not isinstance(item, dict):
                continue
            ptype = str(item.get("type") or "")
            value = str(item.get("value") or "")
            proof: dict[str, Any] = {"type": ptype, "id": f"local-{order.id}-{ptype}"}
            if ptype == "photo":
                proof["url"] = value
            elif ptype == "signature":
                proof["signature"] = value
            elif ptype in {"otp", "barcode"}:
                proof["otp"] = value
            elif value:
                proof["url"] = value
            mapped.append(proof)
        return mapped

    def _driver_location(
        self,
        db: Session,
        order: Order,
        translated: dict[str, Any],
    ) -> dict[str, Any] | None:
        loc = translated.get("location")
        if loc:
            return loc
        driver_id = getattr(order, "assigned_driver_id", None)
        if not driver_id:
            return None
        from porterchain_api.dispatch_engine.driver_pin import driver_pin

        return driver_pin(driver_id)

    def _eta(
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
            cached = get_cached_eta(cache_key)
            if cached is not None:
                return cached

        result = self._maps.eta_between(origin_pt, destination)
        if not result:
            return None
        duration = int(result.get("duration_seconds", 0))
        arrives_at = (datetime.now(UTC) + timedelta(seconds=duration)).isoformat()
        eta = {
            **result,
            "arrives_at": arrives_at,
            "label": self._format_eta_label(duration),
        }
        if cache_key:
            set_cached_eta(cache_key, eta)
        return eta

    def _route(
        self,
        origin: tuple[float, float] | None,
        destination: tuple[float, float] | None,
    ) -> dict[str, Any] | None:
        if not origin or not destination:
            return None
        return self._maps.optimized_route(origin, destination)

    def _driver_info(
        self,
        db: Session,
        order: Order,
        live_raw: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        return driver_info(db, order, live_raw)

    def _vehicle_info(
        self,
        db: Session,
        order: Order,
        live_raw: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        return vehicle_info(db, order, live_raw)

    def _tracking_history(self, db: Session, order_id: str) -> list[dict[str, Any]]:
        return tracking_history(db, order_id)

    def _build_replay(
        self,
        history: list[dict[str, Any]],
        activity: list[dict[str, Any]],
        live_raw: dict[str, Any] | None,
    ) -> list[dict[str, Any]]:
        return build_replay(history, activity, live_raw)

    def _merchant_geofences(
        self,
        db: Session,
        ctx: MerchantContext,
        *,
        order: Order | None = None,
    ) -> list[dict[str, Any]]:
        return merchant_geofences(db, ctx, order=order)

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
        return delivery_status(order_state, in_flight=IN_FLIGHT_STATES)

    @staticmethod
    def _format_eta_label(seconds: int) -> str:
        return format_eta_label(seconds)
