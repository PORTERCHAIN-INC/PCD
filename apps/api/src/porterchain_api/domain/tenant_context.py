"""Multi-tenant scope for merchant and customer data isolation (DD-07)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class TenantKind(StrEnum):
    MERCHANT = "merchant"
    CUSTOMER = "customer"


@dataclass(frozen=True)
class TenantScope:
    """Canonical tenant boundary — all tenant-owned reads/writes must carry a scope."""

    kind: TenantKind
    tenant_id: str

    @classmethod
    def merchant(cls, merchant_id: str) -> TenantScope:
        return cls(kind=TenantKind.MERCHANT, tenant_id=merchant_id)

    @classmethod
    def customer(cls, customer_id: str) -> TenantScope:
        return cls(kind=TenantKind.CUSTOMER, tenant_id=customer_id)
