"""One-time staff enrollment / login tokens (Redis).

Used by StaffIdpService for enroll, reissue, and login-request. Tokens are
consumed on activate to mint a Redis staff session.
"""

from __future__ import annotations

import json
import logging
import secrets
import time
from dataclasses import dataclass
from typing import Any

from porterchain_api.auth.staff_session import _client

logger = logging.getLogger("porterchain.security")

ENROLLMENT_PREFIX = "pc:staff:enroll:v1:"
DEFAULT_TTL_SECONDS = 60 * 60 * 48  # 48h


@dataclass(frozen=True)
class StaffEnrollmentToken:
    token: str
    admin_user_id: str
    email: str
    role: str
    expires_at: int


def create_enrollment_token(
    *,
    admin_user_id: str,
    email: str,
    role: str,
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
) -> StaffEnrollmentToken | None:
    client = _client()
    if client is None or not admin_user_id:
        return None
    token = secrets.token_urlsafe(32)
    expires_at = int(time.time()) + max(60, ttl_seconds)
    payload = {
        "admin_user_id": admin_user_id,
        "email": email.lower().strip(),
        "role": role,
        "expires_at": expires_at,
    }
    try:
        client.setex(
            f"{ENROLLMENT_PREFIX}{token}",
            max(60, ttl_seconds),
            json.dumps(payload),
        )
    except Exception:  # noqa: BLE001
        logger.exception("staff_enrollment_create_failed")
        return None
    return StaffEnrollmentToken(
        token=token,
        admin_user_id=admin_user_id,
        email=payload["email"],
        role=role,
        expires_at=expires_at,
    )


def peek_enrollment_token(token: str) -> StaffEnrollmentToken | None:
    client = _client()
    if client is None or not token:
        return None
    try:
        raw = client.get(f"{ENROLLMENT_PREFIX}{token}")
        if not raw:
            return None
        data = json.loads(raw)
        if not isinstance(data, dict):
            return None
        return StaffEnrollmentToken(
            token=token,
            admin_user_id=str(data["admin_user_id"]),
            email=str(data["email"]),
            role=str(data["role"]),
            expires_at=int(data["expires_at"]),
        )
    except Exception:  # noqa: BLE001
        logger.debug("staff_enrollment_peek_failed", exc_info=True)
        return None


def consume_enrollment_token(token: str) -> StaffEnrollmentToken | None:
    enrollment = peek_enrollment_token(token)
    if enrollment is None:
        return None
    client = _client()
    if client is None:
        return None
    try:
        client.delete(f"{ENROLLMENT_PREFIX}{token}")
    except Exception:  # noqa: BLE001
        logger.debug("staff_enrollment_consume_failed", exc_info=True)
    return enrollment
