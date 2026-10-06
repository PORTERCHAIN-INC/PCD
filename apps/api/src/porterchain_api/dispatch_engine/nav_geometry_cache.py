"""Redis cache for nav / public-track corridor geometry.

Pickup/dropoff do not change every poll. Store Valhalla/OSRM legs keyed by
order + origin grid so GET can refresh the GPS pin without another /route.
"""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

CACHE_KEY = "porterchain:nav:geom:{order_id}:{grid}"
CACHE_TTL_SECONDS = 15 * 60


def _grid(origin: tuple[float, float] | None, dest: tuple[float, float] | None) -> str:
    def cell(pt: tuple[float, float] | None) -> str:
        if not pt:
            return "none"
        return f"{round(pt[0], 3)}:{round(pt[1], 3)}"

    return f"{cell(origin)}|{cell(dest)}"


def cache_key(order_id: str, origin: tuple[float, float] | None, dest: tuple[float, float] | None) -> str:
    return CACHE_KEY.format(order_id=order_id, grid=_grid(origin, dest))


def read_nav_geometry(
    order_id: str,
    origin: tuple[float, float] | None,
    dest: tuple[float, float] | None,
) -> dict[str, Any] | None:
    try:
        from porterchain_shared.redis_client import get_redis_client

        raw = get_redis_client().get(cache_key(order_id, origin, dest))
        if not raw:
            return None
        data = json.loads(raw)
        return data if isinstance(data, dict) else None
    except Exception as exc:  # noqa: BLE001
        logger.debug("nav geometry read failed: %s", exc)
        return None


def write_nav_geometry(
    order_id: str,
    origin: tuple[float, float] | None,
    dest: tuple[float, float] | None,
    payload: dict[str, Any],
) -> None:
    try:
        from porterchain_shared.redis_client import get_redis_client

        get_redis_client().setex(
            cache_key(order_id, origin, dest),
            CACHE_TTL_SECONDS,
            json.dumps(payload),
        )
    except Exception as exc:  # noqa: BLE001
        logger.debug("nav geometry write failed: %s", exc)
