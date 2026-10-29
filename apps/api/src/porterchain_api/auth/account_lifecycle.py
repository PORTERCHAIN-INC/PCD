"""Shared account activation helpers — single place for pending→active flips.

Approve/authorize routes keep role-specific side effects (org ACTIVE);
this module owns the porterchain_users status transition used after persona
provisioning so login prepare and admin authorize do not diverge.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from porterchain_api.auth.unified_catalog import AccountStatus
from porterchain_api.user_models import PorterchainUser


def activate_pending_user(user: PorterchainUser) -> bool:
    """Flip pending → active. Returns True when status changed."""
    if user.status == AccountStatus.PENDING.value:
        user.status = AccountStatus.ACTIVE.value
        return True
    return False


def activate_user_for_clerk(db: Session, auth_subject: str | None) -> PorterchainUser | None:
    """Activate the registry user bound to a Clerk subject (if present)."""
    if not auth_subject or auth_subject.startswith("pending:"):
        return None
    user = db.query(PorterchainUser).filter(PorterchainUser.auth_subject == auth_subject).first()
    if not user:
        return None
    activate_pending_user(user)
    return user
