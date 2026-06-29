"""Merchant portal RBAC per ROLE_PERMISSIONS.md."""

from dataclasses import dataclass

from porterchain_api.domain.merchant_states import MerchantRole
from porterchain_api.merchant_models import Merchant, MerchantUser


@dataclass(frozen=True)
class MerchantContext:
    merchant: Merchant
    user: MerchantUser
    role: MerchantRole


MODULE_PERMISSIONS: dict[str, frozenset[MerchantRole]] = {
    "dashboard": frozenset(MerchantRole),
    "book": frozenset({MerchantRole.OWNER, MerchantRole.ADMIN, MerchantRole.OPS}),
    "bulk": frozenset({MerchantRole.OWNER, MerchantRole.ADMIN, MerchantRole.OPS}),
    "api_keys": frozenset({MerchantRole.OWNER, MerchantRole.ADMIN}),
    "orders": frozenset(MerchantRole),
    "orders_write": frozenset({MerchantRole.OWNER, MerchantRole.ADMIN, MerchantRole.OPS}),
    "tracking": frozenset(MerchantRole),
    "invoices": frozenset(MerchantRole),
    "invoices_pay": frozenset({MerchantRole.OWNER, MerchantRole.ADMIN, MerchantRole.FINANCE}),
    "statements": frozenset({MerchantRole.OWNER, MerchantRole.ADMIN, MerchantRole.FINANCE, MerchantRole.READONLY}),
    "reports": frozenset(MerchantRole),
    "billing": frozenset({MerchantRole.OWNER, MerchantRole.ADMIN, MerchantRole.FINANCE}),
    "users": frozenset({MerchantRole.OWNER, MerchantRole.ADMIN}),
    "settings": frozenset({MerchantRole.OWNER, MerchantRole.ADMIN, MerchantRole.FINANCE, MerchantRole.OPS}),
    "support": frozenset(MerchantRole),
}


def require_module(ctx: MerchantContext, module: str) -> None:
    allowed = MODULE_PERMISSIONS.get(module, frozenset())
    if ctx.role not in allowed:
        raise PermissionError(f"merchant_forbidden:{module}")


def parse_merchant_role(role_str: str) -> MerchantRole:
    for role in MerchantRole:
        if role.value == role_str or role.name.lower() == role_str:
            return role
    return MerchantRole.OPS
