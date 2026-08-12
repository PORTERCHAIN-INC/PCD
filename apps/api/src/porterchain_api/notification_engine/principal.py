"""Resolve authenticated user for notification endpoints (admin, driver, or merchant)."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from porterchain_api.admin_models import AdminUser, Driver
from porterchain_api.auth.dev import allow_auth_dev_bypass
from porterchain_api.auth.staff_session import STAFF_BEARER_PREFIX, get_session
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


def _resolve_staff_notification_user(db: Session, token: str) -> NotificationUser | None:
    """Map ``staff_sess_*`` Redis session → admin notification recipient (no Clerk)."""
    if not token.startswith(STAFF_BEARER_PREFIX):
        return None
    session = get_session(token.removeprefix(STAFF_BEARER_PREFIX).strip())
    if session is None:
        return None
    user = (
        db.query(AdminUser)
        .filter(AdminUser.id == session.admin_user_id, AdminUser.is_active.is_(True))
        .first()
    )
    if not user:
        return None
    return NotificationUser("admin", user.id)


def _resolve_merchant_recipient(
    db: Session,
    settings: Settings,
    clerk_user_id: str,
    org_id: str | None,
) -> NotificationUser | None:
    """Resolve merchant inbox recipient from MerchantUser (not Clerk Organizations).

    Porterchain merchants often have null ``clerk_org_id`` — membership is
    ``merchant_users.clerk_user_id`` → ``merchant_id``.
    """
    user = (
        db.query(MerchantUser)
        .filter(MerchantUser.clerk_user_id == clerk_user_id, MerchantUser.is_active.is_(True))
        .order_by(MerchantUser.created_at)
        .first()
    )
    if user:
        merchant = db.query(Merchant).filter(Merchant.id == user.merchant_id).first()
        if not merchant or merchant.status != MerchantStatus.ACTIVE.value:
            return None
        if org_id:
            # Accept merchant UUID or legacy Clerk org id when provided.
            if org_id not in {merchant.id, merchant.clerk_org_id or ""}:
                return None
        return NotificationUser("merchant", merchant.id)

    # Legacy / local seed: look up by Clerk org id (or dev_merchant_org under bypass).
    resolved_org = org_id
    if allow_auth_dev_bypass(settings) and not resolved_org:
        resolved_org = "dev_merchant_org"
    if not resolved_org:
        return None

    merchant = db.query(Merchant).filter(Merchant.clerk_org_id == resolved_org).first()
    if not merchant or merchant.status != MerchantStatus.ACTIVE.value:
        return None
    if not allow_auth_dev_bypass(settings):
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

    staff_user = _resolve_staff_notification_user(db, token)
    if staff_user:
        return staff_user

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

        # Prefer merchant/customer before admin — never auto-elevate merchants to admin
        # under CLERK_DEV_BYPASS (that stole inbox identity and masked membership bugs).
        merchant_user = _resolve_merchant_recipient(
            db,
            settings,
            claims.clerk_user_id,
            x_merchant_org_id or claims.org_id,
        )
        if merchant_user:
            return merchant_user

        customer = db.query(Customer).filter(Customer.clerk_user_id == claims.clerk_user_id).first()
        if customer:
            return NotificationUser("customer", customer.id)

        user = db.query(AdminUser).filter(AdminUser.clerk_user_id == claims.clerk_user_id).first()
        if not user and allow_auth_dev_bypass(settings):
            from porterchain_api.auth.admin import _ensure_dev_admin

            user = _ensure_dev_admin(db, claims.clerk_user_id, None)
        if user and user.is_active:
            return NotificationUser("admin", user.id)
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
        staff_user = _resolve_staff_notification_user(db, token)
        if staff_user:
            return staff_user

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
            merchant_user = _resolve_merchant_recipient(
                db, settings, claims.clerk_user_id, org_id or claims.org_id
            )
            if merchant_user:
                return merchant_user
            customer = db.query(Customer).filter(Customer.clerk_user_id == claims.clerk_user_id).first()
            if customer:
                return NotificationUser("customer", customer.id)
            admin = db.query(AdminUser).filter(AdminUser.clerk_user_id == claims.clerk_user_id).first()
            if not admin and allow_auth_dev_bypass(settings):
                from porterchain_api.auth.admin import _ensure_dev_admin

                admin = _ensure_dev_admin(db, claims.clerk_user_id, None)
            if admin and admin.is_active:
                return NotificationUser("admin", admin.id)
        except Exception:  # noqa: BLE001
            return None
        return None
    finally:
        db.close()
