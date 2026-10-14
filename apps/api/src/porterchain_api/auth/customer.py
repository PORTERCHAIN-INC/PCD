"""Resolve customer context from Clerk JWT + Porterchain customers table."""

from fastapi import HTTPException
from sqlalchemy.orm import Session

from porterchain_api.auth.clerk import ClerkClaims
from porterchain_api.auth.clerk_client import ClerkClient
from porterchain_api.auth.clerk_registry import fetch_clerk_user, is_clerk_secret_configured
from porterchain_api.auth.dev import is_dev_bypass_subject
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

    # Clerk Backend lookup happens BEFORE any query so the request never holds a
    # transaction open while waiting on the network. DB phone still wins.
    clerk_phone: str | None = None
    if not phone and is_clerk_secret_configured(settings):
        clerk_phone = _clerk_phone_cached(settings, claims.clerk_user_id)

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

    if not phone:
        phone = clerk_phone

    return email, phone


_PHONE_CACHE_TTL_S = 300.0
_phone_cache: dict[str, tuple[float, str | None]] = {}


def _clerk_phone_cached(settings: Settings, clerk_user_id: str) -> str | None:
    import time

    now = time.monotonic()
    hit = _phone_cache.get(clerk_user_id)
    if hit and hit[0] > now:
        return hit[1]
    phone = None
    try:
        clerk_user, _kind = fetch_clerk_user(settings, clerk_user_id)
        if clerk_user:
            phone = ClerkClient.primary_phone(clerk_user)
    except Exception:  # noqa: BLE001
        phone = None
    if len(_phone_cache) > 10_000:
        _phone_cache.clear()
    _phone_cache[clerk_user_id] = (now + _PHONE_CACHE_TTL_S, phone)
    return phone


def require_customer(
    db: Session,
    claims: ClerkClaims,
    settings: Settings,
) -> Customer:
    meta = getattr(claims, "public_metadata", None) or {}
    if meta.get("impersonation") and meta.get("user_type") == "customer":
        customer = db.get(Customer, str(meta.get("target_id") or ""))
        if not customer:
            raise HTTPException(status_code=404, detail="customer_not_found")
        return customer

    # Contact first: its Clerk lookups run before this request's first query.
    email, phone = resolve_customer_contact(db, claims, settings)
    assert_clerk_id_exclusive(db, claims, portal="customer", settings=settings)
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
    if not is_dev_bypass_subject(claims.clerk_user_id):
        principal = resolve_principal_for_claims(db, claims)
        if not principal:
            raise HTTPException(status_code=403, detail="user_not_provisioned")
        assert_self_scope(principal, customer.id, db)
    return customer
