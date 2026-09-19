"""Tenant access guards — deny cross-tenant reads (DD-07)."""

from __future__ import annotations

from porterchain_api.domain.tenant_context import TenantKind, TenantScope
from porterchain_api.booking_models import Order


class TenantAccessDenied(PermissionError):
    """Raised when a principal attempts to access another tenant's resource."""


def assert_order_visible(order: Order | None, scope: TenantScope) -> Order:
    if order is None:
        raise LookupError("order_not_found")
    if scope.kind == TenantKind.MERCHANT:
        if order.merchant_id != scope.tenant_id:
            raise TenantAccessDenied("cross_tenant_order_access")
    elif scope.kind == TenantKind.CUSTOMER:
        if order.customer_id != scope.tenant_id:
            raise TenantAccessDenied("cross_tenant_order_access")
    return order


def merchant_owns_order(order: Order | None, merchant_id: str) -> bool:
    return bool(order and order.merchant_id == merchant_id)


def customer_owns_order(order: Order | None, customer_id: str) -> bool:
    return bool(order and order.customer_id == customer_id)
