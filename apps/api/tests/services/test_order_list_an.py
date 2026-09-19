"""AN — paginated order lists and capped admin dumps."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from porterchain_api.admin_engine.driver360_service import Driver360Service
from porterchain_api.admin_engine.finance_service import AdminFinanceService, FinanceFilters
from porterchain_api.admin_engine.merchant360_service import Merchant360Service
from porterchain_api.booking_engine.numbers import generate_order_number, generate_tracking_number
from porterchain_api.domain.states import OrderState
from porterchain_api.merchant_engine.orders_service import MerchantOrderFilters, MerchantOrdersService
from porterchain_api.booking_models import Order
from porterchain_api.order_engine.filters import OrderFilters
from porterchain_api.order_engine.platform_service import OrderPlatformService
from porterchain_api.platform.pagination import DEFAULT_PAGE_SIZE, MAX_LIST_LIMIT


def _order(
    merchant_id: str,
    *,
    amount_cents: int = 1500,
    city: str | None = None,
) -> Order:
    place = city or "Toronto"
    pickup = {"formatted": f"1 King St W, {place}", "city": place}
    return Order(
        order_number=generate_order_number(),
        tracking_number=generate_tracking_number(),
        state=OrderState.BOOKED.value,
        merchant_id=merchant_id,
        amount_cents=amount_cents,
        currency="cad",
        pickup=pickup,
        dropoff={"formatted": "200 Bay St, Toronto", "city": "Toronto"},
        scheduled_at=datetime.now(UTC),
    )


def test_order_pages_are_disjoint_and_total_stable(db, merchant_ctx) -> None:
    base = datetime.now(UTC)
    rows = []
    for i in range(3):
        order = _order(merchant_ctx.merchant.id)
        db.add(order)
        db.flush()
        order.updated_at = base + timedelta(seconds=i)
        rows.append(order)
    db.commit()

    svc = MerchantOrdersService()
    first = svc.list_page(db, merchant_ctx, MerchantOrderFilters(limit=2, offset=0))
    second = svc.list_page(db, merchant_ctx, MerchantOrderFilters(limit=2, offset=2))
    assert first["total"] == second["total"] >= 3
    assert first["limit"] == 2
    assert first["offset"] == 0
    assert second["offset"] == 2
    first_ids = {row["order_id"] for row in first["items"]}
    second_ids = {row["order_id"] for row in second["items"]}
    assert first_ids.isdisjoint(second_ids)
    assert len(first["items"]) == 2
    assert len(second["items"]) >= 1


def test_default_page_is_smaller_than_old_dump(db, merchant_ctx) -> None:
    page = MerchantOrdersService().list_page(db, merchant_ctx, MerchantOrderFilters())
    assert page["limit"] == DEFAULT_PAGE_SIZE
    assert page["offset"] == 0
    assert page["limit"] < 500


def test_list_page_clamps_limit(db, merchant_ctx) -> None:
    page = MerchantOrdersService().list_page(
        db, merchant_ctx, MerchantOrderFilters(limit=9_999, offset=-3)
    )
    assert page["limit"] == MAX_LIST_LIMIT
    assert page["offset"] == 0


def test_city_and_priority_filter_before_paging(db, merchant_ctx) -> None:
    db.add(_order(merchant_ctx.merchant.id, city="Hamilton", amount_cents=8_000))
    db.add(_order(merchant_ctx.merchant.id, city="Toronto", amount_cents=25_000))
    db.commit()
    svc = MerchantOrdersService()
    hamilton = svc.list_page(db, merchant_ctx, MerchantOrderFilters(city="hamil", limit=50))
    assert hamilton["total"] >= 1
    assert all("Hamilton" in row["pickup"] for row in hamilton["items"])
    high = svc.list_page(db, merchant_ctx, MerchantOrderFilters(priority="high", limit=50))
    assert high["total"] >= 1
    assert all(row["priority"] == "high" for row in high["items"])


def test_admin_reports_uses_counts_not_unbounded_rows(db, merchant_ctx) -> None:
    db.add(_order(merchant_ctx.merchant.id))
    db.commit()
    reports = OrderPlatformService().reports(db)
    assert reports["monthly_orders"] >= 1
    assert isinstance(reports["top_merchants"], list)
    assert len(reports["top_merchants"]) <= 10
    if reports["top_merchants"]:
        name, count = reports["top_merchants"][0]
        assert isinstance(name, str)
        assert int(count) >= 1


def test_merchant_360_orders_are_paged(db, merchant_ctx) -> None:
    for i in range(3):
        db.add(_order(merchant_ctx.merchant.id))
    db.commit()
    page = Merchant360Service().orders(db, merchant_ctx.merchant.id, limit=2, offset=0)
    assert page["total"] >= 3
    assert page["limit"] == 2
    assert len(page["items"]) == 2
    next_page = Merchant360Service().orders(db, merchant_ctx.merchant.id, limit=2, offset=2)
    assert {row["id"] for row in page["items"]}.isdisjoint({row["id"] for row in next_page["items"]})


def test_driver_360_orders_envelope(db, driver) -> None:
    page = Driver360Service().orders(db, driver.id, limit=5)
    assert page["items"] == []
    assert page["total"] == 0
    assert page["limit"] == 5


def test_finance_invoice_page_is_capped(db) -> None:
    page = AdminFinanceService().list_invoices_page(db, FinanceFilters(limit=9_999))
    assert page["limit"] == MAX_LIST_LIMIT
    assert page["offset"] == 0
    assert isinstance(page["items"], list)
    assert page["total"] >= 0


def test_list_enriched_still_returns_rows(db, merchant_ctx) -> None:
    rows = OrderPlatformService().list_enriched(
        db, OrderFilters(merchant_id=merchant_ctx.merchant.id, limit=10)
    )
    assert isinstance(rows, list)
