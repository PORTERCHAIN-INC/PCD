"""Resolve authenticated user for notification endpoints (admin, driver, or merchant)."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from starlette.concurrency import run_in_threadpool
from sqlalchemy.orm import Session

from porterchain_api.admin_models import AdminUser, Driver
from porterchain_api.auth.dev import (
    DEV_LEGACY_SUBJECT,
    allow_auth_dev_bypass,
    is_merchant_dev_subject,
)
from porterchain_api.config import Settings, get_settings
from porterchain_api.db import get_db
from porterchain_api.domain.merchant_states import MerchantStatus
from porterchain_api.merchant_models import Merchant, MerchantUser
from porterchain_api.booking_models import Customer

_bearer = HTTPBearer(auto_error=False)
_PORTAL_OK = {MerchantStatus.ACTIVE.value, MerchantStatus.ONBOARDING.value}
MERCHANT_INBOX_FORBIDDEN = "You do not have access to that company inbox."
DRIVER_INBOX_FORBIDDEN = "You do not have access to that driver inbox."


class NotificationUser:
    def __init__(self, user_role: str, user_id: str) -> None:
        self.user_role = user_role
        self.user_id = user_id


def _admin_recipient_from_claims(db: Session, claims) -> NotificationUser | None:
    """Keycloak ``pc-admin`` token → admin inbox, matched by verified email."""
    from porterchain_api.auth.keycloak_staff import ADMIN_CLIENT_ID

    if getattr(claims, "authorized_party", None) != ADMIN_CLIENT_ID or not claims.email:
        return None
    user = (
        db.query(AdminUser)
        .filter(AdminUser.email == claims.email.lower(), AdminUser.is_active.is_(True))
        .first()
    )
    return NotificationUser("admin", user.id) if user else None


def _active_merchant_seats(db: Session, auth_subject: str) -> list[MerchantUser]:
    return (
        db.query(MerchantUser)
        .filter(MerchantUser.auth_subject == auth_subject, MerchantUser.is_active.is_(True))
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
    auth_subject: str,
    merchant_id: str | None,
) -> NotificationUser | None:
    """Inbox identity is the company (``merchants.id``), selected by ``X-Merchant-Id``.

    Keycloak Organization ids are not companies. Do not look up ``external_org_id``.
    """
    seats = _active_merchant_seats(db, auth_subject)
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

    if not allow_auth_dev_bypass(settings) or not is_merchant_dev_subject(auth_subject):
        return None
    merchant = db.query(Merchant).filter(Merchant.external_org_id == "dev_merchant_org").first()
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
    # All DB work runs in the threadpool; only the JWKS verify is awaited on the
    # loop (2026-10-14 freeze: sync DB/Keycloak I/O on the loop stalled every request).
    pre_user = await run_in_threadpool(
        _notification_pre_sync, db, token, settings
    )
    if pre_user:
        return pre_user

    try:
        from porterchain_api.auth.bearer import verify_access_token

        portal = (x_porterchain_portal or "").strip().lower() or None
        if not portal and (x_merchant_id or "").strip():
            portal = "merchant"
        claims = await verify_access_token(token, settings, portal=portal)
        found = await run_in_threadpool(
            _notification_post_sync, db, token, settings, claims, portal, x_merchant_id, x_driver_id
        )
        if found:
            return found
    except HTTPException:
        raise
    except Exception:  # noqa: BLE001
        pass

    raise HTTPException(status_code=401, detail="authentication_required")


def _notification_pre_sync(db: Session, token: str, settings: Settings) -> NotificationUser | None:
    try:
        from porterchain_api.auth.driver import _driver_id_from_token

        driver_id = _driver_id_from_token(token, settings)
        if db.query(Driver).filter(Driver.id == driver_id).first():
            return NotificationUser("driver", driver_id)
    except Exception:  # noqa: BLE001
        pass

    db.rollback()  # no open transaction while the loop awaits JWKS
    return None


def _notification_post_sync(
    db: Session,
    token: str,
    settings: Settings,
    claims,
    portal: str | None,
    x_merchant_id: str | None,
    x_driver_id: str | None,
) -> NotificationUser | None:
    staff = _admin_recipient_from_claims(db, claims)
    if staff:
        return staff

    # Prefer merchant/customer before admin — never auto-elevate merchants to admin
    # under AUTH_DEV_BYPASS (that stole inbox identity and masked membership bugs).
    # X-Merchant-Id is the company UUID, and the only company selector (BF).
    # Ignore Keycloak org_id on the JWT.
    requested_merchant = (x_merchant_id or "").strip() or None
    skip_merchant = portal in {"admin", "customer", "driver"}
    if not skip_merchant:
        merchant_user = _resolve_merchant_recipient(
            db,
            settings,
            claims.auth_subject,
            requested_merchant,
        )
        if merchant_user:
            return merchant_user
        if requested_merchant and _active_merchant_seats(db, claims.auth_subject):
            raise HTTPException(status_code=403, detail=MERCHANT_INBOX_FORBIDDEN)

    if portal == "driver":
        # Driver identity comes ONLY from the verified token's own Keycloak user.
        # ``X-Driver-Id`` is never trusted to pick a driver: a customer/merchant
        # token with a forged header must not reach another driver's inbox,
        # preferences or push devices (audit day 4, finding 1).
        requested_driver = (x_driver_id or "").strip() or None
        driver = db.query(Driver).filter(Driver.auth_subject == claims.auth_subject).first()
        if driver is None and allow_auth_dev_bypass(settings) and token == "dev":
            from porterchain_api.auth.dev import resolve_dev_bypass_driver

            driver = resolve_dev_bypass_driver(db)
        if driver is None:
            if requested_driver:
                # Signed-in, but not a driver, claiming a driver id → forbidden.
                raise HTTPException(status_code=403, detail=DRIVER_INBOX_FORBIDDEN)
            raise HTTPException(status_code=401, detail="authentication_required")
        if requested_driver and requested_driver != driver.id:
            raise HTTPException(status_code=403, detail=DRIVER_INBOX_FORBIDDEN)
        return NotificationUser("driver", driver.id)

    if portal not in {"admin", "driver"}:
        customer = db.query(Customer).filter(Customer.auth_subject == claims.auth_subject).first()
        if customer:
            return NotificationUser("customer", customer.id)
        if portal == "customer":
            raise HTTPException(status_code=401, detail="authentication_required")

    user = db.query(AdminUser).filter(AdminUser.auth_subject == claims.auth_subject).first()
    if not user and allow_auth_dev_bypass(settings) and claims.auth_subject == DEV_LEGACY_SUBJECT:
        from porterchain_api.auth.admin import _ensure_dev_admin

        user = _ensure_dev_admin(db, claims.auth_subject, None)
    if user and user.is_active:
        return NotificationUser("admin", user.id)
    return None


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
    ws_portal = (portal or "").strip().lower() or ("merchant" if merchant_id else None)
    pre_user = await run_in_threadpool(_ws_pre_sync, token, settings)
    if pre_user:
        return pre_user
    try:
        from porterchain_api.auth.bearer import verify_access_token

        claims = await verify_access_token(token, settings, portal=ws_portal)
        return await run_in_threadpool(
            _ws_post_sync, token, settings, claims, merchant_id, ws_portal
        )
    except Exception:  # noqa: BLE001
        return None


def _ws_pre_sync(token: str, settings: Settings) -> NotificationUser | None:
    from porterchain_api.db import SessionLocal, _safe_close

    db = SessionLocal()
    try:
        try:
            from porterchain_api.auth.driver import _driver_id_from_token

            driver_id = _driver_id_from_token(token, settings)
            if db.query(Driver).filter(Driver.id == driver_id).first():
                return NotificationUser("driver", driver_id)
        except Exception:  # noqa: BLE001
            pass

        return None
    finally:
        _safe_close(db)


def _ws_post_sync(
    token: str, settings: Settings, claims, merchant_id: str | None, ws_portal: str | None
) -> NotificationUser | None:
    from porterchain_api.db import SessionLocal, _safe_close

    db = SessionLocal()
    try:
        staff = _admin_recipient_from_claims(db, claims)
        if staff:
            return staff
        skip_merchant = ws_portal in {"admin", "customer", "driver"}
        merchant_user = None
        if not skip_merchant:
            merchant_user = _resolve_merchant_recipient(
                db, settings, claims.auth_subject, merchant_id
            )
        if merchant_user:
            return merchant_user
        if merchant_id and _active_merchant_seats(db, claims.auth_subject):
            return None
        if ws_portal == "driver":
            driver = db.query(Driver).filter(Driver.auth_subject == claims.auth_subject).first()
            if driver is None and allow_auth_dev_bypass(settings) and token == "dev":
                from porterchain_api.auth.dev import resolve_dev_bypass_driver

                driver = resolve_dev_bypass_driver(db)
            return NotificationUser("driver", driver.id) if driver else None
        if ws_portal not in {"admin", "driver"}:
            customer = db.query(Customer).filter(Customer.auth_subject == claims.auth_subject).first()
            if customer:
                return NotificationUser("customer", customer.id)
            if ws_portal == "customer":
                return None
        admin = db.query(AdminUser).filter(AdminUser.auth_subject == claims.auth_subject).first()
        if (
            not admin
            and allow_auth_dev_bypass(settings)
            and claims.auth_subject == DEV_LEGACY_SUBJECT
        ):
            from porterchain_api.auth.admin import _ensure_dev_admin

            admin = _ensure_dev_admin(db, claims.auth_subject, None)
        if admin and admin.is_active:
            return NotificationUser("admin", admin.id)
        return None
    finally:
        _safe_close(db)
