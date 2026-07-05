"""Tenant scope unit tests (DD-07)."""

from porterchain_api.domain.tenant_context import TenantKind, TenantScope


def test_merchant_scope() -> None:
    scope = TenantScope.merchant("m-1")
    assert scope.kind == TenantKind.MERCHANT
    assert scope.tenant_id == "m-1"


def test_customer_scope() -> None:
    scope = TenantScope.customer("c-1")
    assert scope.kind == TenantKind.CUSTOMER
    assert scope.tenant_id == "c-1"
