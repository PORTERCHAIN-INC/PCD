"""Keycloak verified email ↔ system profile email identity rules.

Rule: every provisioned profile (admin / merchant / driver / customer) bound to a
Keycloak subject must store the same normalized email as Keycloak's verified primary
email. Keycloak id alone is never enough when emails disagree.

Keycloak verified email SSOT (never trust Porterchain DB as Keycloak identity):
1. Signed session JWT email claim (when present)
2. Keycloak Backend API primary email with verification.status == verified
3. Fail closed — idp_email_required / idp_email_unverified

Mismatched persona rows are hard-deleted — never left as pending links.
"""

from __future__ import annotations

import logging
import time
from dataclasses import replace
from typing import TYPE_CHECKING, Any

from sqlalchemy import or_
from sqlalchemy.orm import Session

from porterchain_api.identity_models import IdentityLink
from porterchain_api.unified_identity_models import UserEmail
from porterchain_api.user_models import PorterchainUser

if TYPE_CHECKING:
    from porterchain_api.auth.claims import IdentityClaims
    from porterchain_api.config import Settings

logger = logging.getLogger("porterchain.security")

EMAIL_IDENTITY_MISMATCH = "email_identity_mismatch"
IDP_EMAIL_REQUIRED = "idp_email_required"
IDP_EMAIL_UNVERIFIED = "idp_email_unverified"

# Short TTL cache: Keycloak Backend lookup when JWT omits email (hot-path backstop).
_EMAIL_CACHE_TTL_S = 60.0
_email_cache: dict[str, tuple[float, str | None, str | None]] = {}


def normalize_email(email: str | None) -> str | None:
    if not email:
        return None
    cleaned = email.strip().lower()
    return cleaned or None


def emails_match(system_email: str | None, identity_email: str | None) -> bool:
    left = normalize_email(system_email)
    right = normalize_email(identity_email)
    if not left or not right:
        return False
    return left == right


def require_idp_email(identity_email: str | None) -> str:
    """Fail closed when Keycloak verified email is missing."""
    normalized = normalize_email(identity_email)
    if not normalized:
        raise PermissionError(IDP_EMAIL_REQUIRED)
    return normalized


def require_system_email_matches_idp(
    system_email: str | None,
    identity_email: str | None,
    *,
    detail: str = EMAIL_IDENTITY_MISMATCH,
) -> None:
    """Raise PermissionError when Keycloak email missing or ≠ system profile email."""
    require_idp_email(identity_email)
    if not emails_match(system_email, identity_email):
        raise PermissionError(detail)


