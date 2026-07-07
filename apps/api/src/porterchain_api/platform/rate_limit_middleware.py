"""Global API rate limiting for authenticated portal routes."""

from __future__ import annotations

import logging
import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse

from porterchain_api.config import get_settings

logger = logging.getLogger(__name__)

_PREFIXES = (
    "/v1/admin/",
    "/v1/merchant/",
    "/v1/customers/",
    "/driver-api/",
)
_EXEMPT_PREFIXES = (
    "/health",
    "/webhooks/",
    "/v1/webhooks/",
    "/v1/quotes",
    "/v1/booking-drafts",
    "/v1/orders/track/",
)


def _client_key(request: Request) -> str:
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return f"bearer:{auth[7:36]}"
    api_key = request.headers.get("X-Api-Key")
    if api_key:
        return f"apikey:{api_key[:24]}"
    forwarded = request.headers.get("X-Forwarded-For")
    ip = forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else "unknown")
    return f"ip:{ip}"


class PortalRateLimitMiddleware(BaseHTTPMiddleware):
    """Redis sliding-window rate limit for portal JWT routes (GAP-H04)."""

    def __init__(self, app, *, limit_per_minute: int | None = None) -> None:
        super().__init__(app)
        self._limit = limit_per_minute

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        path = request.url.path
        if not any(path.startswith(p) for p in _PREFIXES):
            return await call_next(request)
        if any(path.startswith(p) for p in _EXEMPT_PREFIXES):
            return await call_next(request)
        if request.method == "OPTIONS":
            return await call_next(request)

        settings = get_settings()
        if settings.app_env == "local":
            return await call_next(request)
        limit = self._limit or getattr(settings, "portal_rate_limit_per_minute", 120)
        key = f"porterchain:ratelimit:{_client_key(request)}"
        window = int(time.time() // 60)

        allowed, current, error = _check_rate(key, window, limit)
        if error:
            logger.warning("rate limit unavailable — failing closed: %s", error)
            return JSONResponse(
                status_code=503,
                content={"detail": "rate_limit_unavailable"},
            )
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "rate_limit_exceeded",
                    "limit_per_minute": limit,
                    "requests_last_minute": current,
                },
                headers={"Retry-After": "60"},
            )
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(max(0, limit - current))
        return response


def _check_rate(key: str, window: int, limit: int) -> tuple[bool, int, str | None]:
    """Return (allowed, current_count, error_message). Fail closed when Redis is unavailable."""
    try:
        from porterchain_shared.redis_client import get_redis_client

        client = get_redis_client()
        bucket = f"{key}:{window}"
        current = int(client.incr(bucket))
        if current == 1:
            client.expire(bucket, 70)
        return current <= limit, current, None
    except Exception as exc:
        return False, 0, str(exc)
