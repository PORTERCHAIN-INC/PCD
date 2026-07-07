"""Standardized API response envelopes (platform API contract).

Success::

    {"success": true, "data": <payload>}

Error::

    {"success": false, "error": {"code": "<CODE>", "message": "<human readable>"}}

Usage guidance
--------------
* New and refactored endpoints SHOULD return :func:`success` for 2xx payloads.
* Errors are emitted centrally by the global exception handlers in
  :mod:`porterchain_api.main`, which produce the envelope above **and** retain
  the legacy ``detail`` field so existing frontend clients keep working during
  the incremental migration.

Keeping the error contract in one place means Driver/Customer (and every other)
flow returns a consistent, machine-readable ``error.code`` without a risky
big-bang rewrite of every endpoint's success body.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ErrorBody(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    """Standardized error envelope (documented shape for OpenAPI)."""

    success: bool = False
    error: ErrorBody


class SuccessResponse(BaseModel):
    """Standardized success envelope (documented shape for OpenAPI)."""

    success: bool = True
    data: Any = None


def success(data: Any) -> dict[str, Any]:
    """Wrap a successful payload in the standard envelope."""
    return {"success": True, "data": data}


def error(code: str, message: str) -> dict[str, Any]:
    """Build the standard error envelope."""
    return {"success": False, "error": {"code": code, "message": message}}


def error_payload(code: str, message: str, *, detail: Any = None) -> dict[str, Any]:
    """Standard error envelope plus a backward-compatible ``detail`` field.

    ``detail`` mirrors the legacy FastAPI error shape so existing clients that
    read ``response.detail`` continue to work while new clients read
    ``response.error.code`` / ``response.error.message``.
    """
    payload = error(code, message)
    payload["detail"] = detail if detail is not None else message
    return payload