def email_from_jwt_payload(payload: dict[str, Any]) -> str | None:
    """Extract email from Keycloak session JWT (default tokens omit this — customize session token)."""
    for key in ("email", "primary_email_address", "email_address"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return normalize_email(value)
    return None


def verified_primary_email_from_idp_user(user: dict[str, Any]) -> tuple[str | None, str | None]:
    """Return (verified_primary_email, failure_detail).

    failure_detail is IDP_EMAIL_UNVERIFIED when a primary exists but is not verified,
    else IDP_EMAIL_REQUIRED when absent.
    """
    emails = user.get("email_addresses") or []
    if not emails:
        return None, IDP_EMAIL_REQUIRED
    primary_id = user.get("primary_email_address_id")
    primary = None
    for entry in emails:
        if entry.get("id") == primary_id:
            primary = entry
            break
    if primary is None:
        primary = emails[0]
    address = normalize_email(primary.get("email_address") if isinstance(primary, dict) else None)
    if not address:
        return None, IDP_EMAIL_REQUIRED
    status = ((primary.get("verification") or {}) if isinstance(primary, dict) else {}).get("status")
    if status != "verified":
        return None, IDP_EMAIL_UNVERIFIED
    return address, None


def resolve_verified_idp_email(
    *,
    jwt_email: str | None,
    auth_subject: str,
    settings: Settings,
) -> str:
    """Resolve Keycloak-attested verified email. Never reads Porterchain DB.

    Raises PermissionError with IDP_EMAIL_REQUIRED or IDP_EMAIL_UNVERIFIED.
    """
    from_jwt = normalize_email(jwt_email)
    if from_jwt:
        return from_jwt

    from porterchain_api.auth.dev import is_dev_bypass_subject

    if not auth_subject or is_dev_bypass_subject(auth_subject):
        raise PermissionError(IDP_EMAIL_REQUIRED)
    if auth_subject.startswith("pending:") or auth_subject.startswith("pending_"):
        raise PermissionError(IDP_EMAIL_REQUIRED)

    from porterchain_api.auth.identity_directory import fetch_identity_user, is_directory_configured

    if not is_directory_configured(settings):
        logger.warning("idp_email_resolve_failed reason=secret_not_configured")
        raise PermissionError(IDP_EMAIL_REQUIRED)

    now = time.monotonic()
    cached = _email_cache.get(auth_subject)
    if cached and cached[0] > now:
        email, detail = cached[1], cached[2]
        if email:
            return email
        raise PermissionError(detail or IDP_EMAIL_REQUIRED)

    try:
        idp_user, _kind = fetch_identity_user(settings, auth_subject)
    except Exception:
        logger.warning("idp_email_resolve_failed reason=backend_lookup_error", exc_info=True)
        _email_cache[auth_subject] = (now + _EMAIL_CACHE_TTL_S, None, IDP_EMAIL_REQUIRED)
        raise PermissionError(IDP_EMAIL_REQUIRED) from None

    if not idp_user:
        _email_cache[auth_subject] = (now + _EMAIL_CACHE_TTL_S, None, IDP_EMAIL_REQUIRED)
        raise PermissionError(IDP_EMAIL_REQUIRED)

    email, detail = verified_primary_email_from_idp_user(idp_user)
    _email_cache[auth_subject] = (now + _EMAIL_CACHE_TTL_S, email, detail)
    if email:
        return email
    raise PermissionError(detail or IDP_EMAIL_REQUIRED)


def enrich_claims_with_verified_email(claims: IdentityClaims, settings: Settings) -> IdentityClaims:
    """Attach Keycloak verified email onto claims before UserSync / portal authz."""
    if normalize_email(claims.email):
        return replace(claims, email=normalize_email(claims.email))
    from porterchain_api.auth.dev import is_dev_bypass_subject

    if not claims.auth_subject or is_dev_bypass_subject(claims.auth_subject):
        return claims
    if claims.auth_subject.startswith("pending:") or claims.auth_subject.startswith("pending_"):
        return claims
    try:
        email = resolve_verified_idp_email(
            jwt_email=claims.email,
            auth_subject=claims.auth_subject,
            settings=settings,
        )
    except PermissionError:
        logger.warning(
            "idp_email_enrich_failed",
            extra={"auth_subject": claims.auth_subject},
        )
        return claims
    return replace(claims, email=email)


def assert_portal_email_identity(system_email: str | None, identity_email: str | None) -> None:
    """Portal gate: require Keycloak email + exact match to system profile."""
    require_system_email_matches_idp(system_email, identity_email)


def delete_email_mismatched_bindings(
    db: Session,
    *,
    auth_subject: str,
    identity_email: str | None,
) -> int:
    """Hard-delete persona rows where auth_subject is bound to a different email.

    Returns the number of persona rows deleted. Safe to call on every auth sync.
    Does nothing when Keycloak email is missing (cannot verify match).
    """
    from porterchain_api.auth.persona_bundle import invalidate_persona_bundle, load_persona_bundle

    expected = normalize_email(identity_email)
    from porterchain_api.auth.dev import is_dev_bypass_subject

    if not expected or not auth_subject or is_dev_bypass_subject(auth_subject):
        return 0
    if auth_subject.startswith("pending:") or auth_subject.startswith("pending_"):
        return 0

    bundle = load_persona_bundle(db, auth_subject, force=True)
    rows = [
        ("admin_users", bundle.admin),
        *[("merchant_users", mu) for mu in bundle.merchant_users],
        ("drivers", bundle.driver),
        ("customers", bundle.customer),
    ]

    deleted = 0
    for table_name, row in rows:
        if row is None:
            continue
        row_email = normalize_email(getattr(row, "email", None))
        if row_email and row_email == expected:
            continue
        logger.warning(
            "email_identity_mismatch_deleted",
            extra={
                "model": table_name,
                "row_id": getattr(row, "id", None),
                "system_email": row_email,
                "identity_email": expected,
            },
        )
        db.delete(row)
        deleted += 1

    if deleted:
        invalidate_persona_bundle(db, auth_subject)
        _strip_registry_if_no_matching_persona(db, auth_subject=auth_subject, identity_email=expected)

    return deleted


# Back-compat alias used by sync/ensure call sites
unlink_email_mismatched_bindings = delete_email_mismatched_bindings


def _strip_registry_if_no_matching_persona(
    db: Session,
    *,
    auth_subject: str,
    identity_email: str,
) -> None:
    """If mismatch deletes removed all personas, drop elevated registry identity for that keycloak id."""
    from porterchain_api.auth.persona_bundle import load_persona_bundle

    bundle = load_persona_bundle(db, auth_subject, force=True)
    candidates = [
        bundle.admin,
        *bundle.merchant_users,
        bundle.driver,
        bundle.customer,
    ]
    still_bound = any(
        row is not None and emails_match(getattr(row, "email", None), identity_email)
        for row in candidates
    )
    if still_bound:
        return

    user = db.query(PorterchainUser).filter(PorterchainUser.auth_subject == auth_subject).first()
    if not user:
        return
    # Registry email must equal Keycloak; if it already matches and has no personas, leave as unprovisioned.
    if emails_match(user.email, identity_email):
        user.role = "unprovisioned"
        return

    # Hard-delete registry identity that itself carried a mismatched email
    logger.warning(
        "email_identity_mismatch_registry_deleted",
        extra={"user_id": user.id, "system_email": user.email, "identity_email": identity_email},
    )
    db.query(UserEmail).filter(UserEmail.user_id == user.id).delete(synchronize_session=False)
    db.query(IdentityLink).filter(
        or_(IdentityLink.platform_user_id == user.id, IdentityLink.auth_subject == auth_subject)
    ).delete(synchronize_session=False)
    db.delete(user)
