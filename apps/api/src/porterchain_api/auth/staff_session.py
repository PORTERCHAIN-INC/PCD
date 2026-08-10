"""Staff IdP session store (Redis) — foundation for admin.porterchain.com without Clerk.

Admin portal still uses Clerk until enrollment + session cookie routes are wired.
This module is the SSOT for staff session payloads once that cutover lands.
"""

from __future__ import annotations

import json
import logging
import secrets
import time
from dataclasses import asdict, dataclass
from typing import Any

logger = logging.getLogger("porterchain.security")

SESSION_PREFIX = "pc:staff:session:v1:"
DEFAULT_TTL_SECONDS = 60 * 60 * 12  # 12h
STAFF_COOKIE_NAME = "pc_staff_sid"
STAFF_BEARER_PREFIX = "staff_sess_"


def staff_cookie_params(settings, *, max_age: int = DEFAULT_TTL_SECONDS) -> dict:
    """HttpOnly cookie attrs for Set-Cookie / delete_cookie."""
    from porterchain_shared.redis_health import is_local_env

    local = is_local_env(getattr(settings, "app_env", "local"))
    # Cross-subdomain in prod (admin.* ↔ api.*) needs Domain + SameSite=None.
    domain = None if local else ".porterchain.com"
    return {
        "key": STAFF_COOKIE_NAME,
        "httponly": True,
        "secure": not local,
        "samesite": "lax" if local else "none",
        "path": "/",
        "max_age": max(60, int(max_age)),
        "domain": domain,
    }


def session_id_from_authorization(authorization: str | None) -> str | None:
    """Parse ``Authorization: Bearer staff_sess_<id>``."""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.removeprefix("Bearer ").strip()
    if not token.startswith(STAFF_BEARER_PREFIX):
        return None
    sid = token.removeprefix(STAFF_BEARER_PREFIX).strip()
    return sid or None


def bearer_token_for_session(session_id: str) -> str:
    return f"{STAFF_BEARER_PREFIX}{session_id}"


@dataclass(frozen=True)
class StaffSession:
    session_id: str
    admin_user_id: str
    email: str
    role: str
    created_at: float
    expires_at: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StaffSession:
        return cls(
            session_id=str(data["session_id"]),
            admin_user_id=str(data["admin_user_id"]),
            email=str(data["email"]),
            role=str(data["role"]),
            created_at=float(data["created_at"]),
            expires_at=float(data["expires_at"]),
        )


def _client():
    try:
        from porterchain_shared.redis_client import get_redis_client

        client = get_redis_client()
        client.ping()
        return client
    except Exception:  # noqa: BLE001
        return None


def create_session(
    *,
    admin_user_id: str,
    email: str,
    role: str,
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
) -> StaffSession | None:
    """Create a staff session. Returns None if Redis is unavailable."""
    client = _client()
    if client is None or not admin_user_id:
        return None
    now = time.time()
    session = StaffSession(
        session_id=secrets.token_urlsafe(32),
        admin_user_id=admin_user_id,
        email=email.lower().strip(),
        role=role,
        created_at=now,
        expires_at=now + max(60, ttl_seconds),
    )
    try:
        client.setex(
            f"{SESSION_PREFIX}{session.session_id}",
            max(60, ttl_seconds),
            json.dumps(session.to_dict()),
        )
        return session
    except Exception:  # noqa: BLE001
        logger.exception("staff_session_create_failed")
        return None


def get_session(session_id: str) -> StaffSession | None:
    if not session_id:
        return None
    client = _client()
    if client is None:
        return None
    try:
        raw = client.get(f"{SESSION_PREFIX}{session_id}")
        if not raw:
            return None
        data = json.loads(raw)
        if not isinstance(data, dict):
            return None
        session = StaffSession.from_dict(data)
        if session.expires_at < time.time():
            revoke_session(session_id)
            return None
        return session
    except Exception:  # noqa: BLE001
        logger.debug("staff_session_get_failed", exc_info=True)
        return None


def revoke_session(session_id: str) -> bool:
    if not session_id:
        return False
    client = _client()
    if client is None:
        return False
    try:
        return bool(client.delete(f"{SESSION_PREFIX}{session_id}"))
    except Exception:  # noqa: BLE001
        logger.debug("staff_session_revoke_failed", exc_info=True)
        return False
