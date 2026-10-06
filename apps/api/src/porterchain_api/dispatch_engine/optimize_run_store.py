"""Redis store for async Control Tower optimize runs.

HTTP handlers write pending and read status. The worker finishes the
PorterChain day plan (OR-Tools + Valhalla) and writes ready/error.
Never run the search inside the GET/POST that drew the page.
"""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

CACHE_KEY = "porterchain:optimize:{run_id}"
FLEET_OPEN_KEY = "porterchain:optimize:fleet_open"
CACHE_TTL_SECONDS = 15 * 60
STATUS_PENDING = "pending"
STATUS_READY = "ready"
STATUS_ERROR = "error"


def cache_key(run_id: str) -> str:
    return CACHE_KEY.format(run_id=run_id)


def read_optimize_run(run_id: str) -> dict[str, Any] | None:
    try:
        from porterchain_shared.redis_client import get_redis_client

        raw = get_redis_client().get(cache_key(run_id))
        if not raw:
            return None
        data = json.loads(raw)
        return data if isinstance(data, dict) else None
    except Exception as exc:  # noqa: BLE001 — miss is pending/404, not 500
        logger.debug("optimize run read failed: %s", exc)
        return None


def write_optimize_run(run_id: str, payload: dict[str, Any]) -> None:
    from porterchain_shared.redis_client import get_redis_client

    get_redis_client().setex(
        cache_key(run_id),
        CACHE_TTL_SECONDS,
        json.dumps(payload),
    )


def mark_fleet_optimize_open() -> None:
    """Fleet preview is uncommitted. Manual assign must not resequence."""
    try:
        from porterchain_shared.redis_client import get_redis_client

        get_redis_client().setex(FLEET_OPEN_KEY, CACHE_TTL_SECONDS, "1")
    except Exception as exc:  # noqa: BLE001
        logger.debug("fleet optimize open flag failed: %s", exc)


def clear_fleet_optimize_open() -> None:
    try:
        from porterchain_shared.redis_client import get_redis_client

        get_redis_client().delete(FLEET_OPEN_KEY)
    except Exception as exc:  # noqa: BLE001
        logger.debug("fleet optimize open clear failed: %s", exc)


def fleet_optimize_open() -> bool:
    try:
        from porterchain_shared.redis_client import get_redis_client

        return bool(get_redis_client().get(FLEET_OPEN_KEY))
    except Exception as exc:  # noqa: BLE001
        logger.debug("fleet optimize open read failed: %s", exc)
        return False


def enqueue_optimize_job(run_id: str) -> None:
    from porterchain_api.dispatch_engine.routing_jobs import enqueue_routing_job

    enqueue_routing_job({"action": "optimize_run", "run_id": run_id})
