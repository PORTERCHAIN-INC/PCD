"""Redis store for async Control Tower optimize runs (Step 2 Wave 0).

HTTP handlers write pending and read status. The worker writes ready/error
after Fleetbase orchestrator returns. Never call the orchestrator from GET/POST.
"""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

CACHE_KEY = "porterchain:optimize:{run_id}"
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


def enqueue_optimize_job(run_id: str) -> None:
    from porterchain_api.fleetbase_engine.routing_jobs import enqueue_routing_job

    enqueue_routing_job({"action": "optimize_run", "run_id": run_id})
