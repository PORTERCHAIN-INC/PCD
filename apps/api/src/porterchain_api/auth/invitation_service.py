"""Invitation workflows — Driver + optional Admin customer Clerk invites.

Staff use staff IdP enroll (``StaffIdpService``). Merchant seats are email-bind via
``merchant_engine.team_service.ensure_merchant_seat``. Retail customers may self-signup
on Platform Clerk; Admin can also mint a local customer row and optionally invite.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.admin_engine.audit import log_admin_audit
from porterchain_api.admin_engine.rbac import AdminContext
from porterchain_api.auth.clerk_client import ClerkInviteResult
from porterchain_api.auth.clerk_registry import (
    clerk_client_for_kind,
    is_clerk_secret_configured,
)
from porterchain_api.config import Settings
from porterchain_api.domain.admin_states import AdminRole
from porterchain_api.invitation_models import UserInvitation

logger = logging.getLogger(__name__)

# All AdminRole values are enrollable via Staff IdP (real-world role matrix).
INVITABLE_ADMIN_ROLES = frozenset(role.value for role in AdminRole)

OPEN_SIGNUP_USER_TYPES = frozenset({"customer", "merchant"})


def pending_clerk_id(email: str) -> str:
    return f"pending:{email.lower().strip()}"


class InvitationService:
    """Send Clerk invitations for drivers and Admin-created retail customers."""

    def invite_driver(
        self,
        db: Session,
        ctx: AdminContext | None,
        settings: Settings,
        driver: Any,
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
            log_admin_audit(
                db,
                ctx,
                action="driver.invited",
                resource_type="driver",
                resource_id=driver.id,
                payload={"email": normalized},
            )
        db.commit()
        db.refresh(invitation)
        return invitation

    def invite_existing_driver(
        self,
        db: Session,
        ctx: AdminContext | None,
        settings: Settings,
        driver: Any,
    ) -> dict[str, Any]:
        if not is_clerk_secret_configured(settings, "driver"):
            raise RuntimeError("clerk_not_configured")
        invitation = self.invite_driver(db, ctx, settings, driver)
        return {
            "driver_id": driver.id,
            "email": driver.email,
            "invitation_status": invitation.status,
            "clerk_action": invitation.invitation_metadata.get("clerk_action"),
        }

    def invite_customer(
        self,
        db: Session,
        ctx: AdminContext | None,
        settings: Settings,
        customer: Any,
    ) -> UserInvitation:
        """Invite (or link) a retail customer on Platform Clerk. Does not commit."""
        if not is_clerk_secret_configured(settings, "customer"):
            raise ValueError("clerk_not_configured")
        normalized = (customer.email or "").lower().strip()
        if not normalized:
            raise ValueError("email_required")
        clerk = clerk_client_for_kind(settings, "customer")
        redirect = f"{settings.customer_portal_url.rstrip('/')}/sign-up"
        metadata = {
            "role": "customer",
            "porterchain_role": "customer",
            "user_type": "customer",
            "customer_id": customer.id,
        }
        clerk_result = clerk.invite_user(normalized, redirect_url=redirect, public_metadata=metadata)
        if clerk_result.clerk_user_id:
            customer.clerk_user_id = clerk_result.clerk_user_id
            from porterchain_api.auth.authz_sync import (
                sync_authz_after_persona_mutation,
            )

            sync_authz_after_persona_mutation(db, clerk_result.clerk_user_id)
        invitation = self._record_invitation(
            db,
            email=normalized,
            user_type="customer",
            role="customer",
            clerk_result=clerk_result,
            platform_user_id=customer.id,
            invited_by=ctx.user.id if ctx and ctx.user else None,
            redirect_url=redirect,
            metadata={"full_name": getattr(customer, "full_name", None)},
        )
        if ctx:
            log_admin_audit(
                db,
                ctx,
                action="customer.invited",
                resource_type="customer",
                resource_id=customer.id,
                payload={"email": normalized, "clerk_action": clerk_result.action},
            )
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
