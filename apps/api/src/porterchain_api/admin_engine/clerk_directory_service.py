"""Settings user directory — Clerk live sync for driver/merchant/customer.

Staff provisioning and directory listing are Staff IdP only
(``StaffIdpService`` / ``AdminSettingsService.list_platform_users``).
This module must not treat staff as a Clerk application kind.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.admin_engine.audit import log_admin_audit
from porterchain_api.admin_engine.clerk_directory_local import (
    create_local_driver,
    invite_directory_user,
)
from porterchain_api.admin_engine.rbac import AdminContext
from porterchain_api.admin_models import AdminUser, Driver
from porterchain_api.auth.clerk_client import ClerkClient
from porterchain_api.auth.clerk_registry import (
    ClerkAppKind,
    clerk_client_for_kind,
    is_clerk_secret_configured,
)
from porterchain_api.auth.invitation_service import InvitationService
from porterchain_api.auth.portal_guard import is_legacy_shared_clerk_app
from porterchain_api.config import Settings
from porterchain_api.domain.admin_states import DriverStatus
from porterchain_api.merchant_engine.lookups import (
    get_merchant,
    get_merchant_user,
    get_merchant_user_by_email,
)
from porterchain_api.merchant_engine.team_service import (
    bind_seat_clerk,
    deactivate_seat,
)

logger = logging.getLogger(__name__)


_PLATFORM_USER_TYPES = frozenset({"staff", "driver", "customer", "merchant"})
_CLERK_DIRECTORY_TYPES = frozenset({"driver", "customer", "merchant"})


def require_platform_user_type(user_type: str) -> str:
    if user_type not in _PLATFORM_USER_TYPES:
        raise ValueError("invalid_user_type")
    return user_type


def require_clerk_directory_type(user_type: str) -> str:
    """Staff uses Staff IdP — never a Clerk directory application."""
    if user_type == "staff":
        raise ValueError("staff_uses_staff_idp_not_clerk")
    if user_type not in _CLERK_DIRECTORY_TYPES:
        raise ValueError("invalid_user_type")
    return user_type


def clerk_kind_for_user_type(user_type: str) -> ClerkAppKind:
    require_clerk_directory_type(user_type)
    return user_type  # type: ignore[return-value]


def fetch_clerk_snapshots(
    settings: Settings,
    user_type: str,
    *,
    limit: int = 500,
    query: str | None = None,
) -> dict[str, Any]:
    """Email → ClerkUserSnapshot for the tab's Clerk application."""
    from porterchain_api.auth.clerk_client import ClerkUserSnapshot

    require_clerk_directory_type(user_type)
    kind = clerk_kind_for_user_type(user_type)
    if not is_clerk_secret_configured(settings, kind):
        return {}
    client = clerk_client_for_kind(settings, kind)
    users, _total = client.list_users(limit=limit, query=query)
    out: dict[str, ClerkUserSnapshot] = {}
    expected_type = user_type
    legacy_shared = is_legacy_shared_clerk_app(settings)
    for raw in users:
        snap = ClerkClient.snapshot(raw)
        if not snap:
            continue
        if legacy_shared:
            meta_type = (snap.public_metadata or {}).get("user_type")
            if meta_type and meta_type != expected_type:
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
        require_platform_user_type(user_type)
        normalized = email.lower().strip()
        if not normalized:
            raise ValueError("email_required")
        # Retail / staff guards: never set passwords for merchant/customer; staff use IdP enroll.
        if user_type == "staff":
            raise ValueError("staff_use_enroll_endpoint")
        if user_type in ("merchant", "customer") and password:
            raise ValueError("password_create_forbidden_for_retail")
        # Customers: mint local row (+ optional Platform invite) — same path as Customers page.
        if user_type == "customer":
            from porterchain_api.admin_engine.customer_admin_service import (
                CustomerAdminService,
            )

            row = CustomerAdminService().create_customer(
                db,
                ctx,
                settings,
                email=normalized,
                full_name=name,
                send_invite=send_invite,
            )
            return {
                "platform_user_id": row["id"],
                "clerk_user_id": row.get("clerk_user_id"),
                "clerk_action": row.get("clerk_action") or "created",
                "email": normalized,
            }

        # Merchant seats are always reserved locally — never Clerk-invite from Settings (M-16).
        # Must run before clerk_not_configured so Super Admin can add seats without Clerk.
        if user_type == "merchant":
            if not merchant_id:
                raise ValueError("merchant_id_required")
            merchant = get_merchant(db, merchant_id)
            if not merchant:
                raise ValueError("merchant_not_found")
            from porterchain_api.merchant_engine.team_service import (
                ensure_merchant_seat,
            )

            m_role = role or "merchant_ops"
            mu = ensure_merchant_seat(
                db,
                merchant_id=merchant_id,
                email=normalized,
                role=m_role,
                actor_user_id=ctx.user.id,
                audit_action="merchant.member_seat_added",
                commit=False,
            )
            log_admin_audit(
                db,
                ctx,
                action="settings.user.seat_added",
                resource_type="merchant",
                resource_id=mu.id,
                payload={"email": normalized, "clerk_invite": False, "role": m_role},
            )
            db.commit()
            db.refresh(mu)
            return {
                "platform_user_id": mu.id,
                "clerk_user_id": mu.clerk_user_id if str(mu.clerk_user_id).startswith("user_") else None,
                "clerk_action": "seat_reserved",
                "email": normalized,
            }

        # Driver: local PENDING row when Super Admin skips Clerk, or when Clerk is down.
        if user_type == "driver" and not password and not send_invite:
            return create_local_driver(db, ctx, email=normalized, name=name)
        kind = clerk_kind_for_user_type(user_type)
        if not is_clerk_secret_configured(settings, kind):
            if user_type == "driver":
                return create_local_driver(db, ctx, email=normalized, name=name)
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
            raise ValueError(f"invite_unsupported_for_{user_type}")
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

    def invite_user(
        self,
        db: Session,
        ctx: AdminContext,
        settings: Settings,
        user_type: str,
        *,
        platform_user_id: str,
    ) -> dict[str, Any]:
        return invite_directory_user(
            db, ctx, settings, user_type, platform_user_id=platform_user_id
        )

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
        require_platform_user_type(user_type)
        if user_type == "staff":
            raise ValueError("staff_manage_via_staff_idp")
        if user_type in ("merchant", "customer"):
            raise ValueError("clerk_manage_forbidden_for_retail")
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
        require_platform_user_type(user_type)
        if not clerk_user_id and not platform_user_id:
            raise ValueError("clerk_user_id_or_platform_user_id_required")
        if user_type == "customer":
            # C-0: never wipe Platform Clerk retail identities from Admin Settings.
            # C-19: DSR hold also blocks any future tombstone path.
            if platform_user_id:
                from porterchain_api.booking_models import Customer

                customer = db.query(Customer).filter(Customer.id == platform_user_id).first()
                if customer and (customer.privacy_status or "").lower() == "deletion_hold":
                    raise ValueError("customer_privacy_deletion_hold")
            raise ValueError("customer_delete_forbidden")
        if user_type == "staff":
            if not platform_user_id:
                raise ValueError("staff_delete_requires_platform_user_id")
            self._deactivate_platform_user(db, user_type, platform_user_id)
            from porterchain_api.auth.authz_sync import (
                sync_authz_after_persona_mutation,
            )

            u = db.query(AdminUser).filter(AdminUser.id == platform_user_id).first()
            if u and u.clerk_user_id:
                sync_authz_after_persona_mutation(db, u.clerk_user_id)
            log_admin_audit(
                db,
                ctx,
                action="settings.user.deleted",
                resource_type=user_type,
                resource_id=platform_user_id,
                payload={"staff_idp": True},
            )
            db.commit()
            return
        kind = clerk_kind_for_user_type(user_type)
        resolved_clerk_id = clerk_user_id or self._clerk_id_for_platform(db, user_type, platform_user_id)
        if resolved_clerk_id and is_clerk_secret_configured(settings, kind):
            clerk_client_for_kind(settings, kind).delete_user(resolved_clerk_id)
        if platform_user_id:
            self._deactivate_platform_user(db, user_type, platform_user_id)
            clerk_for_sync = resolved_clerk_id or self._clerk_id_for_platform(
                db, user_type, platform_user_id
            )
            if clerk_for_sync:
                from porterchain_api.auth.authz_sync import (
                    sync_authz_after_persona_mutation,
                )

                sync_authz_after_persona_mutation(db, clerk_for_sync)
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
            # Staff IdP subject is not a Clerk user id — never send to Clerk APIs.
            return None
        if user_type == "driver":
            d = db.query(Driver).filter(Driver.id == platform_user_id).first()
            return d.clerk_user_id if d and _clerk_linked(d.clerk_user_id) else None
        if user_type == "merchant":
            mu = get_merchant_user(db, platform_user_id)
            return mu.clerk_user_id if mu and _clerk_linked(mu.clerk_user_id) else None
        if user_type == "customer":
            from porterchain_api.booking_models import Customer

            c = db.query(Customer).filter(Customer.id == platform_user_id).first()
            return c.clerk_user_id if c and _clerk_linked(c.clerk_user_id) else None
        return None

    def _deactivate_platform_user(self, db: Session, user_type: str, platform_user_id: str) -> None:
        if user_type == "staff":
            u = db.query(AdminUser).filter(AdminUser.id == platform_user_id).first()
            if u:
                u.is_active = False
                from porterchain_api.auth.staff_session import revoke_all_for_user

                revoke_all_for_user(u.id)
        elif user_type == "driver":
            d = db.query(Driver).filter(Driver.id == platform_user_id).first()
            if d:
                d.status = DriverStatus.SUSPENDED.value
        elif user_type == "merchant":
            mu = get_merchant_user(db, platform_user_id)
            if mu:
                deactivate_seat(db, mu.id)

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
            raise ValueError("staff_use_enroll_endpoint")
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
            from porterchain_api.admin_engine.merchant_lifecycle import (
                ensure_retail_customer,
            )

            customer = ensure_retail_customer(
                db, email=email, phone=None, full_name=name
            )
            if customer.clerk_user_id and not str(customer.clerk_user_id).startswith("pending"):
                if customer.clerk_user_id != clerk_user_id:
                    raise ValueError("customer_email_exists")
            customer.clerk_user_id = clerk_user_id
            if name and name.strip() and not customer.full_name:
                customer.full_name = name.strip()[:255]
            from porterchain_api.auth.authz_sync import (
                sync_authz_after_persona_mutation,
            )

            sync_authz_after_persona_mutation(db, clerk_user_id)
            return customer.id
        if user_type == "merchant" and merchant_id:
            mu = get_merchant_user_by_email(db, email, merchant_id=merchant_id)
            if mu:
                bind_seat_clerk(db, mu.id, clerk_user_id, activate=True)
                return mu.id
        return None


def _clerk_linked(clerk_user_id: str | None) -> bool:
    if not clerk_user_id:
        return False
    if clerk_user_id.startswith("pending") or clerk_user_id.startswith("staff:"):
        return False
    return True
