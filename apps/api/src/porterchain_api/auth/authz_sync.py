"""Post-mutation SpiceDB + cache sync after persona rows change mid-request."""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from porterchain_api.auth.account_lifecycle import activate_user_for_clerk
from porterchain_api.auth.persona_bundle import invalidate_persona_bundle
from porterchain_api.auth.prepare import invalidate_auth_prepare

logger = logging.getLogger("porterchain.security")


def sync_authz_after_persona_mutation(db: Session, clerk_user_id: str | None) -> None:
    """Invalidate caches, activate pending registry user, push SpiceDB tuples.

    Call after creating/linking AdminUser, MerchantUser, Driver, or Customer rows
    so same-request Checks (organization#portal, profile#access) see fresh tuples.
    """
    if not clerk_user_id or clerk_user_id == "dev_clerk_user":
        return
    # pending: seats have no SpiceDB subject yet; staff:{admin_id} is a real IdP subject.
    if clerk_user_id.startswith("pending:"):
        return

    invalidate_persona_bundle(db, clerk_user_id)
    invalidate_auth_prepare(db, clerk_user_id)

    user = activate_user_for_clerk(db, clerk_user_id)
    if not user:
        return

    try:
        from porterchain_api.auth.principal_cache import cache_invalidate

        cache_invalidate(user.id)
    except Exception:  # noqa: BLE001
        logger.debug("authz_sync_principal_cache_invalidate_failed", exc_info=True)

    try:
        from porterchain_api.authz.tuples import TupleWriter

        TupleWriter().sync_user_from_profiles(db, user)
    except Exception:  # noqa: BLE001
        logger.exception("authz_sync_after_persona_mutation_failed clerk_subject_present=1")
