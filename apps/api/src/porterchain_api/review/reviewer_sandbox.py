"""App Store / Play reviewer demo driver (doc 74 §3, G21 A-APR-02).

The reviewer driver (email in ``REVIEWER_DRIVER_EMAILS``, only while
``REVIEWER_ACCOUNTS_ENABLED=true``) sees two fake sandbox jobs. Every action on a
``sandbox-`` id is answered in memory by :class:`ReviewerSandboxMiddleware`: nothing is
written, dispatch never assigns real work, and no payout or invoice record exists.
"""

from __future__ import annotations

import json
import re
from typing import Any

SANDBOX_PREFIX = "sandbox-"
SANDBOX_ROUTE_ID = "sandbox-route-review"


def reviewer_driver_emails(settings: Any) -> set[str]:
    if not getattr(settings, "reviewer_accounts_enabled", False):
        return set()
    raw = str(getattr(settings, "reviewer_driver_emails", "") or "")
    return {e.strip().lower() for e in raw.split(",") if e.strip()}


def is_reviewer_driver(driver: Any, settings: Any) -> bool:
    email = str(getattr(driver, "email", "") or "").strip().lower()
    return bool(email) and email in reviewer_driver_emails(settings)


_JOBS = [
    ("sandbox-job-1", "PC-REVIEW-1", "TRK-REVIEW-1", "100 King St W, Toronto ON M5X 1A9", "1 Yonge St, Toronto ON M5E 1E5"),
    ("sandbox-job-2", "PC-REVIEW-2", "TRK-REVIEW-2", "100 King St W, Toronto ON M5X 1A9", "290 Bremner Blvd, Toronto ON M5V 3L9"),
]


def _summary(i: int, job: tuple[str, str, str, str, str]) -> dict[str, Any]:
    oid, num, trk, pick, drop = job
    return {
        "order_id": oid, "order_number": num, "tracking_number": trk,
        "state": "ASSIGNED", "status": "assigned", "bucket": "current" if i == 0 else "upcoming",
        "pickup_address": pick, "delivery_address": drop,
        "pickup_stop_id": f"{oid}-pickup", "delivery_stop_id": f"{oid}-delivery",
        "special_instructions": "Demo job for app review. Not a real delivery.",
        "is_current_job": i == 0, "route_id": SANDBOX_ROUTE_ID,
    }


def sandbox_jobs() -> dict[str, Any]:
    jobs = [_summary(i, j) for i, j in enumerate(_JOBS)]
    return {"route_id": SANDBOX_ROUTE_ID, "route_status": "active", "current": jobs[0],
            "upcoming": jobs[1:], "completed": [], "jobs": jobs}


def sandbox_job_detail(order_id: str) -> dict[str, Any] | None:
    for i, j in enumerate(_JOBS):
        if j[0] == order_id:
            d = _summary(i, j)
            d.update({"allowed_actions": ["arrive", "pod-photo", "pod-complete", "deliver"],
                      "pod_requirements": {"photo": True}, "stops": [], "sandbox": True})
            return d
    return None


_ACTION = re.compile(
    r"^/driver-api/v1/(?:routes/(?P<route>sandbox-[\w-]+)/(?:start|stops/[\w-]+/(?P<a>[\w-]+))"
    r"|orders/(?P<order>sandbox-[\w-]+)/(?P<b>[\w/-]+)|jobs/(?P<job>sandbox-[\w-]+))$"
)


def sandbox_response(method: str, path: str) -> dict[str, Any] | None:
    """Synthetic body for a sandbox id, or ``None`` when the path is not a sandbox call."""
    m = _ACTION.match(path)
    if not m:
        return None
    if m.group("job"):
        return sandbox_job_detail(m.group("job")) if method == "GET" else None
    action = m.group("a") or m.group("b") or "start"
    return {"ok": True, "sandbox": True, "action": action,
            "message": "Demo job: nothing was sent to a real customer, merchant or payout."}


class ReviewerSandboxMiddleware:
    """ASGI: answers ``sandbox-`` driver calls in memory. Needs a bearer token; writes nothing."""

    def __init__(self, app: Any, enabled: Any = None) -> None:
        self.app = app
        self._enabled = enabled  # callable → bool; default reads REVIEWER_ACCOUNTS_ENABLED

    def enabled(self) -> bool:
        if self._enabled is not None:
            return bool(self._enabled())
        from porterchain_api.config import get_settings

        return bool(get_settings().reviewer_accounts_enabled)

    async def __call__(self, scope: dict, receive: Any, send: Any) -> None:
        if scope.get("type") == "http" and SANDBOX_PREFIX in scope.get("path", "") and self.enabled():
            body = sandbox_response(scope.get("method", "GET"), scope["path"])
            headers = {k.decode().lower(): v.decode() for k, v in scope.get("headers", [])}
            if body is not None:
                status = 200 if headers.get("authorization", "").lower().startswith("bearer ") else 401
                payload = json.dumps(body if status == 200 else {"detail": "not_authenticated"}).encode()
                await send({"type": "http.response.start", "status": status,
                            "headers": [(b"content-type", b"application/json")]})
                await send({"type": "http.response.body", "body": payload})
                return
        await self.app(scope, receive, send)
