"""Portal surface guards — Clerk app class + single identity per user class."""

from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session

from porterchain_api.admin_models import AdminUser, Driver
from porterchain_api.auth.claims import ClerkClaims
from porterchain_api.auth.clerk_registry import ClerkAppKind, clerk_app_configs
from porterchain_api.config import Settings
from porterchain_api.merchant_models import MerchantUser
from porterchain_api.models import Customer

PORTAL_CLERK_APP: dict[str, ClerkAppKind] = {
    "admin": "admin",
    "staff": "admin",
    "merchant": "merchant",
    "driver": "driver",
    "customer": "customer",
}


def clerk_id_staff_portal(db: Session, clerk_user_id: str) -> str | None:
    """Return admin, merchant, or driver when this Clerk id is provisioned outside retail."""
    if not clerk_user_id or clerk_user_id.startswith("pending:") or clerk_user_id == "dev_clerk_user":
        return None
    if db.query(AdminUser.id).filter(AdminUser.clerk_user_id == clerk_user_id).first():
        return "admin"
    if db.query(MerchantUser.id).filter(MerchantUser.clerk_user_id == clerk_user_id).first():
        return "merchant"
    if db.query(Driver.id).filter(Driver.clerk_user_id == clerk_user_id).first():
        return "driver"
    return None


def is_legacy_shared_clerk_app(settings: Settings) -> bool:
    """True when all user classes share one Clerk Backend API key (local dev)."""
    apps = clerk_app_configs(settings)
    if not apps:
        return False
    secrets = {a.secret_key for a in apps if a.secret_key}
    return len(secrets) == 1


def require_clerk_app_for_portal(
    claims: ClerkClaims,
    settings: Settings,
    portal: str,
) -> None:
    """Reject tokens minted for a different Clerk application (production multi-app mode)."""
    if claims.clerk_user_id == "dev_clerk_user":
        return
    if is_legacy_shared_clerk_app(settings):
        return
    expected = PORTAL_CLERK_APP.get(portal)
    if not expected or not claims.clerk_app:
        return
    if claims.clerk_app != expected:
        raise HTTPException(
            status_code=403,
            detail=f"clerk_app_mismatch:expected_{expected}_got_{claims.clerk_app}",
        )


def assert_clerk_id_exclusive(
    db: Session,
    claims: ClerkClaims,
    *,
    portal: str,
    settings: Settings,
) -> None:
    """
    Block cross-portal access when the same Clerk user id is provisioned in another class.

    Porterchain authorization is per user class — one Clerk identity must not hop portals
    even when email addresses match across tables.
    """
    clerk_id = claims.clerk_user_id
    if not clerk_id or clerk_id.startswith("pending:") or clerk_id == "dev_clerk_user":
        return

    portal_norm = "admin" if portal in ("admin", "staff") else portal

    in_admin = db.query(AdminUser.id).filter(AdminUser.clerk_user_id == clerk_id).first() is not None
    in_merchant = db.query(MerchantUser.id).filter(MerchantUser.clerk_user_id == clerk_id).first() is not None
    in_driver = db.query(Driver.id).filter(Driver.clerk_user_id == clerk_id).first() is not None
    in_customer = db.query(Customer.id).filter(Customer.clerk_user_id == clerk_id).first() is not None

    membership = {
        "admin": in_admin,
        "merchant": in_merchant,
        "driver": in_driver,
        "customer": in_customer,
    }

    if portal_norm not in membership:
        return

    # Customer portal may auto-provision — only reject cross-class identities.
    if portal_norm == "customer":
        for other_portal, is_member in membership.items():
            if other_portal != "customer" and is_member:
                raise HTTPException(
                    status_code=403,
                    detail=f"identity_conflict:clerk_user_is_{other_portal}",
                )
        return

    if not membership[portal_norm]:
        raise HTTPException(status_code=403, detail=f"{portal_norm}_user_not_provisioned")

    for other_portal, is_member in membership.items():
        if other_portal == portal_norm:
            continue
        if is_member:
            raise HTTPException(
                status_code=403,
                detail=f"identity_conflict:clerk_user_is_{other_portal}",
            )
