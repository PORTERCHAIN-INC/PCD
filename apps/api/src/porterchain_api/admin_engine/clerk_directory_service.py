"""Settings user directory — Clerk live sync + provisioned Porterchain records."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.admin_engine.rbac import AdminContext
from porterchain_api.admin_engine.audit import log_admin_audit
from porterchain_api.admin_models import AdminUser, Driver
from porterchain_api.auth.clerk_client import ClerkClient
from porterchain_api.auth.clerk_registry import clerk_client_for_kind, is_clerk_secret_configured
from porterchain_api.auth.clerk_registry import ClerkAppKind
from porterchain_api.auth.portal_guard import is_legacy_shared_clerk_app
from porterchain_api.auth.invitation_service import InvitationService
from porterchain_api.booking_engine import CustomerService
from porterchain_api.config import Settings
from porterchain_api.domain.admin_states import DriverStatus
from porterchain_api.merchant_models import Merchant, MerchantUser

logger = logging.getLogger(__name__)

_CUSTOMERS = CustomerService()


def clerk_kind_for_user_type(user_type: str) -> ClerkAppKind:
    return "admin" if user_type == "staff" else user_type  # type: ignore[return-value]


def fetch_clerk_snapshots(
    settings: Settings,
    user_type: str,
    *,
    limit: int = 500,
    query: str | None = None,
) -> dict[str, Any]:
    """Email → ClerkUserSnapshot for the tab's Clerk application."""
    from porterchain_api.auth.clerk_client import ClerkUserSnapshot

    kind = clerk_kind_for_user_type(user_type)
    if not is_clerk_secret_configured(settings, kind):
        return {}
    client = clerk_client_for_kind(settings, kind)
    users, _total = client.list_users(limit=limit, query=query)
    out: dict[str, ClerkUserSnapshot] = {}
    expected_type = "admin" if user_type == "staff" else user_type
    legacy_shared = is_legacy_shared_clerk_app(settings)
    for raw in users:
        snap = ClerkClient.snapshot(raw)
        if not snap:
            continue
        if legacy_shared:
            meta_type = (snap.public_metadata or {}).get("user_type")
            if meta_type and meta_type != expected_type and not (meta_type == "admin" and expected_type == "staff"):
                continue
        out[snap.email] = snap
    return out


