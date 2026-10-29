"""Local-only auth bypass helpers — never active in staging/production."""

from __future__ import annotations

from typing import Any

from porterchain_api.auth.claims import IdentityClaims
from porterchain_api.config import Settings
from porterchain_shared.config.project_mode import ProjectMode, project_mode_for_app_env

DEV_BYPASS_DRIVER_EMAIL = "marco@porterchain.com"
DEV_STAFF_EMAIL = "admin@porterchain.com"
DEV_MERCHANT_EMAIL = "merchant@porterchain.com"
DEV_CUSTOMER_EMAIL = "customer@porterchain.com"

DEV_LEGACY_SUBJECT = "dev_clerk_user"
DEV_MERCHANT_SUBJECT = "dev_merchant_user"
DEV_CUSTOMER_SUBJECT = "dev_customer_user"
DEV_PORTAL_HEADER = "x-porterchain-portal"

_DEV_SUBJECTS = frozenset({DEV_LEGACY_SUBJECT, DEV_MERCHANT_SUBJECT, DEV_CUSTOMER_SUBJECT})
_PORTALS = frozenset({"merchant", "customer", "admin", "driver"})


def allow_auth_dev_bypass(settings: Settings) -> bool:
    """True only in development project mode with AUTH_DEV_BYPASS=true."""
    return (
        project_mode_for_app_env(settings.app_env) is ProjectMode.DEVELOPMENT
        and settings.auth_dev_bypass
    )


def is_dev_bypass_subject(auth_subject: str | None) -> bool:
    """Synthetic local Bearer-dev Clerk ids — no SpiceDB tuples by design."""
    return bool(auth_subject) and auth_subject in _DEV_SUBJECTS


def is_merchant_dev_subject(auth_subject: str | None) -> bool:
    return auth_subject in {DEV_MERCHANT_SUBJECT, DEV_LEGACY_SUBJECT}


def resolve_dev_portal(*, path: str = "", header: str | None = None) -> str:
    """Pick the local persona from an explicit portal header, else the API path."""
    raw = (header or "").strip().lower()
    if raw in _PORTALS:
        return raw
    p = path or ""
    if (
        p.startswith("/v1/merchant")
        or p.startswith("/v1/merchants")
        or p.startswith("/v1/auth/merchant")
    ):
        return "merchant"
    if (
        p.startswith("/v1/customers")
        or p.startswith("/v1/customer")
        or p.startswith("/v1/auth/customer")
        or p.startswith("/v1/bookings")
    ):
        return "customer"
    if p.startswith("/driver-api"):
        return "driver"
    if p.startswith("/v1/admin"):
        return "admin"
    return "admin"


def dev_claims_for(portal: str) -> IdentityClaims:
    """One synthetic Clerk subject per portal — never reuse staff email on merchant/customer."""
    if portal == "merchant":
        return IdentityClaims(
            auth_subject=DEV_MERCHANT_SUBJECT,
            email=DEV_MERCHANT_EMAIL,
            org_id=None,
            org_role="org:admin",
            public_metadata={"role": "merchant_owner"},
            session_id="dev_session_merchant",
            clerk_app="merchant",
            issuer="https://clerk.porterchain.local",
            authorized_party="pk_dev",
            auth_time=0,
        )
    if portal == "customer":
        return IdentityClaims(
            auth_subject=DEV_CUSTOMER_SUBJECT,
            email=DEV_CUSTOMER_EMAIL,
            phone="+1 416-555-4401",
            public_metadata={"role": "customer"},
            session_id="dev_session_customer",
            clerk_app="customer",
            issuer="https://clerk.porterchain.local",
            authorized_party="pk_dev",
            auth_time=0,
        )
    return IdentityClaims(
        auth_subject=DEV_LEGACY_SUBJECT,
        email=DEV_STAFF_EMAIL,
        org_id=None,
        org_role="dispatcher",
        public_metadata={"role": "dispatcher"},
        session_id="dev_session",
        clerk_app="admin",
        issuer="https://clerk.porterchain.local",
        authorized_party="pk_dev",
        auth_time=0,
    )


def resolve_dev_bypass_driver(db: Any) -> Any | None:
    """Bearer ``dev`` uses the seeded field driver, not leftover pytest rows."""
    from porterchain_api.admin_models import Driver
    from porterchain_api.domain.admin_states import DriverStatus

    preferred = (
        db.query(Driver)
        .filter(
            Driver.status == DriverStatus.APPROVED.value,
            Driver.email == DEV_BYPASS_DRIVER_EMAIL,
        )
        .first()
    )
    if preferred:
        return preferred
    return (
        db.query(Driver)
        .filter(Driver.status == DriverStatus.APPROVED.value)
        .order_by(Driver.created_at.asc())
        .first()
    )
