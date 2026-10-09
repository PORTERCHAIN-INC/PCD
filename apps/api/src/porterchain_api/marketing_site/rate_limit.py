"""Per-IP fixed-window limits for unauthenticated marketing endpoints.

The portal middleware exempts `/v1/public/*`, so these endpoints limit themselves.
Redis down: fail open locally (dev stack), fail closed everywhere else.
"""

from __future__ import annotations

import logging

from fastapi import HTTPException, Request

from porterchain_api.platform.rate_limit import bucket_key, check_fixed_window

logger = logging.getLogger(__name__)

TRAFFIC_MARKETING = "marketing_public"


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        first = forwarded.split(",")[0].strip()
        if first:
            return first[:64]
    return request.client.host if request.client else "unknown"


def enforce_public_limit(request: Request, *, bucket: str, limit: int, app_env: str) -> None:
    from porterchain_shared.redis_health import is_local_env

    key = bucket_key(TRAFFIC_MARKETING, f"{bucket}:ip:{client_ip(request)}")
    allowed, _current, error = check_fixed_window(key, limit)
    if error:
        if is_local_env(app_env):
            logger.warning("marketing rate limit unavailable locally — allowing: %s", error)
            return
        raise HTTPException(status_code=503, detail="rate_limit_unavailable")
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail="rate_limited",
            headers={"Retry-After": "60"},
        )