class ClerkDirectoryService:
    """Create / update / delete users via Clerk + Porterchain provisioning."""

    def create_user(
        self,
        db: Session,
        ctx: AdminContext,
        settings: Settings,
        user_type: str,
        *,
        email: str,
        name: str | None = None,
        role: str | None = None,
        password: str | None = None,
        send_invite: bool = True,
        merchant_id: str | None = None,
    ) -> dict[str, Any]:
        normalized = email.lower().strip()
        if not normalized:
            raise ValueError("email_required")
        kind = clerk_kind_for_user_type(user_type)
        if not is_clerk_secret_configured(settings, kind):
            raise ValueError("clerk_not_configured")

        first_name = None
        last_name = None
        if name and name.strip():
            parts = name.strip().split(None, 1)
            first_name = parts[0]
            last_name = parts[1] if len(parts) > 1 else None

        client = clerk_client_for_kind(settings, kind)
        clerk_user: dict[str, Any] | None = None
        clerk_action = "created"

        if password:
            clerk_user = client.create_user(
                normalized,
                password=password,
                first_name=first_name,
                last_name=last_name,
                public_metadata={"user_type": user_type},
            )
            clerk_action = "created_with_password"
        elif send_invite:
            inv = InvitationService()
            if user_type == "staff":
                if not role:
                    raise ValueError("role_required")
                user, _inv = inv.invite_admin_staff(
                    db, ctx, settings, email=normalized, role=role, name=name
                )
                return {"platform_user_id": user.id, "clerk_action": "invited", "email": normalized}
            if user_type == "driver":
                driver = Driver(
                    full_name=name or normalized.split("@")[0],
                    email=normalized,
                    status=DriverStatus.PENDING.value,
                )
                db.add(driver)
                db.flush()
                inv.invite_driver(db, ctx, settings, driver)
                db.commit()
                return {"platform_user_id": driver.id, "clerk_action": "invited", "email": normalized}
            if user_type == "merchant":
                if not merchant_id:
                    raise ValueError("merchant_id_required")
                merchant = db.query(Merchant).filter(Merchant.id == merchant_id).first()
                if not merchant:
                    raise ValueError("merchant_not_found")
                m_role = role or "merchant_ops"
                metadata = {
                    "user_type": "merchant",
                    "merchant_id": merchant_id,
                    "role": m_role,
                }
                redirect = f"{settings.merchant_portal_url.rstrip('/')}/sign-in"
                clerk_result = client.invite_user(
                    normalized, redirect_url=redirect, public_metadata=metadata
                )
                clerk_ref = clerk_result.clerk_user_id or f"pending:{normalized}"
                mu = (
                    db.query(MerchantUser)
                    .filter(MerchantUser.merchant_id == merchant_id, MerchantUser.email == normalized)
                    .first()
                )
                if not mu:
                    mu = MerchantUser(
                        merchant_id=merchant_id,
                        clerk_user_id=clerk_ref,
                        email=normalized,
                        role=m_role,
                    )
                    db.add(mu)
                else:
                    mu.clerk_user_id = clerk_ref
                    mu.is_active = True
                    mu.role = m_role
                db.flush()
                log_admin_audit(
                    db,
                    ctx,
                    action="settings.user.invited",
                    resource_type="merchant",
                    resource_id=mu.id,
                    payload={"email": normalized, "clerk_action": clerk_result.action},
                )
                db.commit()
                return {
                    "platform_user_id": mu.id,
                    "clerk_user_id": clerk_ref if clerk_ref.startswith("user_") else None,
                    "clerk_action": clerk_result.action,
                    "email": normalized,
                }
            # customer — self-signup; create Clerk + customer row
            clerk_user = client.create_user(
                normalized,
                first_name=first_name,
                last_name=last_name,
                skip_password_requirement=True,
                public_metadata={"user_type": "customer"},
            )
            clerk_action = "created"
        else:
            clerk_user = client.create_user(
                normalized,
                first_name=first_name,
                last_name=last_name,
                skip_password_requirement=True,
                public_metadata={"user_type": user_type},
            )

        if not clerk_user:
            raise ValueError("clerk_create_failed")

        clerk_id = str(clerk_user["id"])
        platform_id = self._provision_from_clerk(
            db,
            ctx,
            user_type,
            email=normalized,
            clerk_user_id=clerk_id,
            name=name,
            role=role,
            merchant_id=merchant_id,
        )
        log_admin_audit(
            db,
            ctx,
            action="settings.user.created",
            resource_type=user_type,
            resource_id=platform_id or clerk_id,
            payload={"email": normalized, "clerk_action": clerk_action},
        )
        db.commit()
        return {
            "platform_user_id": platform_id,
            "clerk_user_id": clerk_id,
            "clerk_action": clerk_action,
            "email": normalized,
        }

    def update_clerk_user(
        self,
        db: Session,
        ctx: AdminContext,
        settings: Settings,
        user_type: str,
        clerk_user_id: str,
        *,
        name: str | None = None,
        password: str | None = None,
        banned: bool | None = None,
    ) -> dict[str, Any]:
        kind = clerk_kind_for_user_type(user_type)
        client = clerk_client_for_kind(settings, kind)
        first_name = None
        last_name = None
        if name and name.strip():
            parts = name.strip().split(None, 1)
            first_name = parts[0]
            last_name = parts[1] if len(parts) > 1 else None
        if first_name is not None or password:
            client.update_user(
                clerk_user_id,
                first_name=first_name,
                last_name=last_name,
                password=password,
            )
        if banned is True:
            client.ban_user(clerk_user_id)
        elif banned is False:
            client.unban_user(clerk_user_id)
        log_admin_audit(
            db,
            ctx,
            action="settings.user.updated",
            resource_type=user_type,
            resource_id=clerk_user_id,
            payload={"banned": banned, "password_reset": bool(password)},
        )
        db.commit()
        snap = ClerkClient.snapshot(client.get_user(clerk_user_id) or {})
        return {"clerk_user_id": clerk_user_id, "clerk_status": snap.clerk_status if snap else None}

    def delete_clerk_user(
        self,
        db: Session,
        ctx: AdminContext,
        settings: Settings,
        user_type: str,
        *,
        clerk_user_id: str | None = None,
        platform_user_id: str | None = None,
    ) -> None:
        kind = clerk_kind_for_user_type(user_type)
        resolved_clerk_id = clerk_user_id or self._clerk_id_for_platform(db, user_type, platform_user_id)
        if resolved_clerk_id and is_clerk_secret_configured(settings, kind):
            clerk_client_for_kind(settings, kind).delete_user(resolved_clerk_id)
        if platform_user_id:
            self._deactivate_platform_user(db, user_type, platform_user_id)
        log_admin_audit(
            db,
            ctx,
            action="settings.user.deleted",
            resource_type=user_type,
            resource_id=platform_user_id or resolved_clerk_id or "",
            payload={"clerk_user_id": resolved_clerk_id},
        )
        db.commit()

    def _clerk_id_for_platform(self, db: Session, user_type: str, platform_user_id: str | None) -> str | None:
        if not platform_user_id:
            return None
        if user_type == "staff":
            u = db.query(AdminUser).filter(AdminUser.id == platform_user_id).first()
            return u.clerk_user_id if u and _clerk_linked(u.clerk_user_id) else None
        if user_type == "driver":
            d = db.query(Driver).filter(Driver.id == platform_user_id).first()
            return d.clerk_user_id if d and _clerk_linked(d.clerk_user_id) else None
        if user_type == "merchant":
            mu = db.query(MerchantUser).filter(MerchantUser.id == platform_user_id).first()
            return mu.clerk_user_id if mu and _clerk_linked(mu.clerk_user_id) else None
        if user_type == "customer":
            from porterchain_api.models import Customer

            c = db.query(Customer).filter(Customer.id == platform_user_id).first()
            return c.clerk_user_id if c and _clerk_linked(c.clerk_user_id) else None
        return None

    def _deactivate_platform_user(self, db: Session, user_type: str, platform_user_id: str) -> None:
        if user_type == "staff":
            u = db.query(AdminUser).filter(AdminUser.id == platform_user_id).first()
            if u:
                u.is_active = False
        elif user_type == "driver":
            d = db.query(Driver).filter(Driver.id == platform_user_id).first()
            if d:
                d.status = DriverStatus.SUSPENDED.value
        elif user_type == "merchant":
            mu = db.query(MerchantUser).filter(MerchantUser.id == platform_user_id).first()
            if mu:
                mu.is_active = False

    def _provision_from_clerk(
        self,
        db: Session,
        ctx: AdminContext,
        user_type: str,
        *,
        email: str,
        clerk_user_id: str,
        name: str | None,
        role: str | None,
        merchant_id: str | None,
    ) -> str | None:
        if user_type == "staff":
            existing = db.query(AdminUser).filter(AdminUser.email == email).first()
            if existing:
                existing.clerk_user_id = clerk_user_id
                existing.is_active = True
                if role:
                    existing.role = role
                if name:
                    existing.name = name
                return existing.id
            user = AdminUser(
                id=str(uuid.uuid4()),
                clerk_user_id=clerk_user_id,
                email=email,
                name=name,
                role=role or "read_only",
            )
            db.add(user)
            db.flush()
            return user.id
        if user_type == "driver":
            existing = db.query(Driver).filter(Driver.email == email).first()
            if existing:
                existing.clerk_user_id = clerk_user_id
                return existing.id
            driver = Driver(
                full_name=name or email.split("@")[0],
                email=email,
                clerk_user_id=clerk_user_id,
                status=DriverStatus.PENDING.value,
            )
            db.add(driver)
            db.flush()
            return driver.id
        if user_type == "customer":
            customer = _CUSTOMERS.get_or_create_from_clerk(
                db, clerk_user_id=clerk_user_id, email=email, phone=None
            )
            return customer.id
        if user_type == "merchant" and merchant_id:
            mu = (
                db.query(MerchantUser)
                .filter(MerchantUser.merchant_id == merchant_id, MerchantUser.email == email)
                .first()
            )
            if mu:
                mu.clerk_user_id = clerk_user_id
                mu.is_active = True
                return mu.id
        return None


def _clerk_linked(clerk_user_id: str | None) -> bool:
    if not clerk_user_id:
        return False
    return not clerk_user_id.startswith("pending")
