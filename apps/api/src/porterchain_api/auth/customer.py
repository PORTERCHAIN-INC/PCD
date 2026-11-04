"""Resolve customer context from Keycloak JWT + Porterchain customers table."""

from fastapi import HTTPException
from sqlalchemy.orm import Session

from porterchain_api.auth.bearer import IdentityClaims
from porterchain_api.auth.identity_directory import IdentityDirectory
from porterchain_api.auth.identity_directory import fetch_identity_user, is_directory_configured
from porterchain_api.auth.dev import is_dev_bypass_subject
from porterchain_api.auth.portal_guard import assert_portal_provisioned
from porterchain_api.booking_engine import CustomerService
from porterchain_api.config import Settings
from porterchain_api.booking_models import Customer
from porterchain_api.user_models import PorterchainUser

_customers = CustomerService()


def resolve_customer_contact(
    db: Session,
    claims: IdentityClaims,
    settings: Settings,
) -> tuple[str | None, str | None]:
    """Resolve Keycloak-attested email (JWT / verified Backend). Phone may use DB fallback."""
    from porterchain_api.auth.email_identity import normalize_email, resolve_verified_idp_email

    email = normalize_email(claims.email)
    phone = claims.phone

    if not email:
        try:
            email = resolve_verified_idp_email(
                jwt_email=None,
                auth_subject=claims.auth_subject,
                settings=settings,
            )
        except PermissionError:
            email = None

    # Keycloak Backend lookup happens BEFORE any query so the request never holds a
    # transaction open while waiting on the network. DB phone still wins.
    idp_phone: str | None = None
    if not phone and is_directory_configured(settings):
        idp_phone = _idp_phone_cached(settings, claims.auth_subject)

    if not phone:
        user = (
            db.query(PorterchainUser)
            .filter(PorterchainUser.auth_subject == claims.auth_subject)
            .first()
        )
        if user and user.phone:
            phone = user.phone
        if not phone:
            customer = _customers.get_by_idp(db, claims.auth_subject)
            if customer:
                phone = customer.phone

    if not phone:
        phone = idp_phone

    return email, phone


_PHONE_CACHE_TTL_S = 300.0
_phone_cache: dict[str, tuple[float, str | None]] = {}


def _idp_phone_cached(settings: Settings, auth_subject: str) -> str | None:
    import time

    now = time.monotonic()
    hit = _phone_cache.get(auth_subject)
    if hit and hit[0] > now:
        return hit[1]
    phone = None
    try:
        idp_user, _kind = fetch_identity_user(settings, auth_subject)
        if idp_user:
            phone = IdentityDirectory.primary_phone(idp_user)
    except Exception:  # noqa: BLE001
        phone = None
    if len(_phone_cache) > 10_000:
        _phone_cache.clear()
    _phone_cache[auth_subject] = (now + _PHONE_CACHE_TTL_S, phone)
    return phone


def require_customer(
    db: Session,
    claims: IdentityClaims,
    settings: Settings,
) -> Customer:
    meta = getattr(claims, "public_metadata", None) or {}
    if meta.get("impersonation") and meta.get("user_type") == "customer":
        customer = db.get(Customer, str(meta.get("target_id") or ""))
        if not customer:
            raise HTTPException(status_code=404, detail="customer_not_found")
        return customer

    # Contact first: its Keycloak lookups run before this request's first query.
    email, phone = resolve_customer_contact(db, claims, settings)
    assert_portal_provisioned(db, claims, portal="customer", settings=settings)
    try:
        customer = _customers.get_or_create_from_idp(
            db,
            auth_subject=claims.auth_subject,
            email=email,
            phone=phone,
        )
    except ValueError as exc:
        detail = str(exc)
        if detail == "email_required":
            raise HTTPException(status_code=400, detail="email_required") from exc
        if detail == "email_identity_mismatch":
            raise HTTPException(status_code=403, detail="email_identity_mismatch") from exc
        # C-23: staff/driver Keycloak on customer portal must not 500.
        if detail.startswith("identity_conflict"):
            raise HTTPException(status_code=403, detail=detail) from exc
        raise

    from porterchain_api.auth.dependencies import assert_self_scope, resolve_principal_for_claims

    # Local AUTH_DEV_BYPASS synthetic subject has no SpiceDB tuples by design.
    if not is_dev_bypass_subject(claims.auth_subject):
        principal = resolve_principal_for_claims(db, claims)
        if not principal:
            raise HTTPException(status_code=403, detail="user_not_provisioned")
        assert_self_scope(principal, customer.id, db)
    return customer
