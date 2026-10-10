"""Staff IdP WebAuthn (passkeys) — challenge store + register/login verify."""

from __future__ import annotations

import json
import logging
import secrets
import time
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

from sqlalchemy.orm import Session
from webauthn import (
    generate_authentication_options,
    generate_registration_options,
    options_to_json,
    verify_authentication_response,
    verify_registration_response,
)
from webauthn.helpers import base64url_to_bytes, bytes_to_base64url
from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria,
    PublicKeyCredentialDescriptor,
    ResidentKeyRequirement,
    UserVerificationRequirement,
)

from porterchain_api.admin_models import AdminUser, StaffWebAuthnCredential
from porterchain_api.auth.staff_session import _client, create_session
from porterchain_api.config import Settings

logger = logging.getLogger("porterchain.security")

CHALLENGE_PREFIX = "pc:staff:webauthn:chal:v1:"
CHALLENGE_TTL = 300  # 5 minutes
RP_NAME = "Porterchain Admin"


def _rp_id(settings: Settings) -> str:
    host = urlparse(settings.admin_portal_url or "http://localhost:3002").hostname or "localhost"
    return host


def _origin(settings: Settings) -> str:
    parsed = urlparse(settings.admin_portal_url or "http://localhost:3002")
    if parsed.scheme and parsed.netloc:
        return f"{parsed.scheme}://{parsed.netloc}"
    return "http://localhost:3002"


def _store_challenge(kind: str, admin_user_id: str, challenge_b64: str) -> str:
    client = _client()
    if client is None:
        raise ValueError("staff_webauthn_redis_unavailable")
    challenge_id = secrets.token_urlsafe(16)
    payload = {
        "kind": kind,
        "admin_user_id": admin_user_id,
        "challenge": challenge_b64,
        "expires_at": int(time.time()) + CHALLENGE_TTL,
    }
    client.setex(f"{CHALLENGE_PREFIX}{challenge_id}", CHALLENGE_TTL, json.dumps(payload))
    return challenge_id


def _pop_challenge(challenge_id: str) -> dict[str, Any] | None:
    client = _client()
    if client is None or not challenge_id:
        return None
    key = f"{CHALLENGE_PREFIX}{challenge_id}"
    try:
        raw = client.get(key)
        if not raw:
            return None
        client.delete(key)
        data = json.loads(raw)
        return data if isinstance(data, dict) else None
    except Exception:
        logger.debug("staff_webauthn_challenge_pop_failed", exc_info=True)
        return None


def registration_options(db: Session, settings: Settings, admin_user: AdminUser) -> dict[str, Any]:
    existing = (
        db.query(StaffWebAuthnCredential)
        .filter(StaffWebAuthnCredential.admin_user_id == admin_user.id)
        .all()
    )
    exclude = [
        PublicKeyCredentialDescriptor(id=base64url_to_bytes(c.credential_id)) for c in existing
    ]
    options = generate_registration_options(
        rp_id=_rp_id(settings),
        rp_name=RP_NAME,
        user_id=admin_user.id.encode("utf-8"),
        user_name=admin_user.email,
        user_display_name=admin_user.name or admin_user.email,
        exclude_credentials=exclude,
        authenticator_selection=AuthenticatorSelectionCriteria(
            resident_key=ResidentKeyRequirement.PREFERRED,
            user_verification=UserVerificationRequirement.REQUIRED,
        ),
    )
    challenge_id = _store_challenge(
        "register", admin_user.id, bytes_to_base64url(options.challenge)
    )
    payload = json.loads(options_to_json(options))
    payload["challenge_id"] = challenge_id
    return payload


