"""Staff AdminUser reads owned by admin_engine."""

from __future__ import annotations

from sqlalchemy.orm import Session

from porterchain_api.admin_models import AdminUser
from porterchain_api.domain.admin_states import AdminRole

# Canonical local Super Admin — same principal for Staff IdP local-session and
# API Bearer-dev tooling. Never a production identity.
LOCAL_SUPER_ADMIN_EMAIL = "admin@porterchain.com"
LOCAL_SUPER_ADMIN_NAME = "Local Super Admin"
LOCAL_SUPER_ADMIN_LEGACY_SUBJECT = "dev_clerk_user"


def get_admin_user(db: Session, admin_id: str | None) -> AdminUser | None:
    if not admin_id:
        return None
    return db.get(AdminUser, admin_id)


def get_admin_by_clerk(db: Session, clerk_user_id: str) -> AdminUser | None:
    return (
        db.query(AdminUser)
        .filter(AdminUser.clerk_user_id == clerk_user_id, AdminUser.is_active.is_(True))
        .first()
    )


def stamp_admin_porterchain_user_id(
    db: Session, clerk_user_id: str, user_id: str
) -> AdminUser | None:
    admin = get_admin_by_clerk(db, clerk_user_id)
    if not admin:
        # Staff IdP / rebind: find by internal FK when subject column lagged.
        admin = (
            db.query(AdminUser)
            .filter(AdminUser.porterchain_user_id == user_id, AdminUser.is_active.is_(True))
            .first()
        )
    if admin and admin.porterchain_user_id != user_id:
        admin.porterchain_user_id = user_id
    return admin


def get_admin_by_email(db: Session, email: str) -> AdminUser | None:
    return db.query(AdminUser).filter(AdminUser.email == email.lower().strip()).first()


def rebind_clerk_by_email(db: Session, email: str, clerk_id: str) -> bool:
    from porterchain_api.auth.email_identity import emails_match

    row = db.query(AdminUser).filter(AdminUser.email == email).first()
    if not row or not emails_match(getattr(row, "email", None), email):
        return False
    if row.clerk_user_id == clerk_id:
        return False
    taken = db.query(AdminUser).filter(AdminUser.clerk_user_id == clerk_id).first()
    if taken and taken.id != row.id:
        return False
    row.clerk_user_id = clerk_id
    return True


def ensure_local_super_admin(db: Session) -> AdminUser:
    """Provision or upgrade the local Super Admin (development-only callers).

    Always ``super_admin`` + active + Staff IdP subject ``staff:{id}``.
    Reuses legacy ``dev_clerk_user`` / founder email rows when present.
    """
    from porterchain_api.admin_engine.staff_idp_service import ensure_staff_identity

    email = LOCAL_SUPER_ADMIN_EMAIL
    user = (
        get_admin_by_email(db, email)
        or db.query(AdminUser)
        .filter(AdminUser.clerk_user_id == LOCAL_SUPER_ADMIN_LEGACY_SUBJECT)
        .first()
    )
    if user:
        user.email = email
        user.name = LOCAL_SUPER_ADMIN_NAME
        user.role = AdminRole.SUPER_ADMIN.value
        user.is_active = True
    else:
        user = AdminUser(
            clerk_user_id=f"pending:{email}",
            email=email,
            name=LOCAL_SUPER_ADMIN_NAME,
            role=AdminRole.SUPER_ADMIN.value,
            is_active=True,
        )
        db.add(user)
    db.flush()
    ensure_staff_identity(db, user)
    db.refresh(user)
    return user


def ensure_dev_admin(
    db: Session,
    clerk_user_id: str,
    clerk_email: str | None,
    role: str | None = None,
) -> AdminUser:
    """API Bearer-dev path — delegates to local Super Admin (role forced).

    ``role`` / ``clerk_user_id`` args kept for call-site compatibility; local
    Super Admin designation is not overridable to a weaker role.
    """
    _ = (clerk_user_id, clerk_email, role)
    return ensure_local_super_admin(db)
