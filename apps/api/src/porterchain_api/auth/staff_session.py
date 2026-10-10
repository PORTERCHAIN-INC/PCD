"""Staff IdP session store (Redis) — SSOT for admin.porterchain.com auth.

Clerk JWT is retired for admin (``admin_clerk_retired_use_staff_idp``). Sessions are
opaque Redis ids exposed as HttpOnly ``pc_staff_sid`` and/or ``Bearer staff_sess_*``.
Admin browser should prefer the Next BFF cookie path so JS never holds the bearer.

Lifecycle:
- Idle sliding TTL on each authenticated touch
- Absolute max lifetime from ``created_at``
- Per-user Redis set index for list / revoke-all
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
USER_INDEX_PREFIX = "pc:staff:sessions:user:v1:"
DEFAULT_TTL_SECONDS = 60 * 60 * 12  # idle sliding window
ABSOLUTE_MAX_SECONDS = 60 * 60 * 24  # hard cap from created_at
STEP_UP_MAX_AGE_SECONDS = 15 * 60  # sensitive actions need recent step-up
STAFF_COOKIE_NAME = "pc_staff_sid"
STAFF_BEARER_PREFIX = "staff_sess_"


def staff_cookie_params(settings, *, max_age: int = DEFAULT_TTL_SECONDS) -> dict:
    """HttpOnly cookie attrs for Set-Cookie / delete_cookie."""
    from porterchain_shared.config.project_mode import runtime_posture_from_settings

    posture = runtime_posture_from_settings(settings)
    # Cross-subdomain in prod (admin.* ↔ api.*) needs Domain + SameSite=None.
    host_only = posture.cookie_domain_mode == "host_only"
    domain = None if host_only else ".porterchain.com"
    return {
        "key": STAFF_COOKIE_NAME,
        "httponly": True,
        "secure": not host_only,
        "samesite": "lax" if host_only else "none",
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
    absolute_expires_at: float = 0.0
    step_up_at: float = 0.0
    client_ip: str = ""
    user_agent: str = ""
    device_label: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StaffSession:
        created = float(data["created_at"])
        absolute = float(data.get("absolute_expires_at") or (created + ABSOLUTE_MAX_SECONDS))
        return cls(
            session_id=str(data["session_id"]),
            admin_user_id=str(data["admin_user_id"]),
            email=str(data["email"]),
            role=str(data["role"]),
            created_at=created,
            expires_at=float(data["expires_at"]),
            absolute_expires_at=absolute,
            step_up_at=float(data.get("step_up_at") or created),
            client_ip=str(data.get("client_ip") or "")[:64],
            user_agent=str(data.get("user_agent") or "")[:256],
            device_label=str(data.get("device_label") or "")[:64],
        )

    def replace(self, **kwargs: Any) -> StaffSession:
        return StaffSession(
            session_id=kwargs.get("session_id", self.session_id),
            admin_user_id=kwargs.get("admin_user_id", self.admin_user_id),
            email=kwargs.get("email", self.email),
            role=kwargs.get("role", self.role),
            created_at=kwargs.get("created_at", self.created_at),
            expires_at=kwargs.get("expires_at", self.expires_at),
            absolute_expires_at=kwargs.get("absolute_expires_at", self.absolute_expires_at),
            step_up_at=kwargs.get("step_up_at", self.step_up_at),
            client_ip=kwargs.get("client_ip", self.client_ip),
            user_agent=kwargs.get("user_agent", self.user_agent),
            device_label=kwargs.get("device_label", self.device_label),
        )

    def public_dict(self, *, current_session_id: str | None = None) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "email": self.email,
            "role": self.role,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "absolute_expires_at": self.absolute_expires_at,
            "step_up_at": self.step_up_at,
            "client_ip": self.client_ip or None,
            "user_agent": self.user_agent or None,
            "device_label": self.device_label or None,
            "is_current": bool(current_session_id and current_session_id == self.session_id),
        }


def _device_label_from_ua(ua: str) -> str:
    low = (ua or "").lower()
    if "iphone" in low or "ipad" in low:
        return "iOS"
    if "android" in low:
        return "Android"
    if "edg/" in low:
        return "Edge"
    if "firefox" in low:
        return "Firefox"
    if "chrome" in low and "safari" in low:
        return "Chrome"
    if "safari" in low:
        return "Safari"
    return "Browser" if ua else ""


def client_meta_from_request(request: Any | None) -> dict[str, str]:
    """Coarse device honesty for session rows (IP + UA label)."""
    if request is None:
        return {}
    forwarded = ""
    try:
        forwarded = (request.headers.get("x-forwarded-for") or "").split(",")[0].strip()
    except Exception:  # noqa: BLE001
        forwarded = ""
    client_ip = forwarded
    if not client_ip:
        try:
            client_ip = getattr(getattr(request, "client", None), "host", None) or ""
        except Exception:  # noqa: BLE001
            client_ip = ""
    try:
        ua = (request.headers.get("user-agent") or "").strip()
    except Exception:  # noqa: BLE001
        ua = ""
    return {
        "client_ip": str(client_ip)[:64],
        "user_agent": str(ua)[:256],
        "device_label": _device_label_from_ua(ua)[:64],
    }


def _client():
    try:
        from porterchain_shared.redis_client import get_redis_client

        client = get_redis_client()
        client.ping()
        return client
    except Exception:  # noqa: BLE001
        return None


def _user_index_key(admin_user_id: str) -> str:
    return f"{USER_INDEX_PREFIX}{admin_user_id}"


def _index_add(client, *, admin_user_id: str, session_id: str, ttl: int) -> None:
    key = _user_index_key(admin_user_id)
    client.sadd(key, session_id)
    client.expire(key, max(ttl, ABSOLUTE_MAX_SECONDS))


def _index_remove(client, *, admin_user_id: str, session_id: str) -> None:
    try:
        client.srem(_user_index_key(admin_user_id), session_id)
    except Exception:
        logger.debug("staff_session_index_remove_failed", exc_info=True)


def create_session(
    *,
    admin_user_id: str,
    email: str,
    role: str,
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
    client_ip: str = "",
    user_agent: str = "",
    device_label: str = "",
    client_meta: dict[str, str] | None = None,
) -> StaffSession | None:
    """Create a staff session and index it under the admin user. Returns None if Redis is down."""
    client = _client()
    if client is None or not admin_user_id:
        return None
    meta = client_meta or {}
    now = time.time()
    idle = max(60, ttl_seconds)
    absolute = now + ABSOLUTE_MAX_SECONDS
    session = StaffSession(
        session_id=secrets.token_urlsafe(32),
        admin_user_id=admin_user_id,
        email=email.lower().strip(),
        role=role,
        created_at=now,
        expires_at=now + idle,
        absolute_expires_at=absolute,
        step_up_at=now,
        client_ip=str(meta.get("client_ip") or client_ip or "")[:64],
        user_agent=str(meta.get("user_agent") or user_agent or "")[:256],
        device_label=str(meta.get("device_label") or device_label or "")[:64],
    )
    try:
        client.setex(
            f"{SESSION_PREFIX}{session.session_id}",
            idle,
            json.dumps(session.to_dict()),
        )
        _index_add(client, admin_user_id=admin_user_id, session_id=session.session_id, ttl=ABSOLUTE_MAX_SECONDS)
        return session
    except Exception:
        logger.exception("staff_session_create_failed")
        return None


def get_session(session_id: str, *, touch: bool = True) -> StaffSession | None:
    """Load session. When ``touch`` is True, slide idle TTL (capped by absolute max)."""
    if not session_id:
        return None
    client = _client()
    if client is None:
        return None
    key = f"{SESSION_PREFIX}{session_id}"
    try:
        raw = client.get(key)
        if not raw:
            return None
        data = json.loads(raw)
        if not isinstance(data, dict):
            return None
        session = StaffSession.from_dict(data)
        now = time.time()
        if session.absolute_expires_at and now >= session.absolute_expires_at:
            revoke_session(session_id)
            return None
        if session.expires_at < now:
            revoke_session(session_id)
            return None
        if touch:
            idle = DEFAULT_TTL_SECONDS
            new_expires = min(now + idle, session.absolute_expires_at or (now + idle))
            remaining = max(60, int(new_expires - now))
            updated = session.replace(expires_at=new_expires)
            client.setex(key, remaining, json.dumps(updated.to_dict()))
            return updated
        return session
    except Exception:
        logger.debug("staff_session_get_failed", exc_info=True)
        return None


def revoke_session(session_id: str) -> bool:
    if not session_id:
        return False
    client = _client()
    if client is None:
        return False
    key = f"{SESSION_PREFIX}{session_id}"
    try:
        raw = client.get(key)
        admin_user_id = None
        if raw:
            try:
                data = json.loads(raw)
                if isinstance(data, dict):
                    admin_user_id = str(data.get("admin_user_id") or "") or None
            except Exception:  # noqa: BLE001
                admin_user_id = None
        deleted = bool(client.delete(key))
        if admin_user_id:
            _index_remove(client, admin_user_id=admin_user_id, session_id=session_id)
        return deleted
    except Exception:
        logger.debug("staff_session_revoke_failed", exc_info=True)
        return False


def revoke_all_for_user(admin_user_id: str, *, except_session_id: str | None = None) -> int:
    """Revoke every session for a staff user. Returns count revoked."""
    if not admin_user_id:
        return 0
    client = _client()
    if client is None:
        return 0
    try:
        members = client.smembers(_user_index_key(admin_user_id)) or set()
    except Exception:
        logger.debug("staff_session_list_index_failed", exc_info=True)
        return 0
    revoked = 0
    for raw_sid in members:
        sid = raw_sid.decode() if isinstance(raw_sid, bytes) else str(raw_sid)
        if except_session_id and sid == except_session_id:
            continue
        if revoke_session(sid):
            revoked += 1
    return revoked


def list_sessions_for_user(
    admin_user_id: str,
    *,
    current_session_id: str | None = None,
) -> list[dict[str, Any]]:
    if not admin_user_id:
        return []
    client = _client()
    if client is None:
        return []
    try:
        members = client.smembers(_user_index_key(admin_user_id)) or set()
    except Exception:  # noqa: BLE001
        return []
    out: list[dict[str, Any]] = []
    for raw_sid in members:
        sid = raw_sid.decode() if isinstance(raw_sid, bytes) else str(raw_sid)
        session = get_session(sid, touch=False)
        if session is None:
            _index_remove(client, admin_user_id=admin_user_id, session_id=sid)
            continue
        out.append(session.public_dict(current_session_id=current_session_id))
    out.sort(key=lambda row: float(row.get("created_at") or 0), reverse=True)
    return out


def attach_session_cookie(response: Any, payload: dict[str, Any], settings, *, max_age: int | None = None) -> Any:
    cookie = staff_cookie_params(settings) if max_age is None else staff_cookie_params(settings, max_age=max_age)
    response.set_cookie(
        cookie["key"],
        payload["session_id"],
        max_age=cookie["max_age"],
        httponly=cookie["httponly"],
        secure=cookie["secure"],
        samesite=cookie["samesite"],
        path=cookie["path"],
        domain=cookie["domain"],
    )
    return response


def clear_session_cookie(response: Any, settings) -> Any:
    cookie = staff_cookie_params(settings, max_age=0)
    response.delete_cookie(
        cookie["key"],
        path=cookie["path"],
        domain=cookie["domain"],
        secure=cookie["secure"],
        httponly=cookie["httponly"],
        samesite=cookie["samesite"],
    )
    return response


def peek_enrollment(token: str) -> dict[str, Any]:
    from porterchain_api.admin_engine.staff_idp_service import StaffIdpService

    enrollment = StaffIdpService().peek(token)
    if enrollment is None:
        raise LookupError("enrollment_invalid_or_expired")
    return {
        "email": enrollment.email,
        "role": enrollment.role,
        "expires_at": enrollment.expires_at,
    }


def login_from_body(
    db,
    settings,
    body: dict[str, Any],
    *,
    client_meta: dict[str, str] | None = None,
) -> dict[str, Any]:
    from porterchain_api.admin_engine.staff_idp_service import StaffIdpService
    from porterchain_api.auth import staff_webauthn

    assertion = body.get("passkey_assertion")
    if assertion:
        challenge_id = (body.get("challenge_id") or assertion.get("challenge_id") or "").strip()
        credential = assertion.get("credential") if isinstance(assertion, dict) else None
        if credential is None and isinstance(assertion, dict) and assertion.get("id"):
            credential = assertion
        if not challenge_id or not isinstance(credential, dict):
            raise ValueError("passkey_assertion_invalid")
        return staff_webauthn.verify_authentication(
            db,
            settings,
            challenge_id=challenge_id,
            credential=credential,
            client_meta=client_meta,
        )

    enrollment_token = (body.get("enrollment_token") or "").strip()
    if not enrollment_token:
        raise ValueError("enrollment_token_required")
    return StaffIdpService().activate(
        db, enrollment_token, settings=settings, client_meta=client_meta
    )


def passkey_credential_payload(row) -> dict[str, Any]:
    return {
        "id": row.id,
        "credential_id": row.credential_id,
        "device_label": row.device_label,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "last_used_at": row.last_used_at.isoformat() if getattr(row, "last_used_at", None) else None,
    }


def authentication_options_for_email(db, settings, *, email: str) -> dict[str, Any]:
    from porterchain_api.auth import staff_webauthn

    if not (email or "").strip():
        raise ValueError("email_required")
    return staff_webauthn.authentication_options(db, settings, email=email)


def verify_registration_from_body(db, settings, *, admin_user, body: dict[str, Any]):
    from porterchain_api.auth import staff_webauthn

    challenge_id = (body.get("challenge_id") or "").strip()
    credential = body.get("credential")
    if not challenge_id or not isinstance(credential, dict):
        raise ValueError("passkey_registration_invalid")
    return staff_webauthn.verify_registration(
        db,
        settings,
        admin_user=admin_user,
        challenge_id=challenge_id,
        credential=credential,
        device_label=body.get("device_label"),
    )


def list_passkeys(db, admin_user_id: str) -> list[dict[str, Any]]:
    from porterchain_api.admin_models import StaffWebAuthnCredential

    rows = (
        db.query(StaffWebAuthnCredential)
        .filter(StaffWebAuthnCredential.admin_user_id == admin_user_id)
        .order_by(StaffWebAuthnCredential.created_at.desc())
        .all()
    )
    return [passkey_credential_payload(r) for r in rows]


def delete_all_passkeys(db, admin_user_id: str) -> int:
    """Wipe every passkey for a staff user. Caller commits."""
    from porterchain_api.admin_models import StaffWebAuthnCredential

    rows = (
        db.query(StaffWebAuthnCredential)
        .filter(StaffWebAuthnCredential.admin_user_id == admin_user_id)
        .all()
    )
    for row in rows:
        db.delete(row)
    return len(rows)


def delete_passkey(db, *, admin_user_id: str, credential_row_id: str) -> bool:
    from porterchain_api.admin_models import StaffWebAuthnCredential

    row = (
        db.query(StaffWebAuthnCredential)
        .filter(
            StaffWebAuthnCredential.id == credential_row_id,
            StaffWebAuthnCredential.admin_user_id == admin_user_id,
        )
        .first()
    )
    if not row:
        return False
    db.delete(row)
    db.commit()
    return True


def mark_step_up(session_id: str) -> StaffSession | None:
    """Refresh step-up timestamp on an existing session (after passkey confirm)."""
    session = get_session(session_id, touch=False)
    if session is None:
        return None
    client = _client()
    if client is None:
        return None
    now = time.time()
    updated = session.replace(
        expires_at=min(
            now + DEFAULT_TTL_SECONDS,
            session.absolute_expires_at or (now + DEFAULT_TTL_SECONDS),
        ),
        step_up_at=now,
    )
    remaining = max(60, int(updated.expires_at - now))
    try:
        client.setex(
            f"{SESSION_PREFIX}{session_id}",
            remaining,
            json.dumps(updated.to_dict()),
        )
        return updated
    except Exception:
        logger.debug("staff_session_step_up_failed", exc_info=True)
        return None


def assert_recent_step_up(
    session: StaffSession | None,
    *,
    max_age_seconds: int = STEP_UP_MAX_AGE_SECONDS,
) -> None:
    """Raise PermissionError when the session lacks a fresh step-up."""
    if session is None:
        raise PermissionError("staff_step_up_required")
    age = time.time() - float(session.step_up_at or 0)
    if age < 0 or age > max_age_seconds:
        raise PermissionError("staff_step_up_required")
