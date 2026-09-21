"""Redis last-known GPS registry — CAS by recorded_at, not a Postgres hot row.

Fleetbase remains live GPS SoT. This cache is the PorterChain OCC registry for
nav/shift leftover-after-drain. Redis miss must never fail ingest.
"""

from __future__ import annotations

import json
import logging
import math
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)

LAST_KEY = "porterchain:gps:last:{driver_id}"
GEO_KEY = "porterchain:gps:geo"
SHIFT_KEY = "porterchain:gps:shift:{driver_id}:{shift_id}"
TTL_SECONDS = 86_400

# KEYS[1]=hash KEYS[2]=geo
# ARGV: epoch, lat, lng, recorded_at, accuracy, heading, speed, fb_id, h3, ttl, member
_CAS_LUA = """
local key = KEYS[1]
local geo_key = KEYS[2]
local new_epoch = tonumber(ARGV[1])
local old = redis.call('HGET', key, 'recorded_at_epoch')
if old and tonumber(old) >= new_epoch then
  return 0
end
local ver = tonumber(redis.call('HGET', key, 'version') or '0') + 1
redis.call('HSET', key,
  'lat', ARGV[2],
  'lng', ARGV[3],
  'recorded_at', ARGV[4],
  'recorded_at_epoch', ARGV[1],
  'accuracy_m', ARGV[5],
  'heading', ARGV[6],
  'speed_mps', ARGV[7],
  'fleetbase_driver_id', ARGV[8],
  'h3', ARGV[9],
  'version', tostring(ver)
)
redis.call('EXPIRE', key, tonumber(ARGV[10]))
pcall(function()
  redis.call('GEOADD', geo_key, ARGV[3], ARGV[2], ARGV[11])
end)
return ver
"""


@dataclass(frozen=True)
class LastKnown:
    driver_id: str
    lat: float
    lng: float
    recorded_at: datetime
    version: int = 1
    accuracy_m: float | None = None
    heading: float | None = None
    speed_mps: float | None = None
    fleetbase_driver_id: str | None = None
    h3: str | None = None

    def as_track_payload(self) -> dict[str, Any]:
        return {
            "fleetbase_driver_id": self.fleetbase_driver_id,
            "driver_id": self.driver_id,
            "lat": self.lat,
            "lng": self.lng,
            "heading": self.heading,
            "speed": self.speed_mps,
            "recorded_at": self.recorded_at.isoformat(),
        }


def parse_recorded_at(raw: Any) -> datetime | None:
    """Parse GPS timestamps. Naive values are treated as UTC. Not string-ordered."""
    if raw is None:
        return None
    if isinstance(raw, datetime):
        dt = raw
    else:
        text = str(raw).strip()
        if not text:
            return None
        try:
            dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except (TypeError, ValueError):
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def recorded_at_epoch(dt: datetime) -> float:
    return dt.timestamp()


def _client() -> Any | None:
    try:
        from porterchain_shared.redis_client import get_redis_client

        return get_redis_client()
    except Exception:
        logger.debug("gps last-known redis unavailable", exc_info=True)
        return None


