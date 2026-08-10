"""Staff IdP enrollment — provision AdminUser without Clerk.

Canonical admin identity path: enroll → activate/login-request → Redis session.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.admin_engine.audit import log_admin_audit
from porterchain_api.admin_engine.rbac import AdminContext
from porterchain_api.admin_models import AdminUser
from porterchain_api.auth.invitation_service import INVITABLE_ADMIN_ROLES, pending_clerk_id
from porterchain_api.auth.staff_enrollment import (
    StaffEnrollmentToken,
    consume_enrollment_token,
    create_enrollment_token,
    peek_enrollment_token,
)
from porterchain_api.auth.staff_mail import send_staff_activate_email
from porterchain_api.auth.staff_session import StaffSession, create_session
from porterchain_api.config import Settings
from porterchain_api.user_models import PorterchainUser
from porterchain_shared.redis_health import is_local_env


def ensure_staff_identity(db: Session, user: AdminUser) -> str:
    """Bind AdminUser to PorterchainUser + SpiceDB using ``staff:{admin_id}`` subject."""
    subject_key = f"staff:{user.id}"
    if (
        user.porterchain_user_id
        and str(user.clerk_user_id or "") == subject_key
    ):
        return user.porterchain_user_id

    by_subject = (
        db.query(PorterchainUser)
        .filter(PorterchainUser.clerk_user_id == subject_key)
        .first()
    )
    linked = (
        db.query(PorterchainUser).filter(PorterchainUser.id == user.porterchain_user_id).first()
        if user.porterchain_user_id
        else None
    )
    legacy_clerk = None
    if user.clerk_user_id and str(user.clerk_user_id).startswith("user_"):
        legacy_clerk = (
            db.query(PorterchainUser)
            .filter(PorterchainUser.clerk_user_id == user.clerk_user_id)
            .first()
        )

    # Prefer an existing staff:{id} registry row to avoid unique collisions when
    # AdminUser still points at a legacy/dev PorterchainUser.
    pc = by_subject or linked or legacy_clerk
    if not pc:
        pc = PorterchainUser(
            clerk_user_id=subject_key,
            email=user.email,
            role="admin",
            status="active",
            onboarding_status="complete",
            default_workspace="admin",
        )
        db.add(pc)
        db.flush()
    else:
        if pc.clerk_user_id != subject_key:
            conflict = (
                db.query(PorterchainUser)
                .filter(
                    PorterchainUser.clerk_user_id == subject_key,
                    PorterchainUser.id != pc.id,
                )
                .first()
            )
            if conflict is not None:
                pc = conflict
            else:
                pc.clerk_user_id = subject_key
        pc.email = user.email or pc.email
        pc.status = "active"
        pc.role = "admin"
        pc.default_workspace = "admin"

    user.porterchain_user_id = pc.id
    user.clerk_user_id = subject_key
    db.flush()

    from porterchain_api.authz.tuples import TupleWriter

    TupleWriter().sync_user_from_profiles(db, pc)
    db.commit()
    return pc.id


def _token_payload(
    *,
    user: AdminUser,
    enrollment: StaffEnrollmentToken,
    email_sent: bool,
    include_token: bool,
) -> dict[str, Any]:
    out: dict[str, Any] = {
        "admin_user_id": user.id,
        "email": user.email,
        "role": user.role,
        "expires_at": enrollment.expires_at,
        "clerk_invite": False,
        "email_sent": email_sent,
    }
    if include_token:
        out["enrollment_token"] = enrollment.token
    return out


class StaffIdpService:
    def enroll(
        self,
        db: Session,
        ctx: AdminContext,
        settings: Settings,
        *,
        email: str,
        role: str,
        name: str | None = None,
    ) -> dict[str, Any]:
        normalized = email.lower().strip()
        if not normalized:
            raise ValueError("email_required")
        if role not in INVITABLE_ADMIN_ROLES:
            raise ValueError("invalid_admin_role")

        clerk_ref = pending_clerk_id(normalized)
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
            if not str(user.clerk_user_id or "").startswith("user_"):
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
        ensure_staff_identity(db, user)
        db.refresh(user)

        enrollment = create_enrollment_token(
            admin_user_id=user.id,
            email=normalized,
            role=role,
        )
        if enrollment is None:
            raise ValueError("staff_enrollment_redis_unavailable")

        email_sent = send_staff_activate_email(
            settings, email=normalized, token=enrollment.token
        )

        log_admin_audit(
            db,
            ctx,
            action="staff.enrolled",
            resource_type="admin_user",
            resource_id=user.id,
            payload={"email": normalized, "role": role, "email_sent": email_sent},
        )
        db.commit()
        db.refresh(user)
        # Admin UI still gets token for copy-once (Mailpit may lag).
        return _token_payload(
            user=user,
            enrollment=enrollment,
            email_sent=email_sent,
            include_token=True,
        )

    def peek(self, token: str) -> StaffEnrollmentToken | None:
        return peek_enrollment_token(token)

    def reissue(
        self,
        db: Session,
        ctx: AdminContext,
        settings: Settings,
        admin_user_id: str,
    ) -> dict[str, Any]:
        """Mint a fresh enrollment token for an existing AdminUser (session expiry / lost link)."""
        user = db.query(AdminUser).filter(AdminUser.id == admin_user_id).first()
        if not user:
            raise LookupError("staff_not_found")
        if not user.is_active:
            raise ValueError("staff_inactive")

        ensure_staff_identity(db, user)
        db.refresh(user)

        enrollment = create_enrollment_token(
            admin_user_id=user.id,
            email=user.email,
            role=user.role,
        )
        if enrollment is None:
            raise ValueError("staff_enrollment_redis_unavailable")

        email_sent = send_staff_activate_email(
            settings, email=user.email, token=enrollment.token
        )

        log_admin_audit(
            db,
            ctx,
            action="staff.enrollment_reissued",
            resource_type="admin_user",
            resource_id=user.id,
            payload={"email": user.email, "role": user.role, "email_sent": email_sent},
        )
        db.commit()
        return _token_payload(
            user=user,
            enrollment=enrollment,
            email_sent=email_sent,
            include_token=True,
        )

    def request_login(self, db: Session, settings: Settings, *, email: str) -> dict[str, Any]:
        """Self-service login: email a one-time activate link (token only in local)."""
        normalized = email.lower().strip()
        if not normalized:
            raise ValueError("email_required")

        user = db.query(AdminUser).filter(AdminUser.email == normalized).first()
        if not user or not user.is_active:
            # Anti-enumeration: identical UX whether or not the email exists.
            return {"ok": True, "email_sent": True}

        ensure_staff_identity(db, user)
        db.refresh(user)

        enrollment = create_enrollment_token(
            admin_user_id=user.id,
            email=user.email,
            role=user.role,
        )
        if enrollment is None:
            raise ValueError("staff_enrollment_redis_unavailable")

        email_sent = send_staff_activate_email(
            settings, email=user.email, token=enrollment.token
        )
        db.commit()
        return _token_payload(
            user=user,
            enrollment=enrollment,
            email_sent=email_sent,
            include_token=is_local_env(settings.app_env),
        )

    def activate(self, db: Session, token: str) -> dict[str, Any]:
        enrollment = consume_enrollment_token(token)
        if enrollment is None:
            raise LookupError("enrollment_invalid_or_expired")

        user = db.query(AdminUser).filter(AdminUser.id == enrollment.admin_user_id).first()
        if not user:
            raise LookupError("staff_not_found")

        user.is_active = True
        user.email = enrollment.email
        user.role = enrollment.role
        db.flush()
        ensure_staff_identity(db, user)
        db.refresh(user)

        session: StaffSession | None = create_session(
            admin_user_id=user.id,
            email=user.email,
            role=user.role,
        )
        if session is None:
            raise ValueError("staff_session_redis_unavailable")

        return {
            "admin_user_id": user.id,
            "email": user.email,
            "role": user.role,
            "session_id": session.session_id,
            "bearer_token": f"staff_sess_{session.session_id}",
            "expires_at": session.expires_at,
        }
