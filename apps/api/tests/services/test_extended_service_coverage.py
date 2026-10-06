"""Additional admin/billing/auth service coverage (§2.1.11)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from unittest.mock import patch

from porterchain_api.admin_engine.booking_draft_admin_service import (
    AdminBookingDraftService,
    AdminDraftFilters,
)
from porterchain_api.admin_engine.dashboard_service import AdminDashboardService
from porterchain_api.admin_engine.driver360_service import Driver360Service
from porterchain_api.admin_engine.driver_service import AdminDriverService
from porterchain_api.admin_engine.merchant_service import AdminMerchantService
from porterchain_api.billing_engine import merchant_service as billing_merchant
from porterchain_api.billing_engine.driver_finance_service import DriverFinanceService
from porterchain_api.booking_engine.booking_draft_service import BookingDraftService
from porterchain_api.collaboration_engine.crm_service import CrmSalesService
from porterchain_api.merchant_engine.booking_validation import MerchantSyncService
from porterchain_api.platform.retired_sync import WebhookIngressService
from porterchain_api.merchant_engine.tracking_service import MerchantTrackingService
from porterchain_api.notification_engine.fcm_service import FCMService, firebase_sdk_available
from porterchain_api.booking_models import Invoice


def test_admin_dashboard_center(db, settings, admin_ctx) -> None:
    center = AdminDashboardService().get_center(db, settings, role=admin_ctx.role.value)
    assert "kpis" in center
    assert "operations" in center
    assert "crm" in center
    assert "new_leads" in center["crm"]
    assert "growth_percent" in center["executive"]
    assert "delivery_sla_percent" in center["executive"]
    assert "forecast_revenue_cents" in center["executive"]
    assert "ai_summary" in center["smart"]
    assert isinstance(center["smart"].get("anomalies"), list)
    assert "top_by_revenue" in center["merchants"]
    assert "top_by_orders" in center["merchants"]
    assert center["kpis"]["fleet_health_percent"] <= 100.0


def test_admin_drivers_and_merchants(db, driver) -> None:
    drivers = AdminDriverService()
    assert isinstance(drivers.list_drivers(db), list)
    assert drivers.get_driver(db, driver.id) is not None
    assert isinstance(drivers.list_payouts(db, driver.id), list)
    assert isinstance(drivers.list_vehicles(db, driver.id), list)
    merchants = AdminMerchantService()
    assert isinstance(merchants.list_merchants(db, limit=10), list)


def test_driver360_detail(db, driver) -> None:
    svc = Driver360Service()
    detail = svc.detail(db, driver.id)
    assert detail is not None
    assert isinstance(svc.analytics(db, driver.id), dict)
    assert isinstance(svc.documents(db, driver.id), dict)
    page = svc.orders(db, driver.id, limit=5)
    assert isinstance(page, dict)
    assert isinstance(page["items"], list)
    assert page["limit"] == 5


def test_booking_draft_admin_paths(db) -> None:
    svc = AdminBookingDraftService()
    assert isinstance(svc.list_drafts(db, AdminDraftFilters(limit=10)), list)
    assert isinstance(svc.analytics(db), dict)
    assert isinstance(svc.abandoned(db, limit=5), list)


def test_booking_draft_service_lookup(db) -> None:
    svc = BookingDraftService()
    assert svc.get_by_id(db, "missing-id") is None
    assert svc.get_by_quote_id(db, "missing-quote") is None


def test_crm_sales_dashboard(db) -> None:
    crm = CrmSalesService()
    assert isinstance(crm.dashboard(db), dict)
    assert isinstance(crm.list_leads(db, limit=5), list)
    assert isinstance(crm.list_companies(db, limit=5), list)


def test_billing_helpers_and_driver_finance(db, merchant_ctx, driver) -> None:
    assert billing_merchant.net_terms_days("NET_30") == 30
    inv = Invoice(
        invoice_number="INV-TEST",
        amount_cents=1000,
        tax_cents=130,
        fees_cents=0,
        currency="cad",
        created_at=datetime.now(UTC),
    )
    assert billing_merchant.invoice_status(inv, None, None) in ("sent", "overdue")
    fin = DriverFinanceService()
    assert isinstance(fin.driver_earnings_snapshot(db, driver), dict)
    assert isinstance(fin.list_statements(db, driver.id, months=3), list)


def test_merchant_sync_validate(db, merchant_ctx) -> None:
    merchant_ctx.merchant.payment_terms = "NET_30"
    db.commit()
    result = MerchantSyncService().validate_booking(db, merchant_ctx.merchant, amount_cents=1000)
    assert result.payment_terms == "NET_30"


@patch("porterchain_api.platform.retired_sync.get_fleetbase_integration")
def test_webhook_ingress_disabled(mock_integration, db, settings) -> None:
    settings.fleetbase_dispatch_bridge = False
    result = WebhookIngressService().accept(
        db, settings, raw_body=b"{}", signature=None
    )
    assert result["status"] == "ignored"


def test_merchant_tracking_by_number(db, settings, merchant_ctx, dispatch_order) -> None:
    svc = MerchantTrackingService()
    snap = svc.track_by_number(db, settings, merchant_ctx, dispatch_order.tracking_number)
    assert snap is not None


def test_fcm_module_helpers() -> None:
    assert isinstance(firebase_sdk_available(), bool)
    assert FCMService() is not None
