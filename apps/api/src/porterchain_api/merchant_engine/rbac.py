"""Merchant portal RBAC per ROLE_PERMISSIONS.md."""

from dataclasses import dataclass
from typing import Any

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
    "claims": frozenset({MerchantRole.OWNER, MerchantRole.ADMIN, MerchantRole.OPS, MerchantRole.FINANCE}),
}


ROLE_LABELS: dict[MerchantRole, str] = {
    MerchantRole.OWNER: "Owner",
    MerchantRole.ADMIN: "Manager",
    MerchantRole.OPS: "Dispatcher",
    MerchantRole.FINANCE: "Accounting",
    MerchantRole.READONLY: "Viewer",
}


def permissions_catalog() -> dict[str, Any]:
    """Expose canonical RBAC matrix — single source of truth for portal."""
    roles = [
        {
            "role": role.value,
            "label": ROLE_LABELS.get(role, role.value),
            "modules": sorted(m for m, allowed in MODULE_PERMISSIONS.items() if role in allowed),
        }
        for role in MerchantRole
    ]
    modules = [
        {
            "module": module,
            "roles": sorted(r.value for r in allowed),
        }
        for module, allowed in sorted(MODULE_PERMISSIONS.items())
    ]
    return {"roles": roles, "modules": modules}


def modules_for_role(role: MerchantRole) -> frozenset[str]:
    return frozenset(m for m, allowed in MODULE_PERMISSIONS.items() if role in allowed)


def require_module(ctx: MerchantContext, module: str) -> None:
    allowed = MODULE_PERMISSIONS.get(module, frozenset())
    if ctx.role not in allowed:
        raise PermissionError(f"merchant_forbidden:{module}")


def parse_merchant_role(role_str: str) -> MerchantRole:
    for role in MerchantRole:
        if role.value == role_str or role.name.lower() == role_str:
            return role
    return MerchantRole.OPS
