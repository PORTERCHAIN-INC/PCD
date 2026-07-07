"""HTTP middleware — merchant API gateway usage + rate-limit enforcement."""

from __future__ import annotations

import time

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse

from porterchain_api.db import SessionLocal
from porterchain_api.gateway_engine import merchant_api as gateway
from porterchain_api.merchant_engine.api_key_service import MerchantApiKeyService

_api_keys = MerchantApiKeyService()
_PREFIX = "/v1/merchant-api"


class MerchantApiGatewayMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if not request.url.path.startswith(_PREFIX):
            return await call_next(request)

        raw_key = request.headers.get("X-Api-Key")
        if not raw_key:
            return await call_next(request)

        db = SessionLocal()
        try:
            record = _api_keys.authenticate_key(db, raw_key)
            if not record:
                return await call_next(request)

            request.state.merchant_api_key = record

            allowed, current, limit = gateway.check_rate_limit(db, record)
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

            start = time.perf_counter()
            response = await call_next(request)
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
