"""
Merchant activation policy — who may start booking without an admin.

`get_merchant_context` refuses every `/v1/merchant/*` call unless the merchant is
ACTIVE, so this module owns the single decision of when that happens. Ops keeps
two switches in the `settings_merchant` SystemConfig row:

- ``approval_required`` (default on) — a stranger signing into the portal waits
  for a human, because activation extends payment terms.
- ``auto_activate_trusted_channels`` (default on) — a channel that authenticated
  the merchant for us, such as a verified Shopify OAuth install, skips that wait.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.domain.merchant_states import MerchantStatus
from porterchain_api.merchant_models import Merchant

logger = logging.getLogger(__name__)

SIGNUP_SOURCE_PORTAL = "merchant_portal_signin"
SIGNUP_SOURCE_SHOPIFY = "shopify_oauth_install"

#: Sources where an external party has already proven the merchant's identity.
#: A Shopify install arrives with a shop domain Shopify itself authenticated;
#: a portal sign-in proves only that someone owns an email address.
TRUSTED_SIGNUP_SOURCES = frozenset({SIGNUP_SOURCE_SHOPIFY})

_CONFIG_KEY = "settings_merchant"


def _merchant_config(db: Session) -> dict[str, Any]:
    from porterchain_api.merchant_engine.config_read import config_dict

    return config_dict(db, _CONFIG_KEY)


def approval_required(db: Session) -> bool:
    return bool(_merchant_config(db).get("approval_required", True))


def trusted_channels_auto_activate(db: Session) -> bool:
    return bool(_merchant_config(db).get("auto_activate_trusted_channels", True))


def is_trusted_source(source: str | None) -> bool:
    return (source or "") in TRUSTED_SIGNUP_SOURCES


def resolve_initial_status(db: Session, *, source: str | None) -> str:
    """Status a brand-new merchant should be created with."""
    if is_trusted_source(source):
        if trusted_channels_auto_activate(db):
            return MerchantStatus.ACTIVE.value
        return MerchantStatus.ONBOARDING.value
    if approval_required(db):
        return MerchantStatus.ONBOARDING.value
    return MerchantStatus.ACTIVE.value


def apply_signup_policy(db: Session, merchant: Merchant, *, source: str) -> Merchant:
    """
    Bring an already-created, not-yet-active merchant in line with current policy.

    Without this a merchant who signed up while approval was required would stay
    stuck in ONBOARDING after ops turned approval off, or after they later
    installed a trusted integration.
    """
    if merchant.status not in (MerchantStatus.PENDING.value, MerchantStatus.ONBOARDING.value):
        return merchant
    if resolve_initial_status(db, source=source) == MerchantStatus.ACTIVE.value:
        return activate_merchant(db, merchant, source=source, commit=False)
    if merchant.status == MerchantStatus.PENDING.value:
        merchant.status = MerchantStatus.ONBOARDING.value
    return merchant


def activate_merchant(
    db: Session,
    merchant: Merchant,
    *,
    source: str,
    commit: bool = True,
) -> Merchant:
    """
    Activate without an admin actor, matching `AdminMerchantService.approve_merchant`.

    Kept in step with that method deliberately: the CRM company flag and the
    authz sync are what make a merchant genuinely bookable, and an auto-activated
    merchant that skipped them would fail in confusing ways later.
    """
    if merchant.status == MerchantStatus.ACTIVE.value:
        return merchant
    if merchant.status == MerchantStatus.SUSPENDED.value:
        # Never let an integration silently undo an ops suspension.
        raise PermissionError("merchant_suspended")

    from porterchain_api.booking_engine._core import emit_event
    from porterchain_api.collaboration_engine.crm_service import CrmSalesService
    from porterchain_api.domain.crm_states import CompanyMerchantStatus
    from porterchain_api.merchant_engine import events as E

    merchant.status = MerchantStatus.ACTIVE.value
    merchant.activated_at = datetime.now(UTC)

    CrmSalesService().set_merchant_status(
        db, merchant.id, CompanyMerchantStatus.ACTIVE_MERCHANT.value
    )

    emit_event(
        db,
        event_type=E.MERCHANT_APPROVED,
        aggregate_type="merchant",
        aggregate_id=merchant.id,
        actor_type="system",
        payload={
            "merchant_id": merchant.id,
            "company_name": merchant.company_name,
            "auto_activated": True,
            "source": source,
        },
    )

    if commit:
        db.commit()
        db.refresh(merchant)

    _sync_authz(db, merchant.id)
    logger.info("merchant_auto_activated merchant_id=%s source=%s", merchant.id, source)
    return merchant


def _sync_authz(db: Session, merchant_id: str) -> None:
    from porterchain_api.auth.authz_sync import sync_authz_after_persona_mutation
    from porterchain_api.merchant_models import MerchantUser

    rows = db.query(MerchantUser).filter(MerchantUser.merchant_id == merchant_id).all()
    for row in rows:
        if not row.clerk_user_id:
            continue
        try:
            sync_authz_after_persona_mutation(db, row.clerk_user_id)
        except Exception:  # noqa: BLE001 — authz sync must not block activation
            logger.warning("merchant_activation_authz_sync_failed user=%s", row.clerk_user_id)
