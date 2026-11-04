"""Staff PorterchainUser registry writes owned by auth."""

from __future__ import annotations

from sqlalchemy.orm import Session

from porterchain_api.user_models import PorterchainUser


def get_porterchain_user(db: Session, user_id: str | None) -> PorterchainUser | None:
    if not user_id:
        return None
    return db.get(PorterchainUser, user_id)


def ensure_staff_porterchain_user(
    db: Session,
    *,
    subject_key: str,
    email: str | None,
    linked_user_id: str | None = None,
    legacy_idp_user_id: str | None = None,
) -> PorterchainUser:
    """Find or create the staff:{admin_id} registry row. Caller stamps AdminUser + commits."""
    by_subject = (
        db.query(PorterchainUser)
        .filter(PorterchainUser.auth_subject == subject_key)
        .first()
    )
    linked = (
        db.query(PorterchainUser).filter(PorterchainUser.id == linked_user_id).first()
        if linked_user_id
        else None
    )
    legacy_idp = None
    if legacy_idp_user_id:
        legacy_idp = (
            db.query(PorterchainUser)
            .filter(PorterchainUser.auth_subject == legacy_idp_user_id)
            .first()
        )

    pc = by_subject or linked or legacy_idp
    if not pc:
        pc = PorterchainUser(
            auth_subject=subject_key,
            email=email,
            role="admin",
            status="active",
            onboarding_status="complete",
            default_workspace="admin",
        )
        db.add(pc)
        db.flush()
        return pc

    if pc.auth_subject != subject_key:
        conflict = (
            db.query(PorterchainUser)
            .filter(
                PorterchainUser.auth_subject == subject_key,
                PorterchainUser.id != pc.id,
            )
            .first()
        )
        if conflict is not None:
            pc = conflict
        else:
            pc.auth_subject = subject_key
    pc.email = email or pc.email
    pc.status = "active"
    pc.role = "admin"
    pc.default_workspace = "admin"
    db.flush()
    return pc
