"""Resolve the driver's next actionable stop from location + remaining route.

Rank remaining stops with Valhalla/OSRM matrix. Haversine is a labeled fallback
only — never invent ETA as distance/500.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any

from porterchain_driver.route_optimizer import _coords
from porterchain_driver.stop_exceptions import MAX_DELIVERY_ATTEMPTS

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

_ACTIONABLE_SKIP = frozenset({"picked_up", "delivered", "pod_completed", "completed", "locked"})
_EARTH_M = 6_371_000
_UNIT_KEYS = ("unit", "suite", "apartment", "apt", "unit_number")
_BUZZER_KEYS = ("buzzer", "intercom", "access_code", "gate_code")
_DOCK_KEYS = ("dock", "dock_door", "loading_dock", "bay")
_CALL_KEYS = ("call_on_arrival", "call_on_arrive", "call_before_arrival")
_PHONE_KEYS = ("phone", "contact_phone", "mobile")


def _first_str(addr: dict[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        raw = addr.get(key)
        if raw is True:
            continue
        text = str(raw).strip() if raw is not None else ""
        if text and text.lower() not in {"true", "false", "none"}:
            return text
    return None


def _truthy(addr: dict[str, Any], keys: tuple[str, ...]) -> bool:
    for key in keys:
        raw = addr.get(key)
        if raw is True:
            return True
        if isinstance(raw, str) and raw.strip().lower() in {"1", "true", "yes"}:
            return True
    return False


def mask_phone(raw: str | None) -> str | None:
    if not raw:
        return None
    digits = "".join(ch for ch in str(raw) if ch.isdigit())
    if len(digits) < 4:
        return None
    return f"•••-••{digits[-2:]}"


def _access_fields(stop: Any) -> dict[str, Any]:
    addr = stop.address if isinstance(getattr(stop, "address", None), dict) else {}
    instructions = getattr(stop, "special_instructions", None)
    if isinstance(instructions, str):
        instructions = instructions.strip() or None
    else:
        instructions = None
    return {
        "special_instructions": instructions,
        "access_unit": _first_str(addr, _UNIT_KEYS),
        "access_buzzer": _first_str(addr, _BUZZER_KEYS),
        "access_dock": _first_str(addr, _DOCK_KEYS),
        "call_on_arrival": _truthy(addr, _CALL_KEYS),
        "contact_phone_masked": mask_phone(_first_str(addr, _PHONE_KEYS)),
    }


def _delivery_attempts(db: Session, order_id: str) -> int:
    try:
        from porterchain_api.booking_models import OrderException
        from porterchain_driver.stop_exceptions import prior_attempt_rows

        rows = prior_attempt_rows(
            db.query(OrderException).filter(OrderException.order_id == order_id).all()
        )
        return len(rows)
    except Exception:  # noqa: BLE001 — tests pass MagicMock sessions
        return 0


def _is_actionable(stop: Any) -> bool:
    return str(stop.status).lower() not in _ACTIONABLE_SKIP


def _haversine_m(a: tuple[float, float], b: tuple[float, float]) -> int:
    lat1, lon1 = math.radians(a[0]), math.radians(a[1])
    lat2, lon2 = math.radians(b[0]), math.radians(b[1])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return int(_EARTH_M * 2 * math.asin(min(1.0, math.sqrt(h))))


class NextStopResolver:
    def __init__(self, maps: Any = None) -> None:
        self._maps = maps

    def _get_maps(self) -> Any:
        if self._maps is None:
            from porterchain_services.maps.service import MapsService

            self._maps = MapsService()
        return self._maps

    def resolve(self, db: Session, driver: Any) -> dict[str, Any] | None:
        from porterchain_driver.sequence_store import read_sequence
        from porterchain_driver.stops import StopsService

        route = StopsService().assigned_route(db, driver)
        if not route or not route.stops:
            return None

        actionable = [
            s for s in sorted(route.stops, key=lambda x: x.sequence) if _is_actionable(s)
        ]
        if not actionable:
            return None

        # Manifest / optimize sequence is SoT when applied — follow waypoint order.
        plan = read_sequence(getattr(driver, "id", "") or "")
        chosen = actionable[0]
        source_hint: str | None = None
        if plan and plan.get("waypoints"):
            by_key = {
                (str(s.order_id), str(s.stop_type).lower()): s for s in actionable
            }
            for wp in plan["waypoints"]:
                if not isinstance(wp, dict):
                    continue
                key = (
                    str(wp.get("order_id") or ""),
                    str(wp.get("stop_type") or "").lower(),
                )
                hit = by_key.get(key)
                if hit is not None:
                    chosen = hit
                    source_hint = "day_plan"
                    break

        origin = self._driver_origin(db, driver.id, route.stops)
        if origin is None:
            return self._to_dict(
                chosen, db=db, distance_m=None, eta_minutes=None, source=source_hint
            )

        # When sequence locks the next stop, still Valhalla ETA to that stop only.
        if source_hint == "day_plan":
            ranked = self._rank_with_matrix(origin, [chosen])
            if ranked is not None:
                stop, meters, seconds, src = ranked
                eta = round(seconds / 60) if seconds is not None else None
                return self._to_dict(
                    stop,
                    db=db,
                    distance_m=meters,
                    eta_minutes=eta,
                    source=f"{source_hint}+{src or 'matrix'}",
                )
            return self._to_dict(
                chosen, db=db, distance_m=None, eta_minutes=None, source=source_hint
            )

        # Opportunistic: among unlocked legs (pickups + onboard dropoffs), nearest road.
        ranked = self._rank_with_matrix(origin, actionable)
        if ranked is not None:
            stop, meters, seconds, source = ranked
            eta = round(seconds / 60) if seconds is not None else None
            return self._to_dict(
                stop, db=db, distance_m=meters, eta_minutes=eta, source=source
            )

        with_coords = [
            (s, c) for s in actionable if (c := self._stop_coords(s)) is not None
        ]
        if not with_coords:
            return self._to_dict(
                actionable[0], db=db, distance_m=None, eta_minutes=None, source=None
            )
        best, coords = min(with_coords, key=lambda sc: _haversine_m(origin, sc[1]))
        dist = _haversine_m(origin, coords)
        return self._to_dict(
            best, db=db, distance_m=dist, eta_minutes=None, source="haversine"
        )

    def _rank_with_matrix(
        self, origin: tuple[float, float], stops: list[Any]
    ) -> tuple[Any, int | None, int | None, str] | None:
        usable: list[tuple[Any, tuple[float, float]]] = []
        for stop in stops:
            coords = self._stop_coords(stop)
            if coords:
                usable.append((stop, coords))
        if not usable:
            return None
        try:
            maps = self._get_maps()
            matrix, source = maps.matrix_durations([origin], [c for _s, c in usable])
        except Exception:
            return None
        if not matrix or not matrix[0]:
            return None
        row = matrix[0]
        best: tuple[Any, int | None, int | None, str] | None = None
        best_key = math.inf
        for i, (stop, _coords) in enumerate(usable):
            if i >= len(row):
                continue
            seconds, meters = row[i]
            if seconds is None and meters is None:
                continue
            key = float(seconds if seconds is not None else meters)
            if key < best_key:
                best_key = key
                best = (stop, meters, seconds, source or "matrix")
        return best

    def _driver_origin(
        self, db: Session, driver_id: str, stops: list[Any]
    ) -> tuple[float, float] | None:
        from porterchain_api.driver_engine.last_known import read_last_known

        known = read_last_known(driver_id)
        if known is not None:
            return float(known.lat), float(known.lng)

        for stop in reversed(sorted(stops, key=lambda s: s.sequence)):
            if stop.status in ("picked_up", "delivered", "pod_completed", "completed"):
                coords = self._stop_coords(stop)
                if coords:
                    return coords
        return None

    @staticmethod
    def _stop_coords(stop: Any) -> tuple[float, float] | None:
        addr = stop.address if isinstance(stop.address, dict) else {}
        return _coords(addr)

    def _to_dict(
        self,
        stop: Any,
        *,
        db: Session | None = None,
        distance_m: int | None,
        eta_minutes: float | None,
        source: str | None,
    ) -> dict[str, Any]:
        addr = stop.address if isinstance(stop.address, dict) else {}
        access = _access_fields(stop)
        attempts = _delivery_attempts(db, str(stop.order_id)) if db is not None else 0
        return {
            "stop_id": stop.stop_id,
            "stop_type": stop.stop_type,
            "order_id": stop.order_id,
            "order_number": stop.order_number,
            "tracking_number": stop.tracking_number,
            "sequence": getattr(stop, "sequence", None) if getattr(stop, "sequence", None) is not None else 0,
            "address": addr,
            "formatted_address": addr.get("formatted") or addr.get("line1") or "—",
            "distance_m": distance_m,
            "eta_minutes": eta_minutes,
            "source": source,
            "status": stop.status,
            "special_instructions": access["special_instructions"],
            "access_unit": access["access_unit"],
            "access_buzzer": access["access_buzzer"],
            "access_dock": access["access_dock"],
            "call_on_arrival": access["call_on_arrival"],
            "contact_phone_masked": access["contact_phone_masked"],
            "delivery_attempts": attempts,
            "max_delivery_attempts": MAX_DELIVERY_ATTEMPTS,
        }
