"""Audited impersonation sessions (Redis) — break-glass \"open as user\".

Staff never receives a forged Clerk JWT. Portals accept ``Bearer pc_imp_<id>``
which resolves to the target persona for a short absolute TTL. Every start/stop
is written to AdminAuditLog; request.state carries the session for engines.
"""

from __future__ import annotations

import json
import logging
import secrets
import time
from dataclasses import asdict, dataclass
from typing import Any, Literal

logger = logging.getLogger("porterchain.security")

IMP_PREFIX = "pc:impersonation:v1:"
IMP_BEARER_PREFIX = "pc_imp_"
DEFAULT_TTL_SECONDS = 15 * 60  # absolute — no sliding
MIN_REASON_LENGTH = 10
TargetType = Literal["driver", "merchant", "customer"]


@dataclass(frozen=True)
class ImpersonationSession:
    session_id: str
    actor_admin_id: str
    actor_email: str
    actor_role: str
    target_type: TargetType
    target_id: str
    target_email: str
    reason: str
    created_at: float
    expires_at: float
    staff_session_id: str = ""
    target_clerk_user_id: str | None = None
    target_label: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ImpersonationSession:
        return cls(
            session_id=str(data["session_id"]),
            actor_admin_id=str(data["actor_admin_id"]),
            actor_email=str(data["actor_email"]),
            actor_role=str(data["actor_role"]),
            target_type=str(data["target_type"]),  # type: ignore[arg-type]
            target_id=str(data["target_id"]),
            target_email=str(data["target_email"]),
            reason=str(data["reason"]),
            created_at=float(data["created_at"]),
            expires_at=float(data["expires_at"]),
            staff_session_id=str(data.get("staff_session_id") or ""),
            target_clerk_user_id=(
                str(data["target_clerk_user_id"])
                if data.get("target_clerk_user_id")
                else None
            ),
            target_label=str(data.get("target_label") or ""),
        )

    def public_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "actor_email": self.actor_email,
            "actor_role": self.actor_role,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "target_email": self.target_email,
            "target_label": self.target_label or self.target_email,
            "reason": self.reason,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "seconds_remaining": max(0, int(self.expires_at - time.time())),
        }


def bearer_token_for_session(session_id: str) -> str:
    return f"{IMP_BEARER_PREFIX}{session_id}"


def session_id_from_authorization(authorization: str | None) -> str | None:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.removeprefix("Bearer ").strip()
    if not token.startswith(IMP_BEARER_PREFIX):
        return None
    sid = token.removeprefix(IMP_BEARER_PREFIX).strip()
    return sid or None


def session_id_from_bearer(token: str | None) -> str | None:
    if not token or not token.startswith(IMP_BEARER_PREFIX):
        return None
    sid = token.removeprefix(IMP_BEARER_PREFIX).strip()
    return sid or None


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
    actor_admin_id: str,
    actor_email: str,
    actor_role: str,
    target_type: TargetType,
    target_id: str,
    target_email: str,
    reason: str,
    staff_session_id: str = "",
    target_clerk_user_id: str | None = None,
    target_label: str = "",
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
) -> ImpersonationSession | None:
    cleaned = (reason or "").strip()
    if len(cleaned) < MIN_REASON_LENGTH:
        raise ValueError("impersonation_reason_too_short")
    if target_type not in ("driver", "merchant", "customer"):
        raise ValueError("invalid_impersonation_target_type")

    client = _client()
    if client is None:
        return None

    now = time.time()
    ttl = max(60, min(int(ttl_seconds), DEFAULT_TTL_SECONDS))
    sid = secrets.token_urlsafe(24)
    session = ImpersonationSession(
        session_id=sid,
        actor_admin_id=actor_admin_id,
        actor_email=actor_email.lower().strip(),
        actor_role=actor_role,
        target_type=target_type,
        target_id=target_id,
        target_email=target_email.lower().strip(),
        reason=cleaned[:500],
        created_at=now,
        expires_at=now + ttl,
        staff_session_id=staff_session_id,
        target_clerk_user_id=target_clerk_user_id,
        target_label=(target_label or target_email)[:120],
    )
    client.setex(f"{IMP_PREFIX}{sid}", ttl, json.dumps(session.to_dict()))
    logger.info(
        "impersonation_started actor=%s target=%s:%s reason_len=%s",
        actor_admin_id,
        target_type,
        target_id,
        len(cleaned),
    )
    return session


def get_session(session_id: str) -> ImpersonationSession | None:
    client = _client()
    if client is None or not session_id:
        return None
    raw = client.get(f"{IMP_PREFIX}{session_id}")
    if not raw:
        return None
    try:
        data = json.loads(raw)
        session = ImpersonationSession.from_dict(data)
    except (TypeError, ValueError, KeyError):
        return None
    if session.expires_at <= time.time():
        revoke_session(session_id)
        return None
    return session


def resolve_from_authorization(authorization: str | None) -> ImpersonationSession | None:
    sid = session_id_from_authorization(authorization)
    if not sid:
        return None
    return get_session(sid)


def resolve_from_bearer(token: str | None) -> ImpersonationSession | None:
    sid = session_id_from_bearer(token)
    if not sid:
        return None
    return get_session(sid)


def revoke_session(session_id: str) -> bool:
    client = _client()
    if client is None or not session_id:
        return False
    deleted = bool(client.delete(f"{IMP_PREFIX}{session_id}"))
    if deleted:
        logger.info("impersonation_stopped session=%s", session_id)
    return deleted
