"""Merchant inbox is company-scoped via X-Merchant-Id, not Clerk orgs."""

from __future__ import annotations

from uuid import uuid4

from porterchain_api.config import Settings
from porterchain_api.domain.merchant_states import MerchantRole, MerchantStatus
from porterchain_api.merchant_engine.rbac import MerchantContext
from porterchain_api.merchant_engine.settings_service import MerchantSettingsService
from porterchain_api.merchant_models import Merchant, MerchantUser
from porterchain_api.notification_engine.engine import get_notification_engine
from porterchain_api.notification_engine.models import NotificationRecord
from porterchain_api.notification_engine.principal import _resolve_merchant_recipient
from porterchain_api.notification_engine.user_settings import UserSettingsService


def _seat(db, *, clerk_id: str, company: str, status: str = MerchantStatus.ACTIVE.value) -> Merchant:
    merchant = Merchant(
        company_name=company,
        email=f"{uuid4().hex[:8]}@inbox.test",
        status=status,
        clerk_org_id=f"org_{uuid4().hex[:8]}",
    )
    db.add(merchant)
    db.flush()
    db.add(
        MerchantUser(
            merchant_id=merchant.id,
            clerk_user_id=clerk_id,
            email=f"{clerk_id}@inbox.test",
            role=MerchantRole.OWNER.value,
            is_active=True,
        )
    )
    db.flush()
    return merchant


def test_inbox_follows_x_merchant_id_not_clerk_org(db):
    clerk = f"user_{uuid4().hex[:10]}"
    first = _seat(db, clerk_id=clerk, company="North Co")
    second = _seat(db, clerk_id=clerk, company="South Co")
    settings = Settings(app_env="local", clerk_dev_bypass=False)

    db.add(
        NotificationRecord(
            template_key="tracking_update",
            category="tracking",
            channel="in_app",
            recipient_type="merchant",
            recipient_id=first.id,
            title="North booked",
            body="North only",
            status="sent",
        )
    )
    db.add(
        NotificationRecord(
            template_key="tracking_update",
            category="tracking",
            channel="in_app",
            recipient_type="merchant",
            recipient_id=second.id,
            title="South booked",
            body="South only",
            status="sent",
        )
    )
    db.flush()

    north = _resolve_merchant_recipient(db, settings, clerk, first.id)
    south = _resolve_merchant_recipient(db, settings, clerk, second.id)
    assert north is not None and north.user_id == first.id
    assert south is not None and south.user_id == second.id

    engine = get_notification_engine()
    north_box = engine.inbox_payload(db, user_role="merchant", user_id=north.user_id, limit=20)
    south_box = engine.inbox_payload(db, user_role="merchant", user_id=south.user_id, limit=20)
    assert {item["title"] for item in north_box["items"]} == {"North booked"}
    assert {item["title"] for item in south_box["items"]} == {"South booked"}

    # Clerk Organization id is not a company selector.
    assert _resolve_merchant_recipient(db, settings, clerk, first.clerk_org_id) is None
    assert _resolve_merchant_recipient(db, settings, clerk, "org_someone_else") is None


def test_onboarding_merchant_can_open_inbox(db):
    clerk = f"user_{uuid4().hex[:10]}"
    merchant = _seat(db, clerk_id=clerk, company="Onboarding Co", status=MerchantStatus.ONBOARDING.value)
    settings = Settings(app_env="local", clerk_dev_bypass=False)
    user = _resolve_merchant_recipient(db, settings, clerk, merchant.id)
    assert user is not None
    assert user.user_id == merchant.id


def test_settings_overview_includes_quiet_hours(db):
    clerk = f"user_{uuid4().hex[:10]}"
    merchant = _seat(db, clerk_id=clerk, company="Quiet Co")
    user = (
        db.query(MerchantUser)
        .filter(MerchantUser.merchant_id == merchant.id, MerchantUser.clerk_user_id == clerk)
        .one()
    )
    ctx = MerchantContext(merchant=merchant, user=user, role=MerchantRole.OWNER)
    overview = MerchantSettingsService().overview(db, ctx)
    assert overview["quiet_hours"]["timezone"] == "America/Toronto"
    assert overview["quiet_hours"]["quiet_hours_enabled"] is False

    UserSettingsService().upsert(
        db,
        user_role="merchant",
        user_id=merchant.id,
        quiet_hours_enabled=True,
        quiet_start_hour=21,
        quiet_end_hour=6,
        timezone="America/Toronto",
    )
    db.flush()
    again = MerchantSettingsService().overview(db, ctx)
    assert again["quiet_hours"]["quiet_hours_enabled"] is True
    assert again["quiet_hours"]["quiet_start_hour"] == 21
