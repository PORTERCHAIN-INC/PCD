"""Standard API error envelope (DD-50 / §2.2.12)."""

from __future__ import annotations

import re
from typing import Any

_CODE_RE = re.compile(r"^[a-z][a-z0-9_]*$")


def error_envelope(
    detail: Any,
    *,
    code: str | None = None,
    request_id: str | None = None,
) -> dict[str, Any]:
    """Return consistent JSON error body: ``detail`` + optional ``code`` + ``request_id``."""
    body: dict[str, Any] = {"detail": detail}
    if code:
        body["code"] = code
    elif isinstance(detail, str) and _CODE_RE.match(detail):
        body["code"] = detail
    elif isinstance(detail, list):
        body["code"] = "validation_error"
    if request_id:
        body["request_id"] = request_id
    return body
