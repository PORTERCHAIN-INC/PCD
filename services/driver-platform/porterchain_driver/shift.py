"""Driver shift lifecycle — start/end, breaks, availability modes, activity log."""

from __future__ import annotations

import math
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

AVAILABILITY_MODES = frozenset({"online", "offline", "busy", "idle", "on_break"})


class ShiftService:
    def snapshot(self, db: Session, driver: Any) -> dict[str, Any]:
        shift = self._active_shift(db, driver.id)
        route = None
        from porterchain_driver.stops import StopsService

        assigned = StopsService().assigned_route(db, driver)
        vehicle = None
        from porterchain_driver.vehicle import VehicleService

        vehicle = VehicleService().get_active_vehicle(db, driver.id)

        capacity = self._capacity_snapshot(db, driver, vehicle, assigned)
        mileage_km = self._mileage_for_shift(db, driver.id, shift) if shift else 0.0
        working = self._working_minutes(shift) if shift else 0

        timeline = self._timeline(db, driver.id, shift)
        activity_log = timeline[-50:]

        return {
            "shift_active": shift is not None,
            "shift": self._serialize_shift(shift) if shift else None,
            "availability": driver.availability or "offline",
            "is_online": bool(driver.is_online),
            "working_minutes": working,
            "working_hours_label": self._format_minutes(working),
            "mileage_km": round(mileage_km, 2),
            "current_vehicle": vehicle,
            "current_route": self._serialize_route(assigned) if assigned else None,
            "capacity": capacity,
            "timeline": timeline,
            "activity_log": activity_log,
            "last_updated": datetime.now(UTC).isoformat(),
        }

    def start_shift(
        self,
        db: Session,
        driver: Any,
        *,
        fleetbase_bridge: Any = None,
        route_id: str | None = None,
    ) -> dict[str, Any]:
        self._require_approved(driver)
        if self._active_shift(db, driver.id):
            raise PermissionError("shift_already_active")

        from porterchain_driver.vehicle import VehicleService
        from porterchain_driver.stops import StopsService

        vehicle = VehicleService().get_active_vehicle(db, driver.id)
        route = StopsService().assigned_route(db, driver)
        rid = route_id or (route.route_id if route else None)

        from porterchain_api.driver_models import DriverShift

        shift = DriverShift(
            driver_id=driver.id,
            status="active",
            vehicle_id=vehicle["id"] if vehicle else None,
            route_id=rid,
        )
        db.add(shift)
        db.flush()

        driver.is_online = True
        driver.availability = "idle"
        if fleetbase_bridge and driver.fleetbase_driver_id:
            fleetbase_bridge.toggle_driver_online(driver.fleetbase_driver_id, online=True)

        if route and rid and fleetbase_bridge:
            StopsService().start_route(db, driver, rid, fleetbase_bridge=fleetbase_bridge)

        self._log(db, driver.id, shift.id, "shift_started", {"route_id": rid, "vehicle_id": shift.vehicle_id})
        self._emit(db, driver, "driver.shift_started", {"shift_id": shift.id})
        db.flush()
        return self.snapshot(db, driver)

    def end_shift(self, db: Session, driver: Any, *, fleetbase_bridge: Any = None) -> dict[str, Any]:
        shift = self._active_shift(db, driver.id)
        if not shift:
            raise LookupError("no_active_shift")

        now = datetime.now(UTC)
        shift.status = "ended"
        shift.ended_at = now
        if shift.break_started_at:
            shift.break_minutes += int((now - shift.break_started_at).total_seconds() // 60)
            shift.break_started_at = None

        mileage = self._mileage_for_shift(db, driver.id, shift)
        shift.mileage_km = mileage

        driver.is_online = False
        driver.availability = "offline"
        if fleetbase_bridge and driver.fleetbase_driver_id:
            fleetbase_bridge.toggle_driver_online(driver.fleetbase_driver_id, online=False)

        self._log(db, driver.id, shift.id, "shift_ended", {"mileage_km": mileage})
        self._emit(db, driver, "driver.shift_ended", {"shift_id": shift.id, "mileage_km": mileage})
        db.flush()
        return self.snapshot(db, driver)

    def start_break(self, db: Session, driver: Any, *, fleetbase_bridge: Any = None) -> dict[str, Any]:
        shift = self._active_shift(db, driver.id)
        if not shift:
            raise LookupError("no_active_shift")
        if shift.status == "on_break":
            raise PermissionError("already_on_break")

        shift.status = "on_break"
        shift.break_started_at = datetime.now(UTC)
        driver.availability = "on_break"
        if fleetbase_bridge and driver.fleetbase_driver_id:
            fleetbase_bridge.toggle_driver_online(driver.fleetbase_driver_id, online=False)

        self._log(db, driver.id, shift.id, "break_started", {})
        self._emit(db, driver, "driver.break_started", {"shift_id": shift.id})
        db.flush()
        return self.snapshot(db, driver)

    def resume_shift(self, db: Session, driver: Any, *, fleetbase_bridge: Any = None) -> dict[str, Any]:
        shift = self._active_shift(db, driver.id)
        if not shift:
            raise LookupError("no_active_shift")
        if shift.status != "on_break":
            raise PermissionError("not_on_break")

        now = datetime.now(UTC)
        if shift.break_started_at:
            shift.break_minutes += int((now - shift.break_started_at).total_seconds() // 60)
            shift.break_started_at = None

        shift.status = "active"
        driver.is_online = True
        driver.availability = "idle"
        if fleetbase_bridge and driver.fleetbase_driver_id:
            fleetbase_bridge.toggle_driver_online(driver.fleetbase_driver_id, online=True)

        self._log(db, driver.id, shift.id, "break_resumed", {})
        self._emit(db, driver, "driver.break_resumed", {"shift_id": shift.id})
        db.flush()
        return self.snapshot(db, driver)

    def set_availability(
        self,
        db: Session,
        driver: Any,
        mode: str,
        *,
        fleetbase_bridge: Any = None,
    ) -> dict[str, Any]:
        self._require_approved(driver)
        mode = mode.lower()
        if mode not in AVAILABILITY_MODES:
            raise ValueError(f"invalid_availability_mode:{mode}")

        driver.availability = "available" if mode == "online" else mode
        driver.is_online = mode in ("online", "busy", "idle", "available")
        if mode == "online":
            driver.availability = "available"

        online_fb = mode in ("online", "busy", "idle", "available")
        if fleetbase_bridge and driver.fleetbase_driver_id:
            fleetbase_bridge.toggle_driver_online(driver.fleetbase_driver_id, online=online_fb)

        shift = self._active_shift(db, driver.id)
        self._log(
            db,
            driver.id,
            shift.id if shift else None,
            "availability_changed",
            {"mode": mode, "is_online": driver.is_online},
        )
        self._emit(
            db,
            driver,
            "driver.online" if online_fb else "driver.offline",
            {"availability": driver.availability},
        )
        db.flush()
        return self.snapshot(db, driver)

    def _active_shift(self, db: Session, driver_id: str):
        from porterchain_api.driver_models import DriverShift

        return (
            db.query(DriverShift)
            .filter(DriverShift.driver_id == driver_id, DriverShift.status.in_(("active", "on_break")))
            .order_by(DriverShift.started_at.desc())
            .first()
        )

    def _serialize_shift(self, shift: Any) -> dict[str, Any]:
        return {
            "id": shift.id,
            "status": shift.status,
            "started_at": shift.started_at.isoformat() if shift.started_at else None,
            "ended_at": shift.ended_at.isoformat() if shift.ended_at else None,
            "break_minutes": shift.break_minutes or 0,
            "mileage_km": shift.mileage_km or 0,
            "vehicle_id": shift.vehicle_id,
            "route_id": shift.route_id,
        }

    @staticmethod
    def _serialize_route(route: Any) -> dict[str, Any]:
        return {
            "route_id": route.route_id,
            "status": route.status,
            "stops_count": len(route.stops),
            "earnings_cents": route.earnings_cents,
            "started_at": route.started_at.isoformat() if route.started_at else None,
        }

    def _capacity_snapshot(
        self, db: Session, driver: Any, vehicle: dict | None, route: Any
    ) -> dict[str, Any]:
        max_kg = float(vehicle["capacity_kg"]) if vehicle and vehicle.get("capacity_kg") else None
        used_kg = 0.0
        stops = len(route.stops) if route else 0
        if route:
            from porterchain_api.models import Order, Quote

            order_ids = {s.order_id for s in route.stops}
            for oid in order_ids:
                order = db.query(Order).filter(Order.id == oid).first()
                if order and order.quote_id:
                    quote = db.query(Quote).filter(Quote.id == order.quote_id).first()
                    if quote and quote.weight_kg:
                        used_kg += float(quote.weight_kg)
        remaining = (max_kg - used_kg) if max_kg is not None else None
        return {
            "max_kg": max_kg,
            "used_kg": round(used_kg, 2),
            "remaining_kg": round(remaining, 2) if remaining is not None else None,
            "stops_count": stops,
            "utilization_percent": round((used_kg / max_kg) * 100, 1) if max_kg and max_kg > 0 else None,
        }

    def _mileage_for_shift(self, db: Session, driver_id: str, shift: Any) -> float:
        from porterchain_api.driver_models import DriverLocationPing

        end = shift.ended_at or datetime.now(UTC)
        pings = (
            db.query(DriverLocationPing)
            .filter(
                DriverLocationPing.driver_id == driver_id,
                DriverLocationPing.created_at >= shift.started_at,
                DriverLocationPing.created_at <= end,
            )
            .order_by(DriverLocationPing.created_at.asc())
            .all()
        )
        if len(pings) < 2:
            return float(shift.mileage_km or 0)
        total_m = 0.0
        for i in range(1, len(pings)):
            total_m += _haversine_m(pings[i - 1].lat, pings[i - 1].lng, pings[i].lat, pings[i].lng)
        return total_m / 1000.0

    def _working_minutes(self, shift: Any) -> int:
        if not shift or not shift.started_at:
            return 0
        end = shift.ended_at or datetime.now(UTC)
        total = int((end - shift.started_at).total_seconds() // 60)
        break_m = shift.break_minutes or 0
        if shift.status == "on_break" and shift.break_started_at:
            break_m += int((datetime.now(UTC) - shift.break_started_at).total_seconds() // 60)
        return max(0, total - break_m)

    def _timeline(self, db: Session, driver_id: str, shift: Any | None) -> list[dict[str, Any]]:
        from porterchain_api.driver_models import DriverShiftActivity

        q = db.query(DriverShiftActivity).filter(DriverShiftActivity.driver_id == driver_id)
        if shift:
            q = q.filter(DriverShiftActivity.shift_id == shift.id)
        rows = q.order_by(DriverShiftActivity.created_at.asc()).limit(100).all()
        return [
            {
                "id": r.id,
                "activity_type": r.activity_type,
                "label": r.activity_type.replace("_", " ").title(),
                "payload": r.payload,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]

    def _log(self, db: Session, driver_id: str, shift_id: str | None, activity_type: str, payload: dict) -> None:
        from porterchain_api.driver_models import DriverShiftActivity

        db.add(
            DriverShiftActivity(
                driver_id=driver_id,
                shift_id=shift_id,
                activity_type=activity_type,
                payload=payload,
            )
        )

    def _emit(self, db: Session, driver: Any, event_type: str, payload: dict) -> None:
        from porterchain_api.booking_engine._core import emit_event

        emit_event(
            db,
            event_type=event_type,
            aggregate_type="driver",
            aggregate_id=driver.id,
            actor_type="driver",
            actor_id=driver.id,
            payload={**payload, "driver_id": driver.id},
        )

    @staticmethod
    def _require_approved(driver: Any) -> None:
        from porterchain_api.domain.admin_states import DriverStatus

        if driver.status != DriverStatus.APPROVED.value:
            raise PermissionError("driver_not_approved")

    @staticmethod
    def _format_minutes(minutes: int) -> str:
        if minutes <= 0:
            return "0m"
        h, m = divmod(minutes, 60)
        return f"{h}h {m}m" if h else f"{m}m"


def _haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 6_371_000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