def _blank(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def _float_or_none(raw: Any) -> float | None:
    if raw is None or raw == "":
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def write_last_known(
    *,
    driver_id: str,
    lat: float,
    lng: float,
    recorded_at: datetime | str,
    accuracy_m: float | None = None,
    heading: float | None = None,
    speed_mps: float | None = None,
    fleetbase_driver_id: str | None = None,
    h3: str | None = None,
    client: Any | None = None,
) -> LastKnown | None:
    """CAS-write last-known. Returns the stored row when accepted; None if stale or Redis down."""
    stamp = parse_recorded_at(recorded_at)
    if stamp is None or not driver_id:
        return None
    redis_client = client if client is not None else _client()
    if redis_client is None:
        return None
    cell_id = h3
    if not cell_id:
        try:
            from porterchain_api.spatial.h3_index import cell as h3_cell

            cell_id = h3_cell(float(lat), float(lng))
        except Exception:
            cell_id = None
    key = LAST_KEY.format(driver_id=driver_id)
    try:
        accepted = redis_client.eval(
            _CAS_LUA,
            2,
            key,
            GEO_KEY,
            str(recorded_at_epoch(stamp)),
            str(lat),
            str(lng),
            stamp.isoformat(),
            _blank(accuracy_m),
            _blank(heading),
            _blank(speed_mps),
            _blank(fleetbase_driver_id),
            _blank(cell_id),
            str(TTL_SECONDS),
            driver_id,
        )
    except Exception:
        logger.debug("gps last-known CAS failed driver=%s", driver_id, exc_info=True)
        return None
    if not accepted:
        return None
    try:
        version = int(accepted)
    except (TypeError, ValueError):
        version = 1
    stored = LastKnown(
        driver_id=driver_id,
        lat=float(lat),
        lng=float(lng),
        recorded_at=stamp,
        version=version,
        accuracy_m=accuracy_m,
        heading=heading,
        speed_mps=speed_mps,
        fleetbase_driver_id=fleetbase_driver_id,
        h3=cell_id,
    )
    if fleetbase_driver_id:
        try:
            from porterchain_api.fleetbase_engine import ops_mirror

            ops_mirror.overlay_driver_location(
                fleetbase_driver_id,
                lat=float(lat),
                lng=float(lng),
                recorded_at=stamp,
            )
        except Exception:
            logger.debug(
                "gps last-known overlay failed driver=%s", driver_id, exc_info=True
            )
    return stored


def read_last_known(driver_id: str, *, client: Any | None = None) -> LastKnown | None:
    if not driver_id:
        return None
    redis_client = client if client is not None else _client()
    if redis_client is None:
        return None
    key = LAST_KEY.format(driver_id=driver_id)
    try:
        data = redis_client.hgetall(key)
    except Exception:
        logger.debug("gps last-known read failed driver=%s", driver_id, exc_info=True)
        return None
    if not data:
        return None
    stamp = parse_recorded_at(data.get("recorded_at"))
    lat = _float_or_none(data.get("lat"))
    lng = _float_or_none(data.get("lng"))
    if stamp is None or lat is None or lng is None:
        return None
    version_raw = data.get("version") or "1"
    try:
        version = int(float(version_raw))
    except (TypeError, ValueError):
        version = 1
    fb = data.get("fleetbase_driver_id") or None
    h3 = data.get("h3") or None
    return LastKnown(
        driver_id=driver_id,
        lat=lat,
        lng=lng,
        recorded_at=stamp,
        version=version,
        accuracy_m=_float_or_none(data.get("accuracy_m")),
        heading=_float_or_none(data.get("heading")),
        speed_mps=_float_or_none(data.get("speed_mps")),
        fleetbase_driver_id=None if fb == "" else fb,
        h3=None if h3 == "" else h3,
    )


def distance_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle meters between two last-known points. Mileage + stop geofence only."""
    return _haversine_m(lat1, lng1, lat2, lng2)


def _haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 6_371_000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(min(1.0, math.sqrt(a)))


def accumulate_shift_mileage(
    *,
    driver_id: str,
    shift_id: str,
    lat: float,
    lng: float,
    recorded_at: datetime | str,
    client: Any | None = None,
) -> float | None:
    """Add consecutive last-known haversine to the open-shift odometer. Wave 2 reader."""
    stamp = parse_recorded_at(recorded_at)
    if stamp is None or not driver_id or not shift_id:
        return None
    redis_client = client if client is not None else _client()
    if redis_client is None:
        return None
    key = SHIFT_KEY.format(driver_id=driver_id, shift_id=shift_id)
    epoch = recorded_at_epoch(stamp)
    try:
        raw = redis_client.get(key)
        meters = 0.0
        if raw:
            prev = json.loads(raw)
            prev_epoch = float(prev.get("recorded_at_epoch") or 0)
            if epoch <= prev_epoch:
                return float(prev.get("meters") or 0)
            prev_lat = prev.get("last_lat")
            prev_lng = prev.get("last_lng")
            meters = float(prev.get("meters") or 0)
            if prev_lat is not None and prev_lng is not None:
                meters += _haversine_m(float(prev_lat), float(prev_lng), lat, lng)
        payload = {
            "last_lat": lat,
            "last_lng": lng,
            "meters": meters,
            "recorded_at": stamp.isoformat(),
            "recorded_at_epoch": epoch,
        }
        redis_client.setex(key, TTL_SECONDS, json.dumps(payload))
        return meters
    except Exception:
        logger.debug("gps shift mileage failed driver=%s", driver_id, exc_info=True)
        return None


def read_shift_mileage_km(
    driver_id: str,
    shift_id: str,
    *,
    client: Any | None = None,
) -> float | None:
    """Shift odometer from the last-known accumulator (km). None if Redis miss."""
    if not driver_id or not shift_id:
        return None
    redis_client = client if client is not None else _client()
    if redis_client is None:
        return None
    key = SHIFT_KEY.format(driver_id=driver_id, shift_id=shift_id)
    try:
        raw = redis_client.get(key)
        if not raw:
            return None
        data = json.loads(raw)
        return float(data.get("meters") or 0) / 1000.0
    except Exception:
        logger.debug("gps shift mileage read failed driver=%s", driver_id, exc_info=True)
        return None
