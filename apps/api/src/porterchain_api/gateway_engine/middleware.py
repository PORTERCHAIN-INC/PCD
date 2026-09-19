"""HTTP middleware — merchant API gateway usage + Redis rate-limit enforcement."""

from __future__ import annotations

import logging
import time

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse

from porterchain_api.config import get_settings
from porterchain_api.db import SessionLocal
from porterchain_api.gateway_engine import merchant_api as gateway
from porterchain_api.merchant_engine.api_key_service import MerchantApiKeyService
from porterchain_api.oauth_engine.oauth_service import OAuthService
from porterchain_api.platform.rate_limit import (
    TRAFFIC_MERCHANT_API,
    TRAFFIC_MERCHANT_API_OAUTH,
    TRAFFIC_MERCHANT_API_OAUTH_SANDBOX,
    TRAFFIC_MERCHANT_API_SANDBOX,
    incr_merchant_api_auth_reject,
    incr_rate_limit_unavailable,
    incr_rate_limited,
    rate_limit_headers,
)

logger = logging.getLogger(__name__)

_api_keys = MerchantApiKeyService()
_oauth = OAuthService()
_PREFIX = "/v1/merchant-api"


class MerchantApiGatewayMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if not request.url.path.startswith(_PREFIX):
            return await call_next(request)
        if request.method == "OPTIONS":
            return await call_next(request)

        settings = get_settings()
        skip_limit = settings.app_env == "local"

        raw_key = request.headers.get("X-Api-Key")
        authorization = request.headers.get("Authorization") or ""
        bearer = (
            authorization.split(" ", 1)[1].strip()
            if authorization.lower().startswith("bearer ")
            else None
        )

        if not raw_key and not bearer:
            return await call_next(request)

        db = SessionLocal()
        try:
            record = None
            traffic_class = TRAFFIC_MERCHANT_API
            identity: str | None = None
            limit = gateway.DEFAULT_RATE_LIMIT

            if raw_key:
                record = _api_keys.authenticate_key(db, raw_key)
                if not record:
                    incr_merchant_api_auth_reject("invalid_key")
                    return await call_next(request)
                request.state.merchant_api_key = record
                identity = record.id
                limit = record.rate_limit_per_minute or gateway.DEFAULT_RATE_LIMIT
                # Isolate sandbox key burn from production traffic class.
                traffic_class = (
                    TRAFFIC_MERCHANT_API_SANDBOX
                    if (record.environment or "").lower() == "sandbox"
                    else TRAFFIC_MERCHANT_API
                )
            elif bearer:
                try:
                    payload = _oauth.resolve_bearer_token(bearer)
                except Exception as exc:
                    logger.warning("merchant-api oauth resolve failed: %s", exc)
                    incr_merchant_api_auth_reject("invalid_key")
                    return await call_next(request)
                if not payload or not payload.get("merchant_id"):
                    incr_merchant_api_auth_reject("invalid_key")
                    return await call_next(request)
                identity = str(payload["merchant_id"])
                oauth_env = str(payload.get("environment") or "sandbox").lower()
                traffic_class = (
                    TRAFFIC_MERCHANT_API_OAUTH_SANDBOX
                    if oauth_env == "sandbox"
                    else TRAFFIC_MERCHANT_API_OAUTH
                )
                limit = gateway.DEFAULT_RATE_LIMIT

            if not skip_limit and identity is not None:
                allowed, current, err = gateway.check_rate_limit_redis(
                    traffic_class=traffic_class,
                    identity=identity,
                    limit=limit,
                )
                if err:
                    logger.warning("merchant-api rate limit unavailable — failing closed: %s", err)
                    incr_rate_limit_unavailable(traffic_class)
                    return JSONResponse(
                        status_code=503,
                        content={"detail": "rate_limit_unavailable"},
                    )
                if not allowed:
                    incr_rate_limited(traffic_class)
                    return JSONResponse(
                        status_code=429,
                        content={
                            "detail": "rate_limit_exceeded",
                            "limit_per_minute": limit,
                            "requests_last_minute": current,
                        },
                        headers={"Retry-After": "60"},
                    )
            else:
                current = 0

            start = time.perf_counter()
            response = await call_next(request)
            if not skip_limit and identity is not None:
                for header, value in rate_limit_headers(limit, current).items():
                    response.headers[header] = value

            if record is not None:
                duration_ms = int((time.perf_counter() - start) * 1000)
                gateway.record_usage(
                    db,
                    api_key=record,
                    method=request.method,
                    path=request.url.path,
                    status_code=response.status_code,
                    duration_ms=duration_ms,
                )
            return response
        finally:
            db.close()
