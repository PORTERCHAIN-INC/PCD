"""Fleetbase ops mirror — Redis cache for leftover GET surfaces.

Request threads read here only. The worker refreshes via adapter HTTP
(ops_timeout + breaker). Never call Fleetbase from readers.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)

TTL_SECONDS = 30
DRIVER_TTL_SECONDS = 86_400  # ingest overlay outlives the 30s roster blob
HISTORY_TTL_SECONDS = 120  # history refresh is ~60s
PREFIX = "porterchain:fb:ops"
DRIVERS_KEY = f"{PREFIX}:drivers"
ZONES_KEY = f"{PREFIX}:zones"
META_KEY = f"{PREFIX}:meta"
SOURCE_MIRROR = "fleetbase_mirror"
SOURCE_MISS = "mirror_miss"
SOURCE_UNAVAILABLE = "unavailable"
SOURCE_LAST_KNOWN = "last_known"


def _tracking_key(fleetbase_order_id: str) -> str:
    return f"{PREFIX}:tracking:{fleetbase_order_id}"


def _history_key(fleetbase_order_id: str) -> str:
    return f"{PREFIX}:history:{fleetbase_order_id}"


def _driver_key(fleetbase_driver_id: str) -> str:
    return f"{PREFIX}:driver:{fleetbase_driver_id}"


def _fleetbase_id(row: dict[str, Any]) -> str:
    return str(row.get("id") or row.get("uuid") or row.get("fleetbase_driver_id") or "")


def _client() -> Any | None:
    try:
        from porterchain_shared.redis_client import get_redis_client

        return get_redis_client()
    except Exception:
        logger.debug("ops_mirror redis unavailable", exc_info=True)
        return None


def _loads(raw: str | None) -> Any | None:
    if not raw:
        return None
    try:
        return json.loads(raw)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None


def _dumps(value: Any) -> str:
    return json.dumps(value, default=str, separators=(",", ":"))


def write_driver_record(fleetbase_driver_id: str, payload: dict[str, Any]) -> bool:
    if not fleetbase_driver_id:
        return False
    client = _client()
    if client is None:
        return False
    try:
        client.setex(_driver_key(fleetbase_driver_id), DRIVER_TTL_SECONDS, _dumps(payload))
        return True
    except Exception:
        logger.debug("ops_mirror write_driver_record failed", exc_info=True)
        return False


def read_driver_record(fleetbase_driver_id: str) -> dict[str, Any] | None:
    if not fleetbase_driver_id:
        return None
    client = _client()
    if client is None:
        return None
    try:
        data = _loads(client.get(_driver_key(fleetbase_driver_id)))
        return data if isinstance(data, dict) else None
    except Exception:
        logger.debug("ops_mirror read_driver_record failed", exc_info=True)
        return None


def overlay_driver_location(
    fleetbase_driver_id: str,
    *,
    lat: float,
    lng: float,
    recorded_at: Any = None,
) -> bool:
    """Patch ingest coords onto the per-driver hash. Does not clobber a newer overlay."""
    if not fleetbase_driver_id:
        return False
    client = _client()
    if client is None:
        return False
    try:
        from porterchain_api.driver_engine.last_known import parse_recorded_at

        existing = _loads(client.get(_driver_key(fleetbase_driver_id)))
        if not isinstance(existing, dict):
            existing = {"id": fleetbase_driver_id}
        stamp = parse_recorded_at(recorded_at)
        prev = parse_recorded_at(existing.get("location_recorded_at"))
        if prev is not None and stamp is not None and prev >= stamp:
            return False
        existing["id"] = existing.get("id") or fleetbase_driver_id
        existing["location"] = {
            "lat": float(lat),
            "lng": float(lng),
            "coordinates": [float(lng), float(lat)],
        }
        existing["location_source"] = "ingest"
        if stamp is not None:
            existing["location_recorded_at"] = stamp.isoformat()
        client.setex(_driver_key(fleetbase_driver_id), DRIVER_TTL_SECONDS, _dumps(existing))
        return True
    except Exception:
        logger.debug("ops_mirror overlay_driver_location failed", exc_info=True)
        return False


def porterchain_driver_pin(driver_id: str) -> dict[str, Any] | None:
    """Public-safe last-known pin keyed by PorterChain driver id.

    GPS cache lives in driver_engine. Booking/merchant readers use this wrap so
    they do not import driver_engine (D2). Overlay onto Fleetbase ids stays in
    overlay_driver_location.
    """
    if not driver_id:
        return None
    try:
        from porterchain_api.driver_engine.last_known import read_last_known

        known = read_last_known(driver_id)
    except Exception:
        logger.debug("ops_mirror porterchain_driver_pin failed", exc_info=True)
        return None
    if known is None:
        return None
    return {
        "lat": known.lat,
        "lng": known.lng,
        "source": SOURCE_LAST_KNOWN,
        "recorded_at": known.recorded_at.isoformat() if known.recorded_at else None,
    }


def write_drivers(drivers: list[dict[str, Any]]) -> bool:
    client = _client()
    if client is None:
        return False
    try:
        client.setex(DRIVERS_KEY, TTL_SECONDS, _dumps(drivers))
        for row in drivers:
            fid = _fleetbase_id(row)
            if not fid:
                continue
            merged = dict(row)
            existing = _loads(client.get(_driver_key(fid)))
            if isinstance(existing, dict) and existing.get("location_source") == "ingest":
                loc = existing.get("location")
                if loc:
                    merged["location"] = loc
                    merged["location_source"] = "ingest"
                    merged["location_recorded_at"] = existing.get("location_recorded_at")
            client.setex(_driver_key(fid), DRIVER_TTL_SECONDS, _dumps(merged))
        return True
    except Exception:
        logger.debug("ops_mirror write_drivers failed", exc_info=True)
        return False


def read_drivers() -> tuple[list[dict[str, Any]], str]:
    client = _client()
    if client is None:
        return [], SOURCE_UNAVAILABLE
    try:
        data = _loads(client.get(DRIVERS_KEY))
        if isinstance(data, list):
            return data, SOURCE_MIRROR
        return [], SOURCE_MISS
    except Exception:
        logger.debug("ops_mirror read_drivers failed", exc_info=True)
        return [], SOURCE_UNAVAILABLE


def write_zones(zones: list[dict[str, Any]]) -> bool:
    client = _client()
    if client is None:
        return False
    try:
        client.setex(ZONES_KEY, TTL_SECONDS, _dumps(zones))
        return True
    except Exception:
        logger.debug("ops_mirror write_zones failed", exc_info=True)
        return False


def read_zones() -> tuple[list[dict[str, Any]], str]:
    client = _client()
    if client is None:
        return [], SOURCE_UNAVAILABLE
    try:
        data = _loads(client.get(ZONES_KEY))
        if isinstance(data, list):
            return data, SOURCE_MIRROR
        return [], SOURCE_MISS
    except Exception:
        logger.debug("ops_mirror read_zones failed", exc_info=True)
        return [], SOURCE_UNAVAILABLE


def write_tracking(fleetbase_order_id: str, payload: dict[str, Any] | None) -> bool:
    if not fleetbase_order_id:
        return False
    client = _client()
    if client is None:
        return False
    try:
        client.setex(_tracking_key(fleetbase_order_id), TTL_SECONDS, _dumps(payload or {}))
        return True
    except Exception:
        logger.debug("ops_mirror write_tracking failed", exc_info=True)
        return False


def read_tracking(fleetbase_order_id: str) -> tuple[dict[str, Any] | None, str]:
    if not fleetbase_order_id:
        return None, SOURCE_MISS
    client = _client()
    if client is None:
        return None, SOURCE_UNAVAILABLE
    try:
        data = _loads(client.get(_tracking_key(fleetbase_order_id)))
        if isinstance(data, dict):
            return data if data else None, SOURCE_MIRROR
        return None, SOURCE_MISS
    except Exception:
        logger.debug("ops_mirror read_tracking failed", exc_info=True)
        return None, SOURCE_UNAVAILABLE


def write_history(fleetbase_order_id: str, payload: dict[str, Any]) -> bool:
    if not fleetbase_order_id:
        return False
    client = _client()
    if client is None:
        return False
    try:
        client.setex(_history_key(fleetbase_order_id), HISTORY_TTL_SECONDS, _dumps(payload))
        return True
    except Exception:
        logger.debug("ops_mirror write_history failed", exc_info=True)
        return False


def read_history(fleetbase_order_id: str) -> tuple[dict[str, Any] | None, str]:
    if not fleetbase_order_id:
        return None, SOURCE_MISS
    client = _client()
    if client is None:
        return None, SOURCE_UNAVAILABLE
    try:
        data = _loads(client.get(_history_key(fleetbase_order_id)))
        if isinstance(data, dict):
            return data, SOURCE_MIRROR
        return None, SOURCE_MISS
    except Exception:
        logger.debug("ops_mirror read_history failed", exc_info=True)
        return None, SOURCE_UNAVAILABLE


def write_meta(*, refreshed_at: str | None = None, **extra: Any) -> bool:
    client = _client()
    if client is None:
        return False
    payload = {
        "refreshed_at": refreshed_at or datetime.now(UTC).isoformat(),
        **extra,
    }
    try:
        client.setex(META_KEY, TTL_SECONDS, _dumps(payload))
        return True
    except Exception:
        logger.debug("ops_mirror write_meta failed", exc_info=True)
        return False


def read_meta() -> dict[str, Any] | None:
    client = _client()
    if client is None:
        return None
    try:
        data = _loads(client.get(META_KEY))
        return data if isinstance(data, dict) else None
    except Exception:
        logger.debug("ops_mirror read_meta failed", exc_info=True)
        return None


def driver_by_fleetbase_id(fleetbase_driver_id: str) -> dict[str, Any] | None:
    """O(1) per-driver hash, then roster blob. Replaces adapter.drivers.get."""
    if not fleetbase_driver_id:
        return None
    rec = read_driver_record(fleetbase_driver_id)
    if rec:
        return rec
    drivers, _source = read_drivers()
    for row in drivers:
        if _fleetbase_id(row) == fleetbase_driver_id:
            return row
    return None


def online_map_from_mirror() -> dict[str, bool]:
    """fleetbase_driver_id → online from mirrored roster."""
    drivers, _source = read_drivers()
    out: dict[str, bool] = {}
    for fd in drivers:
        fid = str(fd.get("id") or fd.get("uuid") or fd.get("fleetbase_driver_id") or "")
        if not fid:
            continue
        online = fd.get("online")
        if not isinstance(online, bool):
            online = str(fd.get("status") or "").lower() in {"online", "active"}
        out[fid] = bool(online)
    return out
