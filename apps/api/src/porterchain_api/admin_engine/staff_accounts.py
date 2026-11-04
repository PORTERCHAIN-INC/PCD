"""Staff accounts — AdminUser rows + Keycloak users (realm ``porterchain``, client ``pc-admin``).

Login, password, TOTP and sessions live in Keycloak. This module provisions the AdminUser,
binds the internal ``staff:{id}`` subject + SpiceDB tuples, and drives the Keycloak user
through the Admin REST API (invite email, MFA reset, disable).
"""

from __future__ import annotations

import time
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.admin_engine.audit import log_admin_audit
from porterchain_api.admin_engine.rbac import AdminContext
from porterchain_api.admin_models import AdminUser
from porterchain_api.auth import keycloak_admin
from porterchain_api.auth.invitation_service import INVITABLE_ADMIN_ROLES
from porterchain_api.config import Settings
from porterchain_shared.redis_health import is_local_env


def ensure_staff_identity(db: Session, user: AdminUser) -> str:
    """Bind AdminUser to PorterchainUser + SpiceDB using ``staff:{admin_id}`` subject.

    Always reconciles SpiceDB — never skip authz sync on an already-bound row
    (that left Local Super Admin sessions without ``platform#portal``).
    """
    from porterchain_api.auth.staff_identity import ensure_staff_porterchain_user
    from porterchain_api.authz.tuples import TupleWriter

    subject_key = f"staff:{user.id}"
    current = str(user.auth_subject or "")
    legacy = None
    if current.startswith("user_") or current == "dev_idp_user":
        legacy = current

    pc = ensure_staff_porterchain_user(
        db,
        subject_key=subject_key,
        email=user.email,
        linked_user_id=user.porterchain_user_id,
        legacy_idp_user_id=legacy,
    )
    user.porterchain_user_id = pc.id
    user.auth_subject = subject_key
    db.flush()
    TupleWriter().sync_user_from_profiles(db, pc)
    try:
        from porterchain_api.auth.principal_cache import cache_invalidate

        cache_invalidate(pc.id)
    except Exception:  # noqa: BLE001
        pass
    db.commit()
    return pc.id


def _invite_actions(role: str) -> list[str]:
    actions = ["VERIFY_EMAIL", "UPDATE_PASSWORD"]
    if role in keycloak_admin.MFA_TIERS:
        actions.append("CONFIGURE_TOTP")
    return actions


def _admin(settings: Settings) -> keycloak_admin.KeycloakAdmin | None:
    """Keycloak admin client, or None in local/test when the service account is unset."""
    if keycloak_admin.configured(settings):
        return keycloak_admin.KeycloakAdmin(settings)
    if is_local_env(settings.app_env):
        return None
    raise keycloak_admin.KeycloakAdminUnavailable("keycloak_admin_unconfigured")


def _payload(user: AdminUser, *, provisioned: bool, email_sent: bool, created: bool = False) -> dict[str, Any]:
    return {
        "admin_user_id": user.id,
        "email": user.email,
        "role": user.role,
        "keycloak_provisioned": provisioned,
        "keycloak_user_created": created,
        "email_sent": email_sent,
        # L213: StaffEnrollResponse requires expires_at (setup link lifetime); missing it 500'd enroll.
        "expires_at": time.time() + keycloak_admin.ACTION_LIFESPAN_SECONDS,
    }


