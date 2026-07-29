"""Clerk verified email ↔ system profile email identity rules.

Rule: every provisioned profile (admin / merchant / driver / customer) bound to a
Clerk subject must store the same normalized email as Clerk's verified primary
email. Clerk id alone is never enough when emails disagree.

Mismatched persona rows are hard-deleted — never left as pending links.
"""

from __future__ import annotations

import logging

from sqlalchemy import or_
from sqlalchemy.orm import Session

from porterchain_api.admin_models import AdminUser, Driver
from porterchain_api.identity_models import IdentityLink
from porterchain_api.merchant_models import MerchantUser
from porterchain_api.models import Customer
from porterchain_api.unified_identity_models import UserEmail
from porterchain_api.user_models import PorterchainUser

logger = logging.getLogger("porterchain.security")

EMAIL_CLERK_MISMATCH = "email_clerk_mismatch"


def normalize_email(email: str | None) -> str | None:
    if not email:
        return None
    cleaned = email.strip().lower()
    return cleaned or None


def emails_match(system_email: str | None, clerk_email: str | None) -> bool:
    left = normalize_email(system_email)
    right = normalize_email(clerk_email)
    if not left or not right:
        return False
    return left == right


def require_system_email_matches_clerk(
    system_email: str | None,
    clerk_email: str | None,
    *,
    detail: str = EMAIL_CLERK_MISMATCH,
) -> None:
    """Raise PermissionError when system email ≠ Clerk verified email."""
    if not emails_match(system_email, clerk_email):
        raise PermissionError(detail)


def delete_email_mismatched_bindings(
    db: Session,
    *,
    clerk_user_id: str,
    clerk_email: str | None,
) -> int:
    """Hard-delete persona rows where clerk_user_id is bound to a different email.

    Returns the number of persona rows deleted. Safe to call on every auth sync.
    Does nothing when Clerk email is missing (cannot verify match).
    """
    expected = normalize_email(clerk_email)
    if not expected or not clerk_user_id or clerk_user_id == "dev_clerk_user":
        return 0
    if clerk_user_id.startswith("pending:") or clerk_user_id.startswith("pending_"):
        return 0

    deleted = 0
    for model in (AdminUser, MerchantUser, Driver, Customer):
        rows = db.query(model).filter(model.clerk_user_id == clerk_user_id).all()
        for row in rows:
            row_email = normalize_email(getattr(row, "email", None))
            if row_email and row_email == expected:
                continue
            logger.warning(
                "email_clerk_mismatch_deleted",
                extra={
                    "model": model.__tablename__,
                    "row_id": getattr(row, "id", None),
                    "system_email": row_email,
                    "clerk_email": expected,
                },
            )
            db.delete(row)
            deleted += 1

    if deleted:
        _strip_registry_if_no_matching_persona(db, clerk_user_id=clerk_user_id, clerk_email=expected)

    return deleted


# Back-compat alias used by sync/ensure call sites
unlink_email_mismatched_bindings = delete_email_mismatched_bindings


def _strip_registry_if_no_matching_persona(
    db: Session,
    *,
    clerk_user_id: str,
    clerk_email: str,
) -> None:
    """If mismatch deletes removed all personas, drop elevated registry identity for that clerk id."""
    still_bound = False
    for model in (AdminUser, MerchantUser, Driver, Customer):
        row = db.query(model).filter(model.clerk_user_id == clerk_user_id).first()
        if row and emails_match(getattr(row, "email", None), clerk_email):
            still_bound = True
            break
    if still_bound:
        return

    user = db.query(PorterchainUser).filter(PorterchainUser.clerk_user_id == clerk_user_id).first()
    if not user:
        return
    # Registry email must equal Clerk; if it already matches and has no personas, leave as unprovisioned.
    if emails_match(user.email, clerk_email):
        user.role = "unprovisioned"
        return

    # Hard-delete registry identity that itself carried a mismatched email
    logger.warning(
        "email_clerk_mismatch_registry_deleted",
        extra={"user_id": user.id, "system_email": user.email, "clerk_email": clerk_email},
    )
    db.query(UserEmail).filter(UserEmail.user_id == user.id).delete(synchronize_session=False)
    db.query(IdentityLink).filter(
        or_(IdentityLink.platform_user_id == user.id, IdentityLink.clerk_user_id == clerk_user_id)
    ).delete(synchronize_session=False)
    db.delete(user)
