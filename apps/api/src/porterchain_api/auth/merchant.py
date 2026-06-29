"""Resolve merchant context from Clerk JWT."""

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from porterchain_api.auth.clerk import get_clerk_user_id
from porterchain_api.config import Settings, get_settings
from porterchain_api.db import get_db
from porterchain_api.domain.merchant_states import MerchantStatus
from porterchain_api.merchant_engine.rbac import MerchantContext, parse_merchant_role
from porterchain_api.merchant_models import Merchant, MerchantUser


@dataclass
class DevMerchantHeaders:
    org_id: str | None = None
    role: str | None = None


def get_merchant_context(
    clerk_user_id: Annotated[str, Depends(get_clerk_user_id)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    x_merchant_org_id: Annotated[str | None, Header()] = None,
    x_merchant_role: Annotated[str | None, Header()] = None,
) -> MerchantContext:
    org_id = x_merchant_org_id
    if (settings.clerk_dev_bypass or settings.app_env == "local") and not org_id:
        org_id = "dev_merchant_org"

    if not org_id:
        raise HTTPException(status_code=403, detail="merchant_org_required")

    merchant = db.query(Merchant).filter(Merchant.clerk_org_id == org_id).first()
    if not merchant:
        if (settings.clerk_dev_bypass or settings.app_env == "local") and org_id == "dev_merchant_org":
            merchant = _ensure_dev_merchant(db, org_id)
        else:
            raise HTTPException(status_code=404, detail="merchant_not_found")

    if merchant.status != MerchantStatus.ACTIVE.value:
        raise HTTPException(status_code=403, detail="merchant_not_active")

    user = db.query(MerchantUser).filter(MerchantUser.clerk_user_id == clerk_user_id).first()
    if not user:
        if settings.clerk_dev_bypass or settings.app_env == "local":
            user = _ensure_dev_user(db, merchant, clerk_user_id, x_merchant_role)
        else:
            raise HTTPException(status_code=403, detail="merchant_user_not_found")

    if user.merchant_id != merchant.id:
        raise HTTPException(status_code=403, detail="merchant_user_mismatch")

    role = parse_merchant_role(x_merchant_role or user.role)
    return MerchantContext(merchant=merchant, user=user, role=role)


def _ensure_dev_merchant(db: Session, org_id: str) -> Merchant:
    merchant = db.query(Merchant).filter(Merchant.clerk_org_id == org_id).first()
    if merchant:
        return merchant
    merchant = Merchant(
        clerk_org_id=org_id,
        status=MerchantStatus.ACTIVE.value,
        company_name="Dev Merchant Co.",
        email="merchant@example.com",
        payment_terms="NET_30",
        activated_at=__import__("datetime").datetime.now(__import__("datetime").UTC),
    )
    db.add(merchant)
    db.commit()
    db.refresh(merchant)
    return merchant


def _ensure_dev_user(
    db: Session, merchant: Merchant, clerk_user_id: str, role: str | None
) -> MerchantUser:
    user = db.query(MerchantUser).filter(MerchantUser.clerk_user_id == clerk_user_id).first()
    if user:
        return user
    user = MerchantUser(
        merchant_id=merchant.id,
        clerk_user_id=clerk_user_id,
        email="merchant@example.com",
        role=role or "merchant_owner",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
