"""Resolve customer context from Clerk JWT + Porterchain customers table."""

from fastapi import HTTPException
from sqlalchemy.orm import Session

from porterchain_api.auth.clerk import ClerkClaims
from porterchain_api.auth.clerk_client import ClerkClient
from porterchain_api.auth.clerk_registry import fetch_clerk_user, is_clerk_secret_configured
from porterchain_api.auth.portal_guard import assert_clerk_id_exclusive
from porterchain_api.booking_engine import CustomerService
from porterchain_api.config import Settings
from porterchain_api.booking_models import Customer
from porterchain_api.user_models import PorterchainUser

_customers = CustomerService()


def resolve_customer_contact(
    db: Session,
    claims: ClerkClaims,
    settings: Settings,
) -> tuple[str | None, str | None]:
    """Resolve Clerk-attested email (JWT / verified Backend). Phone may use DB fallback."""
    from porterchain_api.auth.email_identity import normalize_email, resolve_verified_clerk_email

    email = normalize_email(claims.email)
    phone = claims.phone

    if not email:
        try:
            email = resolve_verified_clerk_email(
                jwt_email=None,
                clerk_user_id=claims.clerk_user_id,
                settings=settings,
            )
        except PermissionError:
            email = None

    if not phone:
        user = (
            db.query(PorterchainUser)
            .filter(PorterchainUser.clerk_user_id == claims.clerk_user_id)
            .first()
        )
        if user and user.phone:
            phone = user.phone
        if not phone:
            customer = _customers.get_by_clerk(db, claims.clerk_user_id)
            if customer:
                phone = customer.phone

    if not phone and is_clerk_secret_configured(settings):
        try:
            clerk_user, _kind = fetch_clerk_user(settings, claims.clerk_user_id)
            if clerk_user:
                phone = ClerkClient.primary_phone(clerk_user)
        except Exception:
            pass

    return email, phone


def require_customer(
    db: Session,
    claims: ClerkClaims,
    settings: Settings,
) -> Customer:
    assert_clerk_id_exclusive(db, claims, portal="customer", settings=settings)
    email, phone = resolve_customer_contact(db, claims, settings)
    try:
        customer = _customers.get_or_create_from_clerk(
            db,
            clerk_user_id=claims.clerk_user_id,
            email=email,
            phone=phone,
        )
    except ValueError as exc:
        detail = str(exc)
        if detail == "email_required":
            raise HTTPException(status_code=400, detail="email_required") from exc
        if detail == "email_clerk_mismatch":
            raise HTTPException(status_code=403, detail="email_clerk_mismatch") from exc
        # C-23: staff/driver Clerk on customer portal must not 500.
        if detail.startswith("identity_conflict"):
            raise HTTPException(status_code=403, detail=detail) from exc
        raise

    from porterchain_api.auth.dependencies import assert_self_scope, resolve_principal_for_claims

    # Local CLERK_DEV_BYPASS synthetic subject has no SpiceDB tuples by design.
    if claims.clerk_user_id != "dev_clerk_user":
        principal = resolve_principal_for_claims(db, claims)
        if not principal:
            raise HTTPException(status_code=403, detail="user_not_provisioned")
        assert_self_scope(principal, customer.id, db)
    return customer
