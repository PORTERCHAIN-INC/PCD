"""Invitation workflows — Driver Clerk invites only.

Staff use staff IdP enroll (``StaffIdpService``). Merchant seats are email-bind via
``merchant_engine.team_service.ensure_merchant_seat``. Customer signup is open on
PorterChain Platform.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.admin_engine.rbac import AdminContext
from porterchain_api.admin_models import AdminAuditLog, Driver
from porterchain_api.auth.clerk_client import ClerkInviteResult
from porterchain_api.auth.clerk_registry import clerk_client_for_kind
from porterchain_api.config import Settings
from porterchain_api.domain.admin_states import AdminRole
from porterchain_api.invitation_models import UserInvitation

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

OPEN_SIGNUP_USER_TYPES = frozenset({"customer", "merchant"})


def pending_clerk_id(email: str) -> str:
    return f"pending:{email.lower().strip()}"


class InvitationService:
    """Send Clerk invitations for drivers only. Staff use staff IdP enroll (no Clerk)."""

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
