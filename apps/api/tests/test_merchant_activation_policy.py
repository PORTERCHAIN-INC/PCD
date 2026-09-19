"""Merchant activation policy — who may book without an admin approving first."""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from porterchain_api.admin_models import SystemConfig
from porterchain_api.domain.merchant_states import MerchantStatus
from porterchain_api.merchant_engine.activation_service import (
    SIGNUP_SOURCE_PORTAL,
    SIGNUP_SOURCE_SHOPIFY,
    activate_merchant,
    apply_signup_policy,
    approval_required,
    is_trusted_source,
    resolve_initial_status,
    trusted_channels_auto_activate,
)
from porterchain_api.merchant_models import Merchant

_CONFIG_KEY = "settings_merchant"


def _set_merchant_config(db: Session, **values) -> None:
    row = db.query(SystemConfig).filter(SystemConfig.key == _CONFIG_KEY).first()
    if row is None:
        row = SystemConfig(key=_CONFIG_KEY, value={})
        db.add(row)
    row.value = {**(row.value or {}), **values}
    db.flush()


def _make_merchant(db: Session, *, status: str = MerchantStatus.ONBOARDING.value) -> Merchant:
    merchant = Merchant(
        status=status,
        company_name=f"Test Co {uuid4().hex[:6]}",
        email=f"{uuid4().hex[:10]}@example.com",
        payment_terms="NET_30",
    )
    db.add(merchant)
    db.flush()
    return merchant


def test_portal_signup_waits_for_admin_by_default(db: Session) -> None:
    _set_merchant_config(db, approval_required=True)
    status = resolve_initial_status(db, source=SIGNUP_SOURCE_PORTAL)
    assert status == MerchantStatus.ONBOARDING.value


def test_portal_signup_activates_when_approval_disabled(db: Session) -> None:
    _set_merchant_config(db, approval_required=False)
    status = resolve_initial_status(db, source=SIGNUP_SOURCE_PORTAL)
    assert status == MerchantStatus.ACTIVE.value


def test_shopify_install_bypasses_admin_approval(db: Session) -> None:
    """The whole point: a verified install must not stall on a human."""
    _set_merchant_config(db, approval_required=True, auto_activate_trusted_channels=True)
    status = resolve_initial_status(db, source=SIGNUP_SOURCE_SHOPIFY)
    assert status == MerchantStatus.ACTIVE.value


def test_trusted_channel_kill_switch(db: Session) -> None:
    _set_merchant_config(db, approval_required=True, auto_activate_trusted_channels=False)
    status = resolve_initial_status(db, source=SIGNUP_SOURCE_SHOPIFY)
    assert status == MerchantStatus.ONBOARDING.value


def test_unknown_source_is_untrusted(db: Session) -> None:
    _set_merchant_config(db, approval_required=True)
    assert is_trusted_source("something_made_up") is False
    assert resolve_initial_status(db, source=None) == MerchantStatus.ONBOARDING.value


def test_config_defaults_are_conservative(db: Session) -> None:
    db.query(SystemConfig).filter(SystemConfig.key == _CONFIG_KEY).delete()
    db.flush()
    assert approval_required(db) is True
    assert trusted_channels_auto_activate(db) is True


def test_activate_merchant_sets_active_and_timestamp(db: Session) -> None:
    merchant = _make_merchant(db)
    activate_merchant(db, merchant, source=SIGNUP_SOURCE_SHOPIFY, commit=False)
    assert merchant.status == MerchantStatus.ACTIVE.value
    assert merchant.activated_at is not None


def test_activate_merchant_is_idempotent(db: Session) -> None:
    merchant = _make_merchant(db, status=MerchantStatus.ACTIVE.value)
    activated_at = merchant.activated_at
    activate_merchant(db, merchant, source=SIGNUP_SOURCE_SHOPIFY, commit=False)
    assert merchant.activated_at == activated_at


def test_existing_onboarding_merchant_activates_when_policy_relaxes(db: Session) -> None:
    """A merchant stuck in ONBOARDING must not stay stuck after ops turns approval off."""
    merchant = _make_merchant(db)
    _set_merchant_config(db, approval_required=False)
    apply_signup_policy(db, merchant, source=SIGNUP_SOURCE_PORTAL)
    assert merchant.status == MerchantStatus.ACTIVE.value


def test_existing_pending_merchant_advances_to_onboarding(db: Session) -> None:
    merchant = _make_merchant(db, status=MerchantStatus.PENDING.value)
    _set_merchant_config(db, approval_required=True)
    apply_signup_policy(db, merchant, source=SIGNUP_SOURCE_PORTAL)
    assert merchant.status == MerchantStatus.ONBOARDING.value


def test_signup_policy_leaves_suspended_merchants_alone(db: Session) -> None:
    merchant = _make_merchant(db, status=MerchantStatus.SUSPENDED.value)
    _set_merchant_config(db, approval_required=False)
    apply_signup_policy(db, merchant, source=SIGNUP_SOURCE_PORTAL)
    assert merchant.status == MerchantStatus.SUSPENDED.value


def test_integration_cannot_undo_a_suspension(db: Session) -> None:
    merchant = _make_merchant(db, status=MerchantStatus.SUSPENDED.value)
    with pytest.raises(PermissionError, match="merchant_suspended"):
        activate_merchant(db, merchant, source=SIGNUP_SOURCE_SHOPIFY, commit=False)
    assert merchant.status == MerchantStatus.SUSPENDED.value
