"""Create merchant rows owned by merchant_engine (CRM convert, admin, auth call this)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.domain.merchant_states import MerchantRole, MerchantStatus
from porterchain_api.merchant_models import Merchant, MerchantUser


def create_onboarding_merchant(
    db: Session,
    *,
    company_name: str | None,
    legal_name: str | None = None,
    email: str | None = None,
    phone: str | None = None,
    hst_number: str | None = None,
    business_number: str | None = None,
    billing_address: dict[str, Any] | None = None,
    preferred_vehicles: list[str] | None = None,
    profile: dict[str, Any] | None = None,
    status: str | None = None,
    payment_terms: str = "NET_30",
    clerk_org_id: str | None = None,
    activated_at: datetime | None = None,
    pricing_config: dict[str, Any] | None = None,
) -> Merchant:
    config = dict(pricing_config or {})
    raw_model = str(config.pop("pricing_model", "") or "distance").lower()
    pricing_model = raw_model if raw_model in ("fsa", "distance") else "distance"
    merchant = Merchant(
        status=status or MerchantStatus.ONBOARDING.value,
        company_name=company_name,
        legal_name=legal_name,
        email=email,
        phone=phone,
        hst_number=hst_number,
        business_number=business_number,
        billing_address=billing_address or {},
        preferred_vehicles=preferred_vehicles or [],
        profile=profile or {},
        payment_terms=payment_terms,
        clerk_org_id=clerk_org_id,
        activated_at=activated_at,
        pricing_config=config,
        pricing_model=pricing_model,
    )
    db.add(merchant)
    db.flush()
    return merchant


def ensure_dev_merchant_seat(db: Session, clerk_user_id: str) -> MerchantUser:
    from porterchain_api.merchant_engine.lookups import get_merchant_by_clerk_org, seats_for_clerk

    merchant = get_merchant_by_clerk_org(db, "dev_merchant_org")
    if not merchant:
        merchant = create_onboarding_merchant(
            db,
            company_name="Dev Merchant Co.",
            email="merchant@example.com",
            status=MerchantStatus.ACTIVE.value,
            clerk_org_id="dev_merchant_org",
            activated_at=datetime.now(UTC),
        )

    seats = seats_for_clerk(db, clerk_user_id)
    if seats:
        return seats[0]

    user = MerchantUser(
        merchant_id=merchant.id,
        clerk_user_id=clerk_user_id,
        email="admin@porterchain.com",
        role=MerchantRole.OWNER.value,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    from porterchain_api.auth.authz_sync import sync_authz_after_persona_mutation

    sync_authz_after_persona_mutation(db, clerk_user_id)
    return user