class StaffAccountService:
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

        kc = _admin(settings)
        user = db.query(AdminUser).filter(AdminUser.email == normalized).first()
        if user:
            user.name = name or user.name
            user.role = role
            user.is_active = True
        else:
            user = AdminUser(
                auth_subject=f"pending:{normalized}",
                email=normalized,
                name=name,
                role=role,
                is_active=True,
            )
            db.add(user)
        db.flush()
        ensure_staff_identity(db, user)
        db.refresh(user)

        created = email_sent = False
        if kc is not None:
            kc_id, created = kc.ensure_staff_user(email=normalized, name=user.name, role=role)
            pending = kc.pending_actions(kc_id)
            email_sent = kc.send_actions_email(kc_id, pending or _invite_actions(role))

        log_admin_audit(
            db,
            ctx,
            action="staff.enrolled",
            resource_type="admin_user",
            resource_id=user.id,
            payload={"email": normalized, "role": role, "email_sent": email_sent,
                     "keycloak_provisioned": kc is not None},
        )
        db.commit()
        db.refresh(user)
        return _payload(user, provisioned=kc is not None, email_sent=email_sent, created=created)

    def reissue(
        self,
        db: Session,
        ctx: AdminContext,
        settings: Settings,
        admin_user_id: str,
    ) -> dict[str, Any]:
        """Re-send the Keycloak setup email (expired link / never finished setup)."""
        user = db.query(AdminUser).filter(AdminUser.id == admin_user_id).first()
        if not user:
            raise LookupError("staff_not_found")
        if not user.is_active:
            raise ValueError("staff_inactive")
        kc = _admin(settings)
        email_sent = False
        if kc is not None:
            kc_id, _ = kc.ensure_staff_user(email=user.email, name=user.name, role=user.role)
            pending = kc.pending_actions(kc_id)
            email_sent = kc.send_actions_email(kc_id, pending or ["UPDATE_PASSWORD"])
        log_admin_audit(
            db,
            ctx,
            action="staff.enrollment_reissued",
            resource_type="admin_user",
            resource_id=user.id,
            payload={"email": user.email, "role": user.role, "email_sent": email_sent},
        )
        db.commit()
        return _payload(user, provisioned=kc is not None, email_sent=email_sent)

    def recover_device(
        self,
        db: Session,
        ctx: AdminContext,
        settings: Settings,
        admin_user_id: str,
        *,
        reason: str | None = None,
    ) -> dict[str, Any]:
        """Lost device: drop OTP/passkeys in Keycloak, force TOTP re-setup, end all sessions."""
        from porterchain_api.auth.staff_security_events import record_security_event

        user = db.query(AdminUser).filter(AdminUser.id == admin_user_id).first()
        if not user:
            raise LookupError("staff_not_found")
        if not user.is_active:
            raise ValueError("staff_inactive")
        kc = _admin(settings)
        removed = 0
        email_sent = False
        if kc is not None:
            kc_id, _ = kc.ensure_staff_user(email=user.email, name=user.name, role=user.role)
            removed = kc.reset_mfa(kc_id)
            email_sent = kc.send_actions_email(kc_id, ["CONFIGURE_TOTP"])
        log_admin_audit(
            db,
            ctx,
            action="staff.device_recovered",
            resource_type="admin_user",
            resource_id=user.id,
            payload={"email": user.email, "reason": reason, "credentials_removed": removed,
                     "email_sent": email_sent},
        )
        db.commit()
        record_security_event(
            user.id,
            kind="device_recovery",
            detail={"by": ctx.user.email if getattr(ctx, "user", None) else None,
                    "credentials_removed": removed},
        )
        out = _payload(user, provisioned=kc is not None, email_sent=email_sent)
        out["credentials_removed"] = removed
        out["sessions_revoked"] = kc is not None
        return out

    def set_active(
        self, db: Session, ctx: AdminContext, settings: Settings, admin_user_id: str, active: bool
    ) -> dict[str, Any]:
        """L220: deactivate / reactivate a staff login (Keycloak disable + sessions ended)."""
        user = db.query(AdminUser).filter(AdminUser.id == admin_user_id).first()
        if not user:
            raise LookupError("staff_not_found")
        me = getattr(getattr(ctx, "user", None), "id", None)
        if not active and me == user.id:
            raise ValueError("cannot_deactivate_self")
        if not active and user.role == "super_admin" and user.is_active:
            others = (
                db.query(AdminUser)
                .filter(AdminUser.role == "super_admin", AdminUser.is_active.is_(True), AdminUser.id != user.id)
                .count()
            )
            if others == 0:
                raise ValueError("last_super_admin")
        user.is_active = bool(active)
        log_admin_audit(
            db,
            ctx,
            action="staff.reactivated" if active else "staff.deactivated",
            resource_type="admin_user",
            resource_id=user.id,
            payload={"email": user.email, "role": user.role},
        )
        db.commit()
        kc_done = False
        if active:
            kc = _admin(settings) if keycloak_admin.configured(settings) else None
            if kc is not None:
                kc.ensure_staff_user(email=user.email, name=user.name, role=user.role)  # re-enables
                kc_done = True
        else:
            kc_done = keycloak_admin.end_staff_sessions(settings, user.email, disable=True)
        return {"id": user.id, "email": user.email, "is_active": user.is_active, "login_updated": kc_done}

    def deactivate_login(self, settings: Settings, email: str) -> bool:
        """Disable the Keycloak user (called when an AdminUser is deactivated)."""
        kc = _admin(settings)
        return kc.disable(email) if kc is not None else False
