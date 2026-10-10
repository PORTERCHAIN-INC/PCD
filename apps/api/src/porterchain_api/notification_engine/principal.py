"""Resolve authenticated user for notification endpoints (admin, driver, or merchant)."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from porterchain_api.admin_models import AdminUser, Driver
from porterchain_api.auth.dev import (
    DEV_LEGACY_SUBJECT,
    allow_auth_dev_bypass,
    is_merchant_dev_subject,
)
from porterchain_api.auth.staff_session import STAFF_BEARER_PREFIX, get_session
from porterchain_api.booking_models import Customer
from porterchain_api.config import Settings, get_settings
from porterchain_api.db import get_db
from porterchain_api.domain.merchant_states import MerchantStatus
from porterchain_api.merchant_models import Merchant, MerchantUser

_bearer = HTTPBearer(auto_error=False)
_PORTAL_OK = {MerchantStatus.ACTIVE.value, MerchantStatus.ONBOARDING.value}
MERCHANT_INBOX_FORBIDDEN = "You do not have access to that company inbox."


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


def _active_merchant_seats(db: Session, clerk_user_id: str) -> list[MerchantUser]:
    return (
        db.query(MerchantUser)
        .filter(MerchantUser.clerk_user_id == clerk_user_id, MerchantUser.is_active.is_(True))
        .order_by(MerchantUser.created_at.asc())
        .all()
    )


def _merchant_inbox_user(merchant: Merchant | None) -> NotificationUser | None:
    if not merchant or merchant.status not in _PORTAL_OK:
        return None
    return NotificationUser("merchant", merchant.id)


def _resolve_merchant_recipient(
    db: Session,
    settings: Settings,
    clerk_user_id: str,
    merchant_id: str | None,
) -> NotificationUser | None:
    """Inbox identity is the company (``merchants.id``), selected by ``X-Merchant-Id``.

    Clerk Organization ids are not companies. Do not look up ``clerk_org_id``.
    """
    seats = _active_merchant_seats(db, clerk_user_id)
    requested = (merchant_id or "").strip() or None
    if requested:
        seat = next((row for row in seats if row.merchant_id == requested), None)
        if not seat:
            return None
        merchant = db.query(Merchant).filter(Merchant.id == seat.merchant_id).first()
        return _merchant_inbox_user(merchant)

    for seat in seats:
        merchant = db.query(Merchant).filter(Merchant.id == seat.merchant_id).first()
        inbox = _merchant_inbox_user(merchant)
        if inbox:
            return inbox

    if not allow_auth_dev_bypass(settings) or not is_merchant_dev_subject(clerk_user_id):
        return None
    merchant = db.query(Merchant).filter(Merchant.clerk_org_id == "dev_merchant_org").first()
    return _merchant_inbox_user(merchant)


async def get_notification_user(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)] = None,
    x_merchant_id: Annotated[str | None, Header()] = None,
    x_porterchain_portal: Annotated[str | None, Header()] = None,
    x_driver_id: Annotated[str | None, Header()] = None,
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

        portal = (x_porterchain_portal or "").strip().lower() or None
        if not portal and (x_merchant_id or "").strip():
            portal = "merchant"
        claims = await verify_clerk_token(token, settings, portal=portal)

        # Prefer merchant/customer before admin — never auto-elevate merchants to admin
        # under CLERK_DEV_BYPASS (that stole inbox identity and masked membership bugs).
        # X-Merchant-Id is the company UUID, and the only company selector (BF).
        # Ignore Clerk org_id on the JWT.
        requested_merchant = (x_merchant_id or "").strip() or None
        skip_merchant = portal in {"admin", "customer", "driver"}
        if not skip_merchant:
            merchant_user = _resolve_merchant_recipient(
                db,
                settings,
                claims.clerk_user_id,
                requested_merchant,
            )
            if merchant_user:
                return merchant_user
            if requested_merchant and _active_merchant_seats(db, claims.clerk_user_id):
                raise HTTPException(status_code=403, detail=MERCHANT_INBOX_FORBIDDEN)

        if portal == "driver":
            requested_driver = (x_driver_id or "").strip() or None
            driver = None
            if requested_driver:
                driver = db.query(Driver).filter(Driver.id == requested_driver).first()
            if driver is None:
                driver = db.query(Driver).filter(Driver.clerk_user_id == claims.clerk_user_id).first()
            if driver is None and allow_auth_dev_bypass(settings) and token == "dev":
                from porterchain_api.auth.dev import resolve_dev_bypass_driver

                driver = resolve_dev_bypass_driver(db)
            if driver:
                return NotificationUser("driver", driver.id)
            raise HTTPException(status_code=401, detail="authentication_required")

        if portal not in {"admin", "driver"}:
            customer = db.query(Customer).filter(Customer.clerk_user_id == claims.clerk_user_id).first()
            if customer:
                return NotificationUser("customer", customer.id)
            if portal == "customer":
                raise HTTPException(status_code=401, detail="authentication_required")

        user = db.query(AdminUser).filter(AdminUser.clerk_user_id == claims.clerk_user_id).first()
        if not user and allow_auth_dev_bypass(settings) and claims.clerk_user_id == DEV_LEGACY_SUBJECT:
            from porterchain_api.auth.admin import _ensure_dev_admin

            user = _ensure_dev_admin(db, claims.clerk_user_id, None)
        if user and user.is_active:
            return NotificationUser("admin", user.id)
    except HTTPException:
        raise
    except Exception:  # noqa: BLE001
        pass

    raise HTTPException(status_code=401, detail="authentication_required")


async def resolve_notification_ws_user(
    token: str,
    *,
    merchant_id: str | None = None,
    portal: str | None = None,
) -> NotificationUser | None:
    """Resolve WebSocket subscriber from bearer token (admin, driver, or merchant).

    ``merchant_id`` is the websocket twin of ``X-Merchant-Id`` — browsers cannot
    set headers on a WebSocket, so it travels as a query param under the same
    name. There is no second selector (BF).
    """
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

            claims = await verify_clerk_token(
                token,
                settings,
                portal=(portal or "").strip().lower() or ("merchant" if merchant_id else None),
            )
            ws_portal = (portal or "").strip().lower() or ("merchant" if merchant_id else None)
            skip_merchant = ws_portal in {"admin", "customer", "driver"}
            merchant_user = None
            if not skip_merchant:
                merchant_user = _resolve_merchant_recipient(
                    db, settings, claims.clerk_user_id, merchant_id
                )
            if merchant_user:
                return merchant_user
            if merchant_id and _active_merchant_seats(db, claims.clerk_user_id):
                return None
            if ws_portal == "driver":
                driver = db.query(Driver).filter(Driver.clerk_user_id == claims.clerk_user_id).first()
                if driver is None and allow_auth_dev_bypass(settings) and token == "dev":
                    from porterchain_api.auth.dev import resolve_dev_bypass_driver

                    driver = resolve_dev_bypass_driver(db)
                return NotificationUser("driver", driver.id) if driver else None
            if ws_portal not in {"admin", "driver"}:
                customer = db.query(Customer).filter(Customer.clerk_user_id == claims.clerk_user_id).first()
                if customer:
                    return NotificationUser("customer", customer.id)
                if ws_portal == "customer":
                    return None
            admin = db.query(AdminUser).filter(AdminUser.clerk_user_id == claims.clerk_user_id).first()
            if (
                not admin
                and allow_auth_dev_bypass(settings)
                and claims.clerk_user_id == DEV_LEGACY_SUBJECT
            ):
                from porterchain_api.auth.admin import _ensure_dev_admin

                admin = _ensure_dev_admin(db, claims.clerk_user_id, None)
            if admin and admin.is_active:
                return NotificationUser("admin", admin.id)
        except Exception:  # noqa: BLE001
            return None
        return None
    finally:
        db.close()
