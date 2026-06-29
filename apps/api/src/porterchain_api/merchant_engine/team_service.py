"""Merchant team management per ROLE_PERMISSIONS.md."""

from sqlalchemy.orm import Session

from porterchain_api.domain.merchant_states import MerchantRole
from porterchain_api.merchant_engine.rbac import MerchantContext
from porterchain_api.merchant_models import MerchantAuditLog, MerchantUser


class MerchantTeamService:
    def list_members(self, db: Session, ctx: MerchantContext) -> list[MerchantUser]:
        return (
            db.query(MerchantUser)
            .filter(MerchantUser.merchant_id == ctx.merchant.id, MerchantUser.is_active.is_(True))
            .order_by(MerchantUser.created_at)
            .all()
        )

    def invite_member(
        self,
        db: Session,
        ctx: MerchantContext,
        *,
        email: str,
        role: str,
    ) -> MerchantUser:
        role_enum = MerchantRole(role) if role in {r.value for r in MerchantRole} else MerchantRole.OPS
        existing = (
            db.query(MerchantUser)
            .filter(MerchantUser.merchant_id == ctx.merchant.id, MerchantUser.email == email)
            .first()
        )
        if existing:
            existing.role = role_enum.value
            existing.is_active = True
            db.commit()
            db.refresh(existing)
            return existing

        user = MerchantUser(
            merchant_id=ctx.merchant.id,
            clerk_user_id=f"pending_{email}",
            email=email,
            role=role_enum.value,
        )
        db.add(user)
        db.flush()
        db.add(
            MerchantAuditLog(
                merchant_id=ctx.merchant.id,
                actor_user_id=ctx.user.id,
                action="team.invited",
                resource_type="merchant_user",
                resource_id=user.id,
                payload={"email": email, "role": role_enum.value},
            )
        )
        db.commit()
        db.refresh(user)
        return user

    def remove_member(self, db: Session, ctx: MerchantContext, user_id: str) -> None:
        user = (
            db.query(MerchantUser)
            .filter(MerchantUser.id == user_id, MerchantUser.merchant_id == ctx.merchant.id)
            .first()
        )
        if not user:
            raise LookupError("team_member_not_found")
        if user.id == ctx.user.id:
            raise PermissionError("cannot_remove_self")
        user.is_active = False
        db.add(
            MerchantAuditLog(
                merchant_id=ctx.merchant.id,
                actor_user_id=ctx.user.id,
                action="team.removed",
                resource_type="merchant_user",
                resource_id=user_id,
                payload={},
            )
        )
        db.commit()

    def update_role(self, db: Session, ctx: MerchantContext, user_id: str, role: str) -> MerchantUser:
        user = (
            db.query(MerchantUser)
            .filter(MerchantUser.id == user_id, MerchantUser.merchant_id == ctx.merchant.id)
            .first()
        )
        if not user:
            raise LookupError("team_member_not_found")
        user.role = role
        db.commit()
        db.refresh(user)
        return user