def verify_registration(
    db: Session,
    settings: Settings,
    *,
    admin_user: AdminUser,
    challenge_id: str,
    credential: dict[str, Any],
    device_label: str | None = None,
) -> StaffWebAuthnCredential:
    stored = _pop_challenge(challenge_id)
    if not stored or stored.get("kind") != "register":
        raise ValueError("webauthn_challenge_invalid")
    if stored.get("admin_user_id") != admin_user.id:
        raise ValueError("webauthn_challenge_mismatch")

    verification = verify_registration_response(
        credential=credential,
        expected_challenge=base64url_to_bytes(stored["challenge"]),
        expected_rp_id=_rp_id(settings),
        expected_origin=_origin(settings),
    )
    cred_id = bytes_to_base64url(verification.credential_id)
    row = StaffWebAuthnCredential(
        admin_user_id=admin_user.id,
        credential_id=cred_id,
        public_key=bytes_to_base64url(verification.credential_public_key),
        sign_count=int(verification.sign_count or 0),
        device_label=(device_label or "").strip() or None,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def authentication_options(db: Session, settings: Settings, *, email: str) -> dict[str, Any]:
    """Public passkey login options — never reveal whether the email exists or has creds."""
    normalized = email.lower().strip()
    if not normalized:
        raise ValueError("email_required")

    user = (
        db.query(AdminUser)
        .filter(AdminUser.email == normalized, AdminUser.is_active.is_(True))
        .first()
    )
    creds: list[StaffWebAuthnCredential] = []
    if user:
        creds = (
            db.query(StaffWebAuthnCredential)
            .filter(StaffWebAuthnCredential.admin_user_id == user.id)
            .all()
        )

    if user and creds:
        allow = [
            PublicKeyCredentialDescriptor(id=base64url_to_bytes(c.credential_id)) for c in creds
        ]
        options = generate_authentication_options(
            rp_id=_rp_id(settings),
            allow_credentials=allow,
            user_verification=UserVerificationRequirement.REQUIRED,
        )
        challenge_id = _store_challenge(
            "login", user.id, bytes_to_base64url(options.challenge)
        )
    else:
        # Decoy: identical shape so unknown emails / no-passkey staff are indistinguishable.
        options = generate_authentication_options(
            rp_id=_rp_id(settings),
            allow_credentials=[],
            user_verification=UserVerificationRequirement.REQUIRED,
        )
        challenge_id = _store_challenge(
            "login_decoy",
            "decoy",
            bytes_to_base64url(options.challenge),
        )

    payload = json.loads(options_to_json(options))
    payload["challenge_id"] = challenge_id
    payload["email"] = normalized
    return payload


def verify_authentication(
    db: Session,
    settings: Settings,
    *,
    challenge_id: str,
    credential: dict[str, Any],
    client_meta: dict[str, str] | None = None,
) -> dict[str, Any]:
    stored = _pop_challenge(challenge_id)
    if not stored:
        raise ValueError("webauthn_challenge_invalid")
    kind = stored.get("kind")
    if kind == "login_decoy":
        # Anti-enumeration: decoy challenges always fail the same way.
        raise ValueError("passkey_login_failed")
    if kind != "login":
        raise ValueError("webauthn_challenge_invalid")

    admin_user_id = str(stored["admin_user_id"])
    user = db.query(AdminUser).filter(AdminUser.id == admin_user_id).first()
    if not user or not user.is_active:
        raise ValueError("passkey_login_failed")

    raw_id = credential.get("id") or credential.get("rawId")
    if not raw_id:
        raise ValueError("webauthn_credential_id_required")
    cred_id = str(raw_id)
    row = (
        db.query(StaffWebAuthnCredential)
        .filter(
            StaffWebAuthnCredential.admin_user_id == user.id,
            StaffWebAuthnCredential.credential_id == cred_id,
        )
        .first()
    )
    if not row:
        raise ValueError("passkey_login_failed")

    verification = verify_authentication_response(
        credential=credential,
        expected_challenge=base64url_to_bytes(stored["challenge"]),
        expected_rp_id=_rp_id(settings),
        expected_origin=_origin(settings),
        credential_public_key=base64url_to_bytes(row.public_key),
        credential_current_sign_count=row.sign_count,
    )
    row.sign_count = int(verification.new_sign_count or row.sign_count)
    row.last_used_at = datetime.now(UTC)
    db.commit()

    from porterchain_api.admin_engine.staff_idp_service import ensure_staff_identity

    ensure_staff_identity(db, user)
    db.refresh(user)

    from porterchain_api.auth.staff_mail import notify_login_if_new_device

    notify_login_if_new_device(
        settings,
        admin_user_id=user.id,
        email=user.email,
        client_meta=client_meta,
    )

    session = create_session(
        admin_user_id=user.id,
        email=user.email,
        role=user.role,
        client_meta=client_meta,
    )
    if session is None:
        raise ValueError("staff_session_redis_unavailable")
    return {
        "admin_user_id": user.id,
        "email": user.email,
        "role": user.role,
        "session_id": session.session_id,
        "bearer_token": f"staff_sess_{session.session_id}",
        "expires_at": session.expires_at,
    }


def step_up_options(db: Session, settings: Settings, *, admin_user: AdminUser) -> dict[str, Any]:
    """WebAuthn options for an authenticated staff step-up (requires enrolled passkey)."""
    creds = (
        db.query(StaffWebAuthnCredential)
        .filter(StaffWebAuthnCredential.admin_user_id == admin_user.id)
        .all()
    )
    if not creds:
        raise ValueError("staff_passkey_not_registered")
    allow = [
        PublicKeyCredentialDescriptor(id=base64url_to_bytes(c.credential_id)) for c in creds
    ]
    options = generate_authentication_options(
        rp_id=_rp_id(settings),
        allow_credentials=allow,
        user_verification=UserVerificationRequirement.REQUIRED,
    )
    challenge_id = _store_challenge("login", admin_user.id, bytes_to_base64url(options.challenge))
    payload = json.loads(options_to_json(options))
    payload["challenge_id"] = challenge_id
    payload["email"] = admin_user.email
    return payload


def confirm_passkey_for_admin(
    db: Session,
    settings: Settings,
    *,
    admin_user: AdminUser,
    challenge_id: str,
    credential: dict[str, Any],
) -> None:
    """Verify a passkey assertion for an already-authenticated admin (step-up)."""
    stored = _pop_challenge(challenge_id)
    if not stored or stored.get("kind") != "login":
        raise ValueError("webauthn_challenge_invalid")
    if str(stored.get("admin_user_id")) != admin_user.id:
        raise ValueError("webauthn_challenge_mismatch")

    raw_id = credential.get("id") or credential.get("rawId")
    if not raw_id:
        raise ValueError("webauthn_credential_id_required")
    cred_id = str(raw_id)
    row = (
        db.query(StaffWebAuthnCredential)
        .filter(
            StaffWebAuthnCredential.admin_user_id == admin_user.id,
            StaffWebAuthnCredential.credential_id == cred_id,
        )
        .first()
    )
    if not row:
        raise ValueError("passkey_login_failed")

    verification = verify_authentication_response(
        credential=credential,
        expected_challenge=base64url_to_bytes(stored["challenge"]),
        expected_rp_id=_rp_id(settings),
        expected_origin=_origin(settings),
        credential_public_key=base64url_to_bytes(row.public_key),
        credential_current_sign_count=row.sign_count,
    )
    row.sign_count = int(verification.new_sign_count or row.sign_count)
    row.last_used_at = datetime.now(UTC)
    db.commit()
