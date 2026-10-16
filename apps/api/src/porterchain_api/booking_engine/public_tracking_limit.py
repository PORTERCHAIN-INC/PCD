"""Per-viewer rate limit for the public live-tracking endpoint.

The global middleware allows 120 req/min per IP across all public routes. Live tracking
carries a (coarse) driver position, so it gets its own tighter bucket per client IP and
tracking number. The website polls every 10 s (6/min); server-side renders from our own
host are exempt (same rule as the middleware).
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import HTTPException

from porterchain_api.platform.rate_limit import bucket_key, check_fixed_window

logger = logging.getLogger(__name__)

TRAFFIC_PUBLIC_TRACKING = "public_tracking"
PUBLIC_TRACKING_LIMIT_PER_MINUTE = 12


def enforce_public_tracking_limit(request: Any, tracking_number: str, *, app_env: str) -> None:
    from porterchain_api.platform.client_ip import client_ip, is_trusted_server

    ip = client_ip(request)
    if is_trusted_server(ip):
        return
    key = bucket_key(TRAFFIC_PUBLIC_TRACKING, f"ip:{ip}:tn:{tracking_number[:64]}")
    allowed, _current, error = check_fixed_window(key, PUBLIC_TRACKING_LIMIT_PER_MINUTE)
    if error:
        if app_env == "local":
            logger.warning("public tracking rate limit unavailable locally; allowing: %s", error)
            return
        raise HTTPException(status_code=503, detail="rate_limit_unavailable")
    if not allowed:
        raise HTTPException(status_code=429, detail="rate_limited", headers={"Retry-After": "60"})
