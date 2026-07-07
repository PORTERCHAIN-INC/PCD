"""Resolve customer context from Clerk JWT + Porterchain customers table."""

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from porterchain_api.auth.clerk import ClerkClaims, get_clerk_claims
from porterchain_api.auth.clerk_client import ClerkClient
from porterchain_api.auth.clerk_registry import fetch_clerk_user, is_clerk_secret_configured
from porterchain_api.auth.portal_guard import assert_clerk_id_exclusive, require_clerk_app_for_portal
from porterchain_api.booking_engine import CustomerService
from porterchain_api.config import Settings, get_settings
from porterchain_api.db import get_db
from porterchain_api.models import Customer
from porterchain_api.user_models import PorterchainUser

_customers = CustomerService()


@dataclass
class CustomerContext:
    customer: Customer
    email: str | None


def resolve_customer_contact(
    db: Session,
    claims: ClerkClaims,
    settings: Settings,
) -> tuple[str | None, str | None]:
    email = claims.email
    phone = claims.phone

    if not email:
        user = (
            db.query(PorterchainUser)
            .filter(PorterchainUser.clerk_user_id == claims.clerk_user_id)
            .first()
        )
        if user and user.email:
            email = user.email
        if user and user.phone and not phone:
            phone = user.phone

    if not email:
        customer = _customers.get_by_clerk(db, claims.clerk_user_id)
        if customer:
            email = customer.email
            phone = phone or customer.phone

    if not email and is_clerk_secret_configured(settings):
        try:
            clerk_user, _kind = fetch_clerk_user(settings, claims.clerk_user_id)
            if clerk_user:
                email = ClerkClient.primary_email(clerk_user)
                phone = phone or ClerkClient.primary_phone(clerk_user)
        except Exception:
            pass

    return email, phone


def require_customer(
    db: Session,
    claims: ClerkClaims,
    settings: Settings,
) -> Customer:
    require_clerk_app_for_portal(claims, settings, "customer")
    assert_clerk_id_exclusive(db, claims, portal="customer", settings=settings)
    email, phone = resolve_customer_contact(db, claims, settings)
    try:
        return _customers.get_or_create_from_clerk(
            db,
            clerk_user_id=claims.clerk_user_id,
            email=email,
            phone=phone,
        )
    except ValueError as exc:
        if str(exc) == "email_required":
            raise HTTPException(status_code=400, detail="email_required") from exc
        raise


async def get_customer_context(
    claims: Annotated[ClerkClaims, Depends(get_clerk_claims)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> CustomerContext:
    customer = require_customer(db, claims, settings)
    return CustomerContext(customer=customer, email=customer.email or claims.email)
