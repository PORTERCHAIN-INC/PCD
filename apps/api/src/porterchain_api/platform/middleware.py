"""HTTP middleware — correlation IDs for observability."""

from __future__ import annotations

import json
import logging
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from porterchain_api.platform.observability import bind_request_context

logger = logging.getLogger(__name__)
REQUEST_ID_HEADER = "X-Request-ID"


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())
        request.state.request_id = request_id
        bind_request_context(
            request_id=request_id,
            path=request.url.path,
            method=request.method,
        )
        response = await call_next(request)
        headers = dict(response.headers)
        headers[REQUEST_ID_HEADER] = request_id

        if response.status_code < 400:
            response.headers[REQUEST_ID_HEADER] = request_id
            return response

        content_type = headers.get("content-type", "")
        if not content_type.startswith("application/json"):
            response.headers[REQUEST_ID_HEADER] = request_id
            return response

        body = b""
        async for chunk in response.body_iterator:
            body += chunk
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            return Response(content=body, status_code=response.status_code, headers=headers)

        if isinstance(data, dict) and "request_id" not in data:
            data["request_id"] = request_id
            if "code" not in data and response.status_code == 404:
                data["code"] = "not_found"

        return JSONResponse(content=data, status_code=response.status_code, headers=headers)
