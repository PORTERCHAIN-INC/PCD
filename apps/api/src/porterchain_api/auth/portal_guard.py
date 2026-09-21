"""Portal surface guards — identity checks (Platform / unified only).

Phase D3: enterprise 4-app Clerk is retired. Tokens are always Platform;
multi-role same subject is allowed; portal visit does not assign roles —
provisioning still required for staff/merchant/driver.
"""

from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session

from porterchain_api.auth.claims import ClerkClaims
from porterchain_api.auth.clerk_registry import clerk_app_configs
from porterchain_api.auth.dev import is_dev_bypass_subject
from porterchain_api.auth.persona_bundle import load_persona_bundle
from porterchain_api.config import Settings


def clerk_id_staff_portal(db: Session, clerk_user_id: str) -> str | None:
    """Return admin, merchant, or driver when this Clerk id is provisioned outside retail."""
    if not clerk_user_id or clerk_user_id.startswith("pending:") or is_dev_bypass_subject(clerk_user_id):
        return None
    return load_persona_bundle(db, clerk_user_id).staff_portal()


def is_legacy_shared_clerk_app(settings: Settings) -> bool:
    """True when all user classes share one Clerk Backend API key."""
    apps = clerk_app_configs(settings)
    if not apps:
        return False
    secrets = {a.secret_key for a in apps if a.secret_key}
    return len(secrets) == 1


def is_unified_clerk_app(settings: Settings) -> bool:
    """True when all configured Clerk slots share one issuer (legacy local collapse).

    Named historically; platform_driver with distinct Driver returns False.
    """
    _ = settings.clerk_unified_mode  # retired flag — ignored
    apps = [a for a in clerk_app_configs(settings) if a.secret_key and a.jwks_url]
    if len(apps) < 2:
        return is_legacy_shared_clerk_app(settings)
    secrets = {a.secret_key for a in apps}
    jwks = {a.jwks_url for a in apps}
    return len(secrets) == 1 and len(jwks) == 1


def assert_clerk_id_exclusive(
    db: Session,
    claims: ClerkClaims,
    *,
    portal: str,
    settings: Settings,
) -> None:
    """
    Unified multi-role behavior (always): allow the same Clerk subject across
    portals; still require portal-specific provisioning (except customer
    auto-provision path).

    ``settings`` retained for call-site compatibility; enterprise exclusivity
    (one Clerk id ⇒ one portal class) is retired.
    """
    _ = settings  # Platform-only; unused

    clerk_id = claims.clerk_user_id
    if not clerk_id or clerk_id.startswith("pending:") or is_dev_bypass_subject(clerk_id):
        return

    portal_norm = "admin" if portal in ("admin", "staff") else portal
    membership = load_persona_bundle(db, clerk_id).membership()

    # Customer auto-provisions; staff portals require a persona row.
    if portal_norm == "customer":
        return
    if not membership.get(portal_norm):
        raise HTTPException(status_code=403, detail=f"{portal_norm}_user_not_provisioned")
