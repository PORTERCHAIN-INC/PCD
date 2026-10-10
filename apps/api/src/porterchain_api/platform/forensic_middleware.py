"""Record privileged / sensitive API calls into the forensic audit chain.

Covers every mutating admin call, every data export / privacy / erasure request (any
method), and merchant webhook / API-key configuration. Stores method, route path,
status, real client IP and the authenticated actor id when known. Never bodies.
"""

from __future__ import annotations

import re

from starlette.middleware.base import BaseHTTPMiddleware

_SENSITIVE = re.compile(r"(export|privacy|erase|evidence|forensic|access-export|ropa|\.csv$)", re.IGNORECASE)
_MERCHANT_CFG = re.compile(r"^/v1/merchant/(webhooks|api-keys|integrations/(webhooks|api-keys))")


def category_for(method: str, path: str) -> str | None:
    if method in ("OPTIONS", "HEAD"):
        return None
    if _SENSITIVE.search(path):
        return "erasure" if "erase" in path or "delete-request" in path else "data_export"
    if method == "GET":
        return None
    if path.startswith("/v1/admin/"):
        return "admin_action"
    if _MERCHANT_CFG.match(path):
        return "webhooks"
    if path.startswith("/v1/auth/staff/"):
        return "auth"
    return None


class ForensicAuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        path = request.url.path
        cat = category_for(request.method, path)
        if cat and not path.startswith("/v1/auth/staff/login"):  # logins recorded with outcome in-route
            from porterchain_api.platform.client_ip import client_ip
            from porterchain_api.platform.forensics import record_now

            route = getattr(request.scope.get("route"), "path", None) or path
            record_now(cat, f"{request.method} {route}"[:128], actor=getattr(request.state, "audit_actor", None),
                       ip=client_ip(request),
                       outcome="ok" if response.status_code < 400 else ("denied" if response.status_code in (401, 403) else "error"),
                       detail={"status": response.status_code, "path": path[:200]})
        return response
