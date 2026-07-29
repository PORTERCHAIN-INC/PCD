"""Invitation workflows — Clerk invite + Porterchain provisioning (masterrule §15)."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy.orm import Session

from porterchain_api.admin_engine.rbac import AdminContext
from porterchain_api.admin_models import AdminAuditLog, AdminUser, Driver
from porterchain_api.auth.clerk_registry import clerk_client_for_kind
from porterchain_api.config import Settings
from porterchain_api.domain.admin_states import AdminRole
from porterchain_api.domain.merchant_states import MerchantRole
from porterchain_api.invitation_models import UserInvitation
from porterchain_api.merchant_engine.rbac import MerchantContext
from porterchain_api.merchant_models import Merchant, MerchantAuditLog, MerchantUser

if TYPE_CHECKING:
    from porterchain_api.admin_engine.rbac import AdminContext as _AdminContext

logger = logging.getLogger(__name__)

INVITABLE_ADMIN_ROLES = frozenset(
    {
        AdminRole.SUPER_ADMIN.value,
        AdminRole.ADMIN.value,
        AdminRole.DISPATCHER.value,
        AdminRole.SUPPORT.value,
        AdminRole.SUPPORT_LEAD.value,
        AdminRole.FINANCE.value,
        AdminRole.FLEET_MANAGER.value,
        AdminRole.SALES_MANAGER.value,
    }
)

OPEN_SIGNUP_USER_TYPES = frozenset({"customer"})


def pending_clerk_id(email: str) -> str:
    return f"pending:{email.lower().strip()}"


class InvitationService:
    """Send Clerk invitations and provision pending Porterchain records."""

    def invite_admin_staff(
        self,
        db: Session,
        ctx: AdminContext,
        settings: Settings,
        *,
        email: str,
        role: str,
        name: str | None = None,
    ) -> tuple[AdminUser, UserInvitation]:
        normalized = email.lower().strip()
        if role not in INVITABLE_ADMIN_ROLES:
            raise ValueError("invalid_admin_role")

        clerk = clerk_client_for_kind(settings, "admin")
        redirect = f"{settings.admin_portal_url.rstrip('/')}/sign-in"
        metadata = {
            "role": role,
            "porterchain_role": role,
            "user_type": "admin",
            "invitation_only": True,
        }
        clerk_result = clerk.invite_user(normalized, redirect_url=redirect, public_metadata=metadata)

        clerk_ref = clerk_result.clerk_user_id or pending_clerk_id(normalized)
        user = (
            db.query(AdminUser)
            .filter((AdminUser.email == normalized) | (AdminUser.clerk_user_id == clerk_ref))
            .first()
        )
        if user:
            user.email = normalized
            user.name = name or user.name
            user.role = role
            user.is_active = True
            if clerk_result.clerk_user_id:
                user.clerk_user_id = clerk_result.clerk_user_id
            elif not user.clerk_user_id.startswith("user_"):
                user.clerk_user_id = clerk_ref
        else:
            user = AdminUser(
                clerk_user_id=clerk_ref,
                email=normalized,
                name=name,
                role=role,
                is_active=True,
            )
            db.add(user)

        db.flush()
        invitation = self._record_invitation(
            db,
            email=normalized,
            user_type="admin",
            role=role,
            clerk_result=clerk_result,
            platform_user_id=user.id,
            invited_by=ctx.user.id,
            redirect_url=redirect,
            metadata={"name": name},
        )
        self._audit(db, ctx, "staff.invited", "admin_user", user.id, {"email": normalized, "role": role})
        db.commit()
        db.refresh(user)
        db.refresh(invitation)
        return user, invitation

    def invite_driver(
        self,
        db: Session,
        ctx: AdminContext | None,
        settings: Settings,
        driver: Driver,
    ) -> UserInvitation:
        normalized = driver.email.lower().strip()
        clerk = clerk_client_for_kind(settings, "driver")
        redirect = f"{settings.driver_portal_url.rstrip('/')}/login"
        metadata = {
            "role": "driver",
            "porterchain_role": "driver",
            "user_type": "driver",
            "driver_id": driver.id,
            "invitation_only": True,
        }
        clerk_result = clerk.invite_user(normalized, redirect_url=redirect, public_metadata=metadata)
        if clerk_result.clerk_user_id:
            driver.clerk_user_id = clerk_result.clerk_user_id

        invitation = self._record_invitation(
            db,
            email=normalized,
            user_type="driver",
            role="driver",
            clerk_result=clerk_result,
            platform_user_id=driver.id,
            invited_by=ctx.user.id if ctx and ctx.user else None,
            redirect_url=redirect,
            metadata={"full_name": driver.full_name},
        )
        if ctx:
            self._audit(db, ctx, "driver.invited", "driver", driver.id, {"email": normalized})
        db.commit()
        db.refresh(invitation)
        return invitation

    def invite_merchant_member(
        self,
        db: Session,
        ctx: MerchantContext,
        settings: Settings,
        *,
        email: str,
        role: str,
    ) -> MerchantUser:
        normalized = email.lower().strip()
        role_value = role if role in {r.value for r in MerchantRole} else MerchantRole.OPS.value

        clerk = clerk_client_for_kind(settings, "merchant")
        redirect = f"{settings.merchant_portal_url.rstrip('/')}/sign-in"
        metadata = {
            "role": role_value,
            "porterchain_role": role_value,
            "user_type": "merchant",
            "merchant_id": ctx.merchant.id,
            "invitation_only": True,
        }
        clerk_result = clerk.invite_user(normalized, redirect_url=redirect, public_metadata=metadata)

        clerk_ref = clerk_result.clerk_user_id or pending_clerk_id(normalized)
        existing = (
            db.query(MerchantUser)
            .filter(MerchantUser.merchant_id == ctx.merchant.id, MerchantUser.email == normalized)
            .first()
        )
        if existing:
            existing.role = role_value
            existing.is_active = True
            if clerk_result.clerk_user_id:
                existing.clerk_user_id = clerk_result.clerk_user_id
            elif not existing.clerk_user_id.startswith("user_"):
                existing.clerk_user_id = clerk_ref
            user = existing
        else:
            user = MerchantUser(
                merchant_id=ctx.merchant.id,
                clerk_user_id=clerk_ref,
                email=normalized,
                role=role_value,
            )
            db.add(user)

        db.flush()
        self._record_invitation(
            db,
            email=normalized,
            user_type="merchant",
            role=role_value,
            clerk_result=clerk_result,
            platform_user_id=user.id,
            merchant_id=ctx.merchant.id,
            invited_by=None,
            redirect_url=redirect,
            metadata={"invited_by_merchant_user": ctx.user.id},
        )
        db.add(
            MerchantAuditLog(
                merchant_id=ctx.merchant.id,
                actor_user_id=ctx.user.id,
                action="team.invited",
                resource_type="merchant_user",
                resource_id=user.id,
                payload={"email": normalized, "role": role_value},
            )
        )
        db.commit()
        db.refresh(user)
        return user

    def invite_merchant_owner(
        self,
        db: Session,
        ctx: AdminContext | None,
        settings: Settings,
        merchant: Merchant,
        *,
        email: str,
        role: str = "merchant_owner",
    ) -> tuple[MerchantUser, UserInvitation]:
        normalized = email.lower().strip()
        if not normalized:
            raise ValueError("merchant_owner_email_required")

        clerk = clerk_client_for_kind(settings, "merchant")
        redirect = f"{settings.merchant_portal_url.rstrip('/')}/sign-in"
        metadata = {
            "role": role,
            "porterchain_role": role,
            "user_type": "merchant",
            "merchant_id": merchant.id,
            "invitation_only": True,
        }
        clerk_result = clerk.invite_user(normalized, redirect_url=redirect, public_metadata=metadata)

        clerk_ref = clerk_result.clerk_user_id or pending_clerk_id(normalized)
        user = (
            db.query(MerchantUser)
            .filter(MerchantUser.merchant_id == merchant.id, MerchantUser.email == normalized)
            .first()
        )
        if user:
            user.role = role
            user.is_active = True
            if clerk_result.clerk_user_id:
                user.clerk_user_id = clerk_result.clerk_user_id
            elif not user.clerk_user_id.startswith("user_"):
                user.clerk_user_id = clerk_ref
        else:
            user = MerchantUser(
                merchant_id=merchant.id,
                clerk_user_id=clerk_ref,
                email=normalized,
                role=role,
            )
            db.add(user)

        db.flush()
        invitation = self._record_invitation(
            db,
            email=normalized,
            user_type="merchant",
            role=role,
            clerk_result=clerk_result,
            platform_user_id=user.id,
            merchant_id=merchant.id,
            invited_by=ctx.user.id if ctx and ctx.user else None,
            redirect_url=redirect,
            metadata={"merchant_id": merchant.id, "company_name": merchant.company_name},
        )
        if ctx:
            self._audit(
                db,
                ctx,
                "merchant.owner_invited",
                "merchant",
                merchant.id,
                {"email": normalized},
            )
        db.commit()
        db.refresh(user)
        db.refresh(invitation)
        return user, invitation

    def invite_merchant_member_admin(
        self,
        db: Session,
        ctx: AdminContext,
        settings: Settings,
        merchant: Merchant,
        *,
        email: str,
        role: str = "merchant_ops",
    ) -> tuple[MerchantUser, UserInvitation]:
        normalized = email.lower().strip()
        if not normalized:
            raise ValueError("merchant_member_email_required")

        role_value = role if role in {r.value for r in MerchantRole} else MerchantRole.OPS.value
        clerk = clerk_client_for_kind(settings, "merchant")
        redirect = f"{settings.merchant_portal_url.rstrip('/')}/sign-in"
        metadata = {
            "role": role_value,
            "porterchain_role": role_value,
            "user_type": "merchant",
            "merchant_id": merchant.id,
            "invitation_only": True,
        }
        clerk_result = clerk.invite_user(normalized, redirect_url=redirect, public_metadata=metadata)

        clerk_ref = clerk_result.clerk_user_id or pending_clerk_id(normalized)
        user = (
            db.query(MerchantUser)
            .filter(MerchantUser.merchant_id == merchant.id, MerchantUser.email == normalized)
            .first()
        )
        if user:
            user.role = role_value
            user.is_active = True
            if clerk_result.clerk_user_id:
                user.clerk_user_id = clerk_result.clerk_user_id
            elif not user.clerk_user_id.startswith("user_"):
                user.clerk_user_id = clerk_ref
        else:
            user = MerchantUser(
                merchant_id=merchant.id,
                clerk_user_id=clerk_ref,
                email=normalized,
                role=role_value,
            )
            db.add(user)

        db.flush()
        invitation = self._record_invitation(
            db,
            email=normalized,
            user_type="merchant",
            role=role_value,
            clerk_result=clerk_result,
            platform_user_id=user.id,
            merchant_id=merchant.id,
            invited_by=ctx.user.id,
            redirect_url=redirect,
            metadata={"merchant_id": merchant.id, "company_name": merchant.company_name},
        )
        self._audit(
            db,
            ctx,
            "merchant.member_invited",
            "merchant",
            merchant.id,
            {"email": normalized, "role": role_value},
        )
        db.commit()
        db.refresh(user)
        db.refresh(invitation)
        return user, invitation

    def mark_accepted(self, db: Session, *, email: str, clerk_user_id: str) -> None:
        normalized = email.lower().strip()
        now = datetime.now(UTC)
        rows = (
            db.query(UserInvitation)
            .filter(
                UserInvitation.email == normalized,
                UserInvitation.status == "pending",
            )
            .all()
        )
        for row in rows:
            row.status = "accepted"
            row.clerk_user_id = clerk_user_id
            row.accepted_at = now

    def _record_invitation(
        self,
        db: Session,
        *,
        email: str,
        user_type: str,
        role: str,
        clerk_result: ClerkInviteResult,
        platform_user_id: str,
        invited_by: str | None,
        redirect_url: str,
        merchant_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> UserInvitation:
        invitation = UserInvitation(
            id=str(uuid.uuid4()),
            email=email,
            user_type=user_type,
            role=role,
            status="accepted" if clerk_result.action == "found" else "pending",
            clerk_invitation_id=clerk_result.clerk_invitation_id,
            clerk_user_id=clerk_result.clerk_user_id,
            platform_user_id=platform_user_id,
            merchant_id=merchant_id,
            invited_by=invited_by,
            redirect_url=redirect_url,
            invitation_metadata={**(metadata or {}), "clerk_action": clerk_result.action},
            accepted_at=datetime.now(UTC) if clerk_result.action == "found" else None,
        )
        db.add(invitation)
        return invitation

    def _audit(
        self,
        db: Session,
        ctx: AdminContext,
        action: str,
        resource_type: str,
        resource_id: str,
        payload: dict[str, Any],
    ) -> None:
        db.add(
            AdminAuditLog(
                actor_user_id=ctx.user.id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                payload=payload,
            )
        )
