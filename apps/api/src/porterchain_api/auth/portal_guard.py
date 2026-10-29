"""Portal surface guards — identity checks (Platform / unified only).

Phase D3: enterprise 4-app Clerk is retired. Tokens are always Platform;
multi-role same subject is allowed; portal visit does not assign roles —
provisioning still required for staff/merchant/driver.
"""

from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session

from porterchain_api.auth.claims import IdentityClaims
from porterchain_api.auth.dev import is_dev_bypass_subject
from porterchain_api.auth.persona_bundle import load_persona_bundle
from porterchain_api.config import Settings


def subject_staff_portal(db: Session, clerk_user_id: str) -> str | None:
    """Return admin, merchant, or driver when this Clerk id is provisioned outside retail."""
    if not clerk_user_id or clerk_user_id.startswith("pending:") or is_dev_bypass_subject(clerk_user_id):
        return None
    return load_persona_bundle(db, clerk_user_id).staff_portal()


def assert_portal_provisioned(
    db: Session,
    claims: IdentityClaims,
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
