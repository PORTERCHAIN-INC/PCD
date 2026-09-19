"""Merchant team seats — email bind, no Clerk Invitation API.

Teammate signs up / signs in on PorterChain Platform; UserSync rebinds
``pending:{email}`` → real ``user_`` clerk id on verified email match.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.auth.email_identity import normalize_email
from porterchain_api.auth.invitation_service import pending_clerk_id
from porterchain_api.domain.catalog_labels import merchant_status_label, seat_status_label
from porterchain_api.domain.merchant_states import PORTAL_OPEN_STATUSES, MerchantRole
from porterchain_api.merchant_engine.audit_copy import serialize_audit_log
from porterchain_api.merchant_engine.lookups import get_merchant
from porterchain_api.merchant_engine.rbac import MerchantContext, english_role, modules_for_role, permissions_catalog
from porterchain_api.merchant_models import MerchantAuditLog, MerchantUser


def seat_status(user: MerchantUser) -> str:
    if not user.is_active:
        return "off"
    clerk_id = user.clerk_user_id or ""
    if clerk_id.startswith("pending:") or clerk_id.startswith("pending_"):
        return "pending"
    return "active"


def serialize_member(user: MerchantUser) -> dict:
    status = seat_status(user)
    return {
        "id": user.id,
        "email": user.email,
        "role": user.role,
        "role_label": english_role(user.role),
        "is_active": bool(user.is_active),
        "seat_status": status,
        "seat_status_label": seat_status_label(status),
        "created_at": user.created_at,
    }


def list_switcher_memberships(
    db: Session,
    seats: list[Any],
    selected_merchant_id: str | None,
) -> dict:
    """Companies this Clerk user can switch to with X-Merchant-Id (not Clerk orgs)."""
    memberships = []
    for seat in seats:
        merchant = get_merchant(db, seat.merchant_id)
        if not merchant:
            continue
        memberships.append(
            {
                "merchant_id": merchant.id,
                "company_name": merchant.company_name,
                "status": merchant.status,
                "status_label": merchant_status_label(merchant.status),
                "role": seat.role,
                "role_label": english_role(seat.role),
                "can_open": merchant.status in PORTAL_OPEN_STATUSES,
                "is_current": merchant.id == selected_merchant_id,
            }
        )
    memberships.sort(key=lambda m: (not m["can_open"], m["company_name"] or ""))
    return {"memberships": memberships}


class MerchantTeamService:
    def list_members(self, db: Session, ctx: MerchantContext) -> list[MerchantUser]:
        return (
            db.query(MerchantUser)
            .filter(MerchantUser.merchant_id == ctx.merchant.id, MerchantUser.is_active.is_(True))
            .order_by(MerchantUser.created_at)
            .all()
        )

    def list_seats(self, db: Session, ctx: MerchantContext) -> list[MerchantUser]:
        return (
            db.query(MerchantUser)
            .filter(MerchantUser.merchant_id == ctx.merchant.id)
            .order_by(MerchantUser.is_active.desc(), MerchantUser.created_at)
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

    def _sync_team_contacts(self, db: Session, merchant) -> None:
        from porterchain_api.merchant_engine.contacts_service import MerchantContactsService

        MerchantContactsService().sync_team_contacts(db, merchant)

    def add_seat(
        self,
        db: Session,
        ctx: MerchantContext,
        *,
        email: str,
        role: str,
    ) -> MerchantUser:
        """Reserve a team seat by email. No Clerk invite email is sent."""
        user = ensure_merchant_seat(
            db,
            merchant_id=ctx.merchant.id,
            email=email,
            role=role,
            actor_user_id=ctx.user.id,
            audit_action="team.seat_added",
        )
        self._sync_team_contacts(db, ctx.merchant)
        return user

    # Back-compat name used by older callers — delegates to add_seat (no Clerk).
    def invite_member(
        self,
        db: Session,
        ctx: MerchantContext,
        settings=None,  # noqa: ANN001 — unused; kept for call-site compat during cutover
        *,
        email: str,
        role: str,
    ) -> MerchantUser:
        _ = settings
        return self.add_seat(db, ctx, email=email, role=role)

    def remove_member(self, db: Session, ctx: MerchantContext, user_id: str) -> None:
        user = (
            db.query(MerchantUser)
            .filter(MerchantUser.id == user_id, MerchantUser.merchant_id == ctx.merchant.id)
            .first()
        )
        if not user:
            raise LookupError("team_member_not_found")
        assert_not_last_owner(db, merchant_id=ctx.merchant.id, user=user, next_role=None)
        user.is_active = False
        self._audit(db, ctx, "team.removed", user.id, {"email": user.email})
        db.commit()
        from porterchain_api.auth.authz_sync import sync_authz_after_persona_mutation

        sync_authz_after_persona_mutation(db, user.clerk_user_id)
        self._sync_team_contacts(db, ctx.merchant)

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
        assert_not_last_owner(db, merchant_id=ctx.merchant.id, user=user, next_role=role)
        user.role = role
        self._audit(db, ctx, "team.role_updated", user.id, {"email": user.email, "role": role})
        db.commit()
        db.refresh(user)
        from porterchain_api.auth.authz_sync import sync_authz_after_persona_mutation

        sync_authz_after_persona_mutation(db, user.clerk_user_id)
        return user

    def update_member(
        self,
        db: Session,
        ctx: MerchantContext,
        user_id: str,
        *,
        role: str | None = None,
        is_active: bool | None = None,
    ) -> MerchantUser:
        if role is None and is_active is None:
            raise ValueError("nothing_to_update")
        user = (
            db.query(MerchantUser)
            .filter(MerchantUser.id == user_id, MerchantUser.merchant_id == ctx.merchant.id)
            .first()
        )
        if not user:
            raise LookupError("team_member_not_found")
        if role is not None:
            if role not in {r.value for r in MerchantRole}:
                raise ValueError("invalid_team_role")
            assert_not_last_owner(db, merchant_id=ctx.merchant.id, user=user, next_role=role)
            user.role = role
        if is_active is not None:
            if is_active is False:
                assert_not_last_owner(db, merchant_id=ctx.merchant.id, user=user, next_role=None)
            user.is_active = is_active
        self._audit(
            db,
            ctx,
            "team.updated",
            user.id,
            {"email": user.email, "role": user.role, "is_active": bool(user.is_active)},
        )
        db.commit()
        db.refresh(user)
        from porterchain_api.auth.authz_sync import sync_authz_after_persona_mutation

        sync_authz_after_persona_mutation(db, user.clerk_user_id)
        self._sync_team_contacts(db, ctx.merchant)
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
        return [serialize_audit_log(log, include_payload=True) for log in logs]

    def two_factor_status(self, ctx: MerchantContext) -> dict:
        _ = ctx
        return {
            "enabled": False,
            "method": "none",
            "enforced_org_wide": False,
            "note": "Two-factor authentication is managed in Clerk for merchant portal users.",
        }

    def update_two_factor(
        self,
        db: Session,
        ctx: MerchantContext,
        *,
        enabled: bool,
        method: str | None = None,
    ) -> dict:
        _ = db, enabled, method
        return self.two_factor_status(ctx)

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


def _active_owners(db: Session, merchant_id: str) -> list[MerchantUser]:
    return (
        db.query(MerchantUser)
        .filter(
            MerchantUser.merchant_id == merchant_id,
            MerchantUser.is_active.is_(True),
            MerchantUser.role == MerchantRole.OWNER.value,
        )
        .all()
    )


def assert_not_last_owner(
    db: Session,
    *,
    merchant_id: str,
    user: MerchantUser,
    next_role: str | None,
) -> None:
    """M-30: never leave a merchant with zero active owners."""
    if not user.is_active or user.role != MerchantRole.OWNER.value:
        return
    demoting = next_role is None or next_role != MerchantRole.OWNER.value
    if not demoting:
        return
    owners = _active_owners(db, merchant_id)
    if len(owners) <= 1 and any(o.id == user.id for o in owners):
        raise ValueError("last_owner_required")


def ensure_merchant_seat(
    db: Session,
    *,
    merchant_id: str,
    email: str,
    role: str,
    actor_user_id: str | None = None,
    audit_action: str = "team.seat_added",
    commit: bool = True,
) -> MerchantUser:
    """Create or reactivate a MerchantUser seat bound by email (pending Clerk id)."""
    normalized = normalize_email(email)
    if not normalized:
        raise ValueError("email_required")
    # M-30: reject unknown roles (no silent OPS fallback).
    if role not in {r.value for r in MerchantRole}:
        raise ValueError("invalid_team_role")
    role_value = role
    clerk_ref = pending_clerk_id(normalized)

    conflict = (
        db.query(MerchantUser)
        .filter(MerchantUser.clerk_user_id == clerk_ref, MerchantUser.merchant_id != merchant_id)
        .first()
    )
    if conflict:
        raise ValueError("email_seat_taken")

    existing = (
        db.query(MerchantUser)
        .filter(MerchantUser.merchant_id == merchant_id, MerchantUser.email == normalized)
        .first()
    )
    if existing:
        existing.role = role_value
        existing.is_active = True
        if not existing.clerk_user_id or not str(existing.clerk_user_id).startswith("user_"):
            existing.clerk_user_id = clerk_ref
        user = existing
    else:
        user = MerchantUser(
            merchant_id=merchant_id,
            clerk_user_id=clerk_ref,
            email=normalized,
            role=role_value,
            is_active=True,
        )
        db.add(user)

    db.flush()
    db.add(
        MerchantAuditLog(
            merchant_id=merchant_id,
            actor_user_id=actor_user_id,
            action=audit_action,
            resource_type="merchant_user",
            resource_id=user.id,
            payload={"email": normalized, "role": role_value, "clerk_invite": False},
        )
    )
    if commit:
        db.commit()
        db.refresh(user)
    return user


def add_linked_seat(
    db: Session,
    *,
    merchant_id: str,
    email: str,
    clerk_user_id: str,
    role: str,
    is_active: bool = True,
) -> MerchantUser:
    user = MerchantUser(
        merchant_id=merchant_id,
        clerk_user_id=clerk_user_id,
        email=email,
        role=role,
        is_active=is_active,
    )
    db.add(user)
    db.flush()
    return user


def update_seat(
    db: Session,
    user: MerchantUser,
    *,
    role: str | None = None,
    is_active: bool | None = None,
) -> MerchantUser:
    if role is not None:
        user.role = role
    if is_active is not None:
        user.is_active = is_active
    return user


def activate_seats(users: list[MerchantUser]) -> None:
    for user in users:
        user.is_active = True


def deactivate_seat(db: Session, user_id: str) -> None:
    user = db.get(MerchantUser, user_id)
    if user:
        user.is_active = False


def bind_seat_clerk(
    db: Session,
    user_id: str,
    clerk_user_id: str,
    *,
    activate: bool = False,
) -> MerchantUser | None:
    user = db.get(MerchantUser, user_id)
    if not user:
        return None
    user.clerk_user_id = clerk_user_id
    if activate:
        user.is_active = True
    return user
