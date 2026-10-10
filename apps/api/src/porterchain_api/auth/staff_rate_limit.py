"""Staff IdP auth rate limits — public login / passkey / activate endpoints."""

from __future__ import annotations

from fastapi import HTTPException, Request

from porterchain_api.platform.rate_limit import (
    bucket_key,
    check_fixed_window,
    incr_rate_limit_unavailable,
    incr_rate_limited,
)
from porterchain_api.auth.sli_metrics import note_auth_event

TRAFFIC_STAFF_AUTH = "staff_auth"
# Per IP (and optionally email) — keep low; magic-link + passkey are cheap to spray.
STAFF_AUTH_LIMIT_PER_MINUTE = 20


def _client_ip(request: Request | None) -> str:
    if request is None:
        return "unknown"
    from porterchain_api.platform.client_ip import client_ip

    return client_ip(request)


def enforce_staff_auth_rate(request: Request | None, *, email: str | None = None) -> None:
    """Raise HTTP 429 when the staff auth bucket is exhausted. Fail closed if Redis is down."""
    identity = _client_ip(request)
    if email and email.strip():
        identity = f"{identity}:{email.lower().strip()}"
    key = bucket_key(TRAFFIC_STAFF_AUTH, identity)
    allowed, _current, err = check_fixed_window(key, STAFF_AUTH_LIMIT_PER_MINUTE)
    if err:
        incr_rate_limit_unavailable(TRAFFIC_STAFF_AUTH)
        note_auth_event("staff_auth_rate", "unavailable")
        raise HTTPException(status_code=503, detail="staff_auth_rate_unavailable")
    if not allowed:
        incr_rate_limited(TRAFFIC_STAFF_AUTH)
        note_auth_event("staff_auth_rate", "limited")
        raise HTTPException(status_code=429, detail="staff_auth_rate_limited")
