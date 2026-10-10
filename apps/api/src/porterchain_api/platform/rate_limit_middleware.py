"""Global API rate limiting for authenticated portal routes."""

from __future__ import annotations

import logging

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse

from porterchain_api.config import get_settings
from porterchain_api.platform.rate_limit import (
    TRAFFIC_PORTAL,
    bucket_key,
    check_fixed_window,
    incr_rate_limit_unavailable,
    incr_rate_limited,
    rate_limit_headers,
)

logger = logging.getLogger(__name__)

_PREFIXES = (
    "/v1/admin/",
    "/v1/merchant/",
    "/v1/customers/",
    "/v1/delivery-manage/",
    "/v1/express/",
    "/v1/email-preferences",
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
    """Redis fixed-window rate limit for portal JWT routes (GAP-H04)."""

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
        key = bucket_key(TRAFFIC_PORTAL, _client_key(request))

        allowed, current, error = check_fixed_window(key, limit)
        if error:
            logger.warning("rate limit unavailable — failing closed: %s", error)
            incr_rate_limit_unavailable(TRAFFIC_PORTAL)
            return JSONResponse(
                status_code=503,
                content={"detail": "rate_limit_unavailable"},
            )
        if not allowed:
            incr_rate_limited(TRAFFIC_PORTAL)
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
        for header, value in rate_limit_headers(limit, current).items():
            response.headers[header] = value
        return response


# Re-export for tests that imported from this module.
from porterchain_api.platform.rate_limit import _check_rate  # noqa: F401
