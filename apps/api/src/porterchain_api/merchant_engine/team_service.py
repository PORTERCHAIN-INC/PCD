"""Merchant team invitations — Clerk invite required (no self-signup)."""

from sqlalchemy.orm import Session

from porterchain_api.auth.clerk_registry import is_clerk_secret_configured
from porterchain_api.auth.invitation_service import InvitationService
from porterchain_api.config import Settings
from porterchain_api.domain.merchant_states import MerchantRole
from porterchain_api.merchant_engine.rbac import MerchantContext, modules_for_role, permissions_catalog
from porterchain_api.merchant_models import MerchantAuditLog, MerchantUser


class MerchantTeamService:
    def list_members(self, db: Session, ctx: MerchantContext) -> list[MerchantUser]:
        return (
            db.query(MerchantUser)
            .filter(MerchantUser.merchant_id == ctx.merchant.id, MerchantUser.is_active.is_(True))
            .order_by(MerchantUser.created_at)
            .all()
        )

    def overview(self, db: Session, ctx: MerchantContext) -> dict:
        members = self.list_members(db, ctx)
        return {
            "member_count": len(members),
            "roles": self.roles_and_permissions(),
            "two_factor": self.two_factor_status(ctx),
            "recent_activity": self.activity_log(db, ctx, limit=10),
        }

    def invite_member(
        self,
        db: Session,
        ctx: MerchantContext,
        settings: Settings,
        *,
        email: str,
        role: str,
    ) -> MerchantUser:
        if not is_clerk_secret_configured(settings, "merchant"):
            raise ValueError("clerk_not_configured")
        return InvitationService().invite_merchant_member(db, ctx, settings, email=email, role=role)

    def remove_member(self, db: Session, ctx: MerchantContext, user_id: str) -> None:
        user = (
            db.query(MerchantUser)
            .filter(MerchantUser.id == user_id, MerchantUser.merchant_id == ctx.merchant.id)
            .first()
        )
        if not user:
            raise LookupError("team_member_not_found")
        user.is_active = False
        self._audit(db, ctx, "team.removed", user.id, {"email": user.email})
        db.commit()

    def update_role(self, db: Session, ctx: MerchantContext, user_id: str, role: str) -> MerchantUser:
        if role not in {r.value for r in MerchantRole}:
            raise ValueError("invalid_team_role")
        user = (
            db.query(MerchantUser)
            .filter(MerchantUser.id == user_id, MerchantUser.merchant_id == ctx.merchant.id)
            .first()
        )
        if not user:
            raise LookupError("team_member_not_found")
        user.role = role
        self._audit(db, ctx, "team.role_updated", user.id, {"email": user.email, "role": role})
        db.commit()
        db.refresh(user)
        return user

    def permissions_for_role(self, role: str) -> list[str]:
        role_enum = MerchantRole(role) if role in {r.value for r in MerchantRole} else MerchantRole.OPS
        return sorted(modules_for_role(role_enum))

    def roles_and_permissions(self) -> dict:
        return permissions_catalog()

    def activity_log(self, db: Session, ctx: MerchantContext, *, limit: int = 50) -> list[dict]:
        logs = (
            db.query(MerchantAuditLog)
            .filter(MerchantAuditLog.merchant_id == ctx.merchant.id)
            .order_by(MerchantAuditLog.created_at.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "id": log.id,
                "action": log.action,
                "actor_user_id": log.actor_user_id,
                "resource_type": log.resource_type,
                "resource_id": log.resource_id,
                "payload": log.payload,
                "created_at": log.created_at.isoformat() if log.created_at else None,
            }
            for log in logs
        ]

    def two_factor_status(self, ctx: MerchantContext) -> dict:
        """Two-factor is enforced by Clerk; Porterchain stores preference flags in audit only."""
        return {
            "enabled": False,
            "method": "none",
            "enforced_org_wide": False,
            "note": "Two-factor authentication is managed in Clerk. Enable MFA in your Clerk account settings.",
        }

    def update_two_factor(
        self,
        db: Session,
        ctx: MerchantContext,
        *,
        enabled: bool,
        method: str | None = None,
    ) -> dict:
        self._audit(db, ctx, "team.two_factor_updated", ctx.user.id, {"enabled": enabled, "method": method})
        db.commit()
        return {
            "enabled": enabled,
            "method": method or "none",
            "enforced_org_wide": False,
            "note": "Two-factor authentication is managed in Clerk. Enable MFA in your Clerk account settings.",
        }

    def _audit(self, db: Session, ctx: MerchantContext, action: str, resource_id: str, payload: dict) -> None:
        db.add(
            MerchantAuditLog(
                merchant_id=ctx.merchant.id,
                actor_user_id=ctx.user.id,
                action=action,
                resource_type="merchant_user",
                resource_id=resource_id,
                payload=payload,
            )
        )
