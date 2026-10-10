"""Tenant access guard tests (DD-07)."""

import pytest

from porterchain_api.domain.tenant_access import TenantAccessDenied, assert_order_visible, customer_owns_order, merchant_owns_order
from porterchain_api.domain.tenant_context import TenantScope
from porterchain_api.booking_models import Order


def _order(*, merchant_id: str | None = None, customer_id: str | None = None) -> Order:
    return Order(
        id="ord-1",
        order_number="ORD-TEST",
        tracking_number="PC-TEST",
        amount_cents=100,
        pickup={},
        dropoff={},
        merchant_id=merchant_id,
        customer_id=customer_id,
    )


def test_merchant_scope_allows_owner() -> None:
    order = _order(merchant_id="m-1")
    result = assert_order_visible(order, TenantScope.merchant("m-1"))
    assert result is order


def test_merchant_scope_denies_other_tenant() -> None:
    order = _order(merchant_id="m-1")
    with pytest.raises(TenantAccessDenied):
        assert_order_visible(order, TenantScope.merchant("m-2"))


def test_customer_scope_denies_other_tenant() -> None:
    order = _order(customer_id="c-1")
    with pytest.raises(TenantAccessDenied):
        assert_order_visible(order, TenantScope.customer("c-2"))


def test_ownership_helpers() -> None:
    order = _order(merchant_id="m-1", customer_id="c-1")
    assert merchant_owns_order(order, "m-1") is True
    assert merchant_owns_order(order, "m-2") is False
    assert customer_owns_order(order, "c-1") is True
    assert customer_owns_order(order, "c-2") is False
