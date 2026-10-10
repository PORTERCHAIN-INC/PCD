"""Merchant *_service.py integration coverage (§2.1.11)."""

from __future__ import annotations

from porterchain_api.merchant_engine.billing_service import MerchantBillingService
from porterchain_api.merchant_engine.contacts_service import MerchantContactsService
from porterchain_api.merchant_engine.dashboard_service import MerchantDashboardService
from porterchain_api.merchant_engine.integrations_service import MerchantIntegrationsService
from porterchain_api.merchant_engine.orders_service import MerchantOrdersService
from porterchain_api.merchant_engine.profile_service import MerchantProfileService
from porterchain_api.merchant_engine.reports_service import MerchantReportsService
from porterchain_api.merchant_engine.settings_service import MerchantSettingsService
from porterchain_api.merchant_engine.team_service import MerchantTeamService
from porterchain_api.merchant_engine.template_service import MerchantTemplateService
from porterchain_api.merchant_engine.tracking_service import MerchantTrackingService
from porterchain_api.merchant_engine.api_key_service import MerchantApiKeyService
from porterchain_api.schemas_merchant import MerchantProfileUpdateRequest


def test_merchant_dashboard(db, merchant_ctx) -> None:
    result = MerchantDashboardService().get_dashboard(db, merchant_ctx)
    assert "todays_orders" in result
    assert result["todays_orders"] == 0


def test_merchant_profile_and_addresses(db, merchant_ctx) -> None:
    svc = MerchantProfileService()
    assert svc.get_profile(merchant_ctx).id == merchant_ctx.merchant.id
    assert svc.list_saved_addresses(db, merchant_ctx) == []
    assert svc.list_recipients(db, merchant_ctx) == []
    addr = svc.create_saved_address(
        db,
        merchant_ctx,
        label="HQ",
        address_type="pickup",
        formatted="100 King St W, Toronto",
        is_default=True,
    )
    assert addr.is_default is True
    recipient = svc.create_recipient(db, merchant_ctx, name="Jane Doe", email="jane@example.com")
    assert recipient.name == "Jane Doe"
    updated = svc.update_profile(
        db,
        merchant_ctx,
        MerchantProfileUpdateRequest(company_name="Updated Co"),
    )
    assert updated.company_name == "Updated Co"


def test_merchant_team_and_settings(db, merchant_ctx) -> None:
    team = MerchantTeamService()
    assert len(team.list_members(db, merchant_ctx)) >= 1
    overview = team.overview(db, merchant_ctx)
    assert overview["member_count"] >= 1
    assert isinstance(team.roles_and_permissions(), dict)
    settings_svc = MerchantSettingsService()
    assert isinstance(settings_svc.overview(db, merchant_ctx), dict)
    assert isinstance(settings_svc.tax_info(merchant_ctx), dict)


def test_merchant_orders_reports_billing(db, merchant_ctx) -> None:
    orders = MerchantOrdersService()
    assert isinstance(orders.list_orders(db, merchant_ctx, limit=10), list)
    reports = MerchantReportsService()
    assert isinstance(reports.summary(db, merchant_ctx), dict)
    billing = MerchantBillingService()
    assert isinstance(billing.statement_summary(db, merchant_ctx), dict)


def test_merchant_integrations_and_api_keys(db, merchant_ctx, settings) -> None:
    integrations = MerchantIntegrationsService()
    assert isinstance(integrations.overview(db, merchant_ctx, api_base_url="http://localhost:8001"), dict)
    api_keys = MerchantApiKeyService()
    assert isinstance(api_keys.list_keys(db, merchant_ctx), list)


def test_merchant_contacts_templates_tracking(db, merchant_ctx, settings) -> None:
    contacts = MerchantContactsService()
    assert isinstance(contacts.list_contacts(db, merchant_ctx), list)
    templates = MerchantTemplateService()
    assert isinstance(templates.list_templates(db, merchant_ctx), list)
    tracking = MerchantTrackingService()
    assert isinstance(tracking.dashboard(db, settings, merchant_ctx), dict)
