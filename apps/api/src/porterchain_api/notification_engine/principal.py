"""Resolve authenticated user for notification endpoints (admin, driver, or merchant)."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from porterchain_api.admin_models import AdminUser, Driver
from porterchain_api.auth.dev import allow_auth_dev_bypass
from porterchain_api.config import Settings, get_settings
from porterchain_api.db import get_db
from porterchain_api.domain.merchant_states import MerchantStatus
from porterchain_api.merchant_models import Merchant, MerchantUser
from porterchain_api.models import Customer

_bearer = HTTPBearer(auto_error=False)


class NotificationUser:
    def __init__(self, user_role: str, user_id: str) -> None:
        self.user_role = user_role
        self.user_id = user_id


def _resolve_merchant_recipient(
    db: Session,
    settings: Settings,
    clerk_user_id: str,
    org_id: str | None,
) -> NotificationUser | None:
    resolved_org = org_id
    if allow_auth_dev_bypass(settings) and not resolved_org:
        resolved_org = "dev_merchant_org"
    if not resolved_org:
        return None

    merchant = db.query(Merchant).filter(Merchant.clerk_org_id == resolved_org).first()
    if not merchant or merchant.status != MerchantStatus.ACTIVE.value:
        return None

    user = db.query(MerchantUser).filter(MerchantUser.clerk_user_id == clerk_user_id).first()
    if not user and not allow_auth_dev_bypass(settings):
        return None
    if user and user.merchant_id != merchant.id:
        return None

    return NotificationUser("merchant", merchant.id)


async def get_notification_user(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)] = None,
    x_merchant_org_id: Annotated[str | None, Header()] = None,
) -> NotificationUser:
    if not credentials or not credentials.credentials:
        raise HTTPException(status_code=401, detail="authentication_required")

    token = credentials.credentials

    try:
        from porterchain_api.auth.driver import _driver_id_from_token

        driver_id = _driver_id_from_token(token, settings)
        if db.query(Driver).filter(Driver.id == driver_id).first():
            return NotificationUser("driver", driver_id)
    except Exception:  # noqa: BLE001
        pass

    try:
        from porterchain_api.auth.clerk import verify_clerk_token

        claims = await verify_clerk_token(token, settings)
        user = db.query(AdminUser).filter(AdminUser.clerk_user_id == claims.clerk_user_id).first()
        if user and user.is_active:
            return NotificationUser("admin", user.id)

        merchant_user = _resolve_merchant_recipient(db, settings, claims.clerk_user_id, x_merchant_org_id)
        if merchant_user:
            return merchant_user

        customer = db.query(Customer).filter(Customer.clerk_user_id == claims.clerk_user_id).first()
        if customer:
            return NotificationUser("customer", customer.id)
    except Exception:  # noqa: BLE001
        pass

    raise HTTPException(status_code=401, detail="authentication_required")


async def resolve_notification_ws_user(
    token: str,
    *,
    org_id: str | None = None,
) -> NotificationUser | None:
    """Resolve WebSocket subscriber from bearer token (admin, driver, or merchant)."""
    from porterchain_api.config import get_settings
    from porterchain_api.db import SessionLocal

    if not token:
        return None

    settings = get_settings()
    db = SessionLocal()
    try:
        try:
            from porterchain_api.auth.driver import _driver_id_from_token

            driver_id = _driver_id_from_token(token, settings)
            if db.query(Driver).filter(Driver.id == driver_id).first():
                return NotificationUser("driver", driver_id)
        except Exception:  # noqa: BLE001
            pass

        try:
            from porterchain_api.auth.clerk import verify_clerk_token

            claims = await verify_clerk_token(token, settings)
            admin = db.query(AdminUser).filter(AdminUser.clerk_user_id == claims.clerk_user_id).first()
            if admin and admin.is_active:
                return NotificationUser("admin", admin.id)
            merchant_user = _resolve_merchant_recipient(db, settings, claims.clerk_user_id, org_id)
            if merchant_user:
                return merchant_user
            customer = db.query(Customer).filter(Customer.clerk_user_id == claims.clerk_user_id).first()
            if customer:
                return NotificationUser("customer", customer.id)
        except Exception:  # noqa: BLE001
            return None
    finally:
        db.close()
