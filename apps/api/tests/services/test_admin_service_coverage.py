"""Admin *_service.py integration coverage (§2.1.11)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import patch
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from porterchain_api.admin_engine.dashboard_service import AdminDashboardService, _chart_trends
from porterchain_api.admin_engine.finance_service import AdminFinanceService, FinanceFilters
from porterchain_api.admin_engine.merchant360_service import Merchant360Service
from porterchain_api.admin_engine.operations_service import AdminOperationsService
from porterchain_api.admin_engine.orders_service import AdminOrdersService
from porterchain_api.admin_engine.pricing_service import AdminPricingService
from porterchain_api.admin_engine.settings_service import AdminSettingsService
from porterchain_api.admin_engine.control_tower_service import ControlTowerService
from porterchain_api.admin_engine.notification_admin_service import NotificationAdminService
from porterchain_api.admin_engine.rbac import AdminContext
from porterchain_api.domain.states import OrderState
from porterchain_api.merchant_models import Merchant
from porterchain_api.models import Order


def test_chart_trends_normalizes_dict_shape() -> None:
    out = _chart_trends(None, {"labels": ["Mon"], "orders": [2], "revenue_cents": [100]})
    assert out["labels"] == ["Mon"]
    assert out["orders"] == [2]
    assert out["revenue_cents"] == [100]


def test_admin_dashboard_empty_db(db: Session) -> None:
    result = AdminDashboardService().get_dashboard(db)
    assert "todays_bookings" in result
    assert isinstance(result["todays_bookings"], int)


def test_admin_settings_read_paths(db: Session, settings) -> None:
    svc = AdminSettingsService()
    assert svc.permissions_matrix()
    assert isinstance(svc.search("stripe"), list)
    assert isinstance(svc.default_config(db), dict)
    assert isinstance(svc.module_config_links(db), dict)
    assert isinstance(svc.vehicles_overview(db), dict)
    assert isinstance(svc.integration_health(db, settings), dict)
    assert isinstance(svc.dashboard(db, settings), dict)
    assert isinstance(svc.center(db, settings), dict)
    assert isinstance(svc.validate(settings, db), dict)
    assert isinstance(svc.export_configuration(db), dict)
    assert isinstance(svc.list_staff(db), list)
    assert isinstance(svc.recent_audit(db, limit=5), list)
    assert isinstance(svc.audit_log(db, limit=5), list)


@patch("porterchain_api.admin_engine.settings_service.fetch_clerk_snapshots", return_value=[])
def test_admin_settings_platform_users(_mock_clerk, db: Session, settings) -> None:
    svc = AdminSettingsService()
    resp = svc.list_platform_users(db, settings, "staff", limit=10)
    assert resp.total >= 0
    assert isinstance(resp.items, list)


def test_admin_finance_read_paths(db: Session, admin_ctx: AdminContext) -> None:
    svc = AdminFinanceService()
    assert isinstance(svc.revenue_summary(db), dict)
    assert isinstance(svc.dashboard(db), dict)
    assert isinstance(svc.list_invoices(db), list)
    assert isinstance(svc.list_invoices_enriched(db, FinanceFilters(limit=10)), list)
    assert isinstance(svc.list_payments(db), list)
    assert isinstance(svc.list_payments_enriched(db, FinanceFilters(limit=10)), list)
    assert isinstance(svc.list_payouts_enriched(db), list)
    assert isinstance(svc.list_ledger(db, limit=10), list)
    assert isinstance(svc.collections(db), list)
    assert isinstance(svc.reports(db), dict)
    assert isinstance(svc.export_gl(db), list)
    assert isinstance(svc.find_duplicate_payments(db), list)


def test_admin_merchant360_read_paths(db: Session, settings, merchant_ctx) -> None:
    svc = Merchant360Service()
    assert isinstance(svc.list_merchants(db, limit=10), list)
    assert isinstance(svc.facets(db), dict)
    assert isinstance(svc.stats(db), dict)
    detail = svc.detail(db, merchant_ctx.merchant.id)
    assert detail is not None
    assert isinstance(svc.orders(db, merchant_ctx.merchant.id, limit=10), list)
    assert isinstance(svc.locations(db, merchant_ctx.merchant.id), dict)
    assert isinstance(svc.team(db, merchant_ctx.merchant.id), list)
    assert isinstance(svc.onboarding(db, merchant_ctx.merchant.id), dict)
    assert isinstance(svc.api_keys(db, merchant_ctx.merchant.id), dict)
    assert isinstance(svc.analytics(db, merchant_ctx.merchant.id), dict)
    assert isinstance(svc.unprovisioned_signups(db, settings), list)


def test_admin_operations_assign_and_queues(
    db: Session,
    settings,
    admin_ctx: AdminContext,
    dispatch_order: Order,
    driver,
) -> None:
    svc = AdminOperationsService()
    db.refresh(dispatch_order)
    assert dispatch_order.state == OrderState.DISPATCH_READY.value
    assigned = svc.assign_driver(db, settings, admin_ctx, dispatch_order.id, driver.id)
    assert assigned.state == OrderState.DRIVER_ASSIGNED.value


def test_admin_orders_force_transition_and_bulk(
    db: Session,
    settings,
    admin_ctx: AdminContext,
    dispatch_order: Order,
    driver,
) -> None:
    svc = AdminOrdersService()
    cancelled = svc.force_transition(db, admin_ctx, dispatch_order.id, OrderState.CANCELLED.value)
    assert cancelled.state == OrderState.CANCELLED.value
    results = svc.bulk_action(db, settings, admin_ctx, [dispatch_order.id], "cancel")
    assert results[0]["status"] == "cancelled"


def test_admin_pricing_and_control_tower(db: Session) -> None:
    pricing = AdminPricingService()
    assert isinstance(pricing.dashboard(db), dict)
    assert isinstance(pricing.list_tariffs(db), list)
    tower = ControlTowerService()
    assert isinstance(tower.stats(db), dict)
    assert isinstance(tower.board(db), list)


def test_notification_admin_dashboard(db: Session) -> None:
    svc = NotificationAdminService()
    assert isinstance(svc.dashboard(db), dict)
    assert isinstance(svc.list_records(db, limit=5), list)
