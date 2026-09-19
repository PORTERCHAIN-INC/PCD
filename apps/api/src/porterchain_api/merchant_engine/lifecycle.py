"""Merchant close / access revocation — org row writes owned here."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.domain.merchant_states import MerchantStatus
from porterchain_api.merchant_models import (
    Merchant,
    MerchantApiKey,
    MerchantUser,
    MerchantWebhook,
    StandingOrder,
)


def set_status(
    merchant: Merchant,
    status: str,
    *,
    activated_at: datetime | None = None,
) -> Merchant:
    merchant.status = status
    if activated_at is not None:
        merchant.activated_at = activated_at
    return merchant


def merge_profile(merchant: Merchant, patch: dict[str, Any]) -> Merchant:
    merchant.profile = {**(merchant.profile or {}), **patch}
    return merchant


def deactivate_access(db: Session, merchant: Merchant) -> None:
    """Revoke portal seats, keys, webhooks, and standing orders. Last-owner guard does not apply."""
    for user in db.query(MerchantUser).filter(MerchantUser.merchant_id == merchant.id).all():
        user.is_active = False
    for key in db.query(MerchantApiKey).filter(MerchantApiKey.merchant_id == merchant.id).all():
        key.is_active = False
    for hook in db.query(MerchantWebhook).filter(MerchantWebhook.merchant_id == merchant.id).all():
        hook.is_active = False
    for standing in db.query(StandingOrder).filter(StandingOrder.merchant_id == merchant.id).all():
        standing.is_active = False


def apply_closed(
    db: Session,
    merchant: Merchant,
    *,
    reason: str,
    actor_id: str,
    extra: dict[str, Any] | None = None,
) -> Merchant:
    merchant.status = MerchantStatus.CLOSED.value
    profile = dict(merchant.profile or {})
    profile["closed"] = {
        "at": datetime.now(UTC).isoformat(),
        "reason": reason,
        "actor_id": actor_id,
        **(extra or {}),
    }
    merchant.profile = profile
    deactivate_access(db, merchant)
    return merchant
