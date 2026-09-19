"""Merchant portal module catalog + SpiceDB Check helpers.

``MODULE_PERMISSIONS`` / ``permissions_catalog`` are UX/display matrices for
team settings and reporting. Authorization Checks go through SpiceDB only
(``require_module`` → organization permission).
"""

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
    "routes": frozenset({MerchantRole.OWNER, MerchantRole.ADMIN, MerchantRole.OPS}),
    "api_keys": frozenset({MerchantRole.OWNER, MerchantRole.ADMIN}),
    "orders": frozenset(MerchantRole),
    "orders_write": frozenset({MerchantRole.OWNER, MerchantRole.ADMIN, MerchantRole.OPS}),
    "tracking": frozenset(MerchantRole),
    "invoices": frozenset({MerchantRole.OWNER, MerchantRole.ADMIN, MerchantRole.FINANCE}),
    "invoices_pay": frozenset({MerchantRole.OWNER, MerchantRole.ADMIN, MerchantRole.FINANCE}),
    "statements": frozenset({MerchantRole.OWNER, MerchantRole.ADMIN, MerchantRole.FINANCE}),
    "reports": frozenset({MerchantRole.OWNER, MerchantRole.ADMIN, MerchantRole.FINANCE}),
    "billing": frozenset({MerchantRole.OWNER, MerchantRole.ADMIN, MerchantRole.FINANCE}),
    "users": frozenset({MerchantRole.OWNER, MerchantRole.ADMIN}),
    "settings": frozenset({MerchantRole.OWNER, MerchantRole.ADMIN}),
    "support": frozenset(MerchantRole),
    "claims": frozenset({MerchantRole.OWNER, MerchantRole.ADMIN, MerchantRole.OPS, MerchantRole.FINANCE}),
}

# SpiceDB organization relation names (schema.zed) for each MerchantRole.
_ROLE_RELATION: dict[MerchantRole, str] = {
    MerchantRole.OWNER: "owner",
    MerchantRole.ADMIN: "admin",
    MerchantRole.OPS: "ops",
    MerchantRole.FINANCE: "finance",
    MerchantRole.READONLY: "readonly",
}

# 403 copy names the job, not the internal module key.
MODULE_JOB: dict[str, str] = {
    "book": "Dispatcher",
    "bulk": "Dispatcher",
    "routes": "Dispatcher",
    "orders_write": "Dispatcher",
    "billing": "Accounting",
    "invoices": "Accounting",
    "invoices_pay": "Accounting",
    "statements": "Accounting",
    "reports": "Accounting",
    "users": "Manager",
    "api_keys": "Manager",
    "settings": "Manager",
}


ROLE_LABELS: dict[MerchantRole, str] = {
    MerchantRole.OWNER: "Owner",
    MerchantRole.ADMIN: "Manager",
    MerchantRole.OPS: "Dispatcher",
    MerchantRole.FINANCE: "Accounting",
    MerchantRole.READONLY: "Viewer",
}

MODULE_ENGLISH: dict[str, str] = {
    "dashboard": "Overview",
    "book": "Booking",
    "bulk": "Bulk upload",
    "routes": "Route planner",
    "api_keys": "Integrations",
    "orders": "Orders",
    "orders_write": "order changes",
    "tracking": "Track",
    "invoices": "Invoices",
    "invoices_pay": "invoice payment",
    "statements": "Statements",
    "reports": "Reports",
    "billing": "Billing",
    "users": "Team",
    "settings": "Company settings",
    "support": "Notifications",
    "claims": "Claims",
}


def english_role(role: MerchantRole | str) -> str:
    if isinstance(role, MerchantRole):
        return ROLE_LABELS.get(role, role.value)
    try:
        return ROLE_LABELS.get(MerchantRole(role), role.replace("_", " ").title())
    except ValueError:
        return role.replace("_", " ").title()


def module_label(module: str) -> str:
    key = (module or "").strip()
    if key in MODULE_ENGLISH:
        return MODULE_ENGLISH[key]
    return key.replace("_", " ").strip().title() or "this page"


def forbidden_message(module: str) -> str:
    if (module or "").strip() == "owner_only":
        return "Ask your company owner to do this."
    job = MODULE_JOB.get((module or "").strip())
    if job:
        return f"Ask your owner for {job} access."
    return f"Ask your owner for access to {module_label(module)}."


def organization_permission_roles() -> dict[str, frozenset[str]]:
    """SpiceDB organization permission → relation names. Keep in sync with schema.zed."""
    extras: dict[str, frozenset[str]] = {
        "portal": frozenset({"owner", "admin", "ops", "finance", "readonly", "member"}),
        "manage": frozenset({"owner", "admin"}),
    }
    modules = {
        module: frozenset(_ROLE_RELATION[role] for role in allowed)
        for module, allowed in MODULE_PERMISSIONS.items()
    }
    return {**extras, **modules}


def permissions_catalog() -> dict[str, Any]:
    """Expose merchant role→module matrix for portal team UI / reporting (not Check SoT)."""
    roles = [
        {
            "role": role.value,
            "label": ROLE_LABELS.get(role, role.value),
            "modules": sorted(m for m, allowed in MODULE_PERMISSIONS.items() if role in allowed),
            "module_labels": [
                module_label(m)
                for m, allowed in sorted(MODULE_PERMISSIONS.items())
                if role in allowed
            ],
        }
        for role in MerchantRole
    ]
    modules = [
        {
            "module": module,
            "label": module_label(module),
            "roles": sorted(r.value for r in allowed),
            "role_labels": [ROLE_LABELS[r] for r in MerchantRole if r in allowed],
        }
        for module, allowed in sorted(MODULE_PERMISSIONS.items())
    ]
    return {"roles": roles, "modules": modules}


def modules_for_role(role: MerchantRole) -> frozenset[str]:
    return frozenset(m for m, allowed in MODULE_PERMISSIONS.items() if role in allowed)


def require_module(ctx: MerchantContext, module: str) -> None:
    """Authorize merchant module via SpiceDB only — no matrix fallback."""
    from porterchain_api.authz.client import get_authz_client

    user_id = getattr(ctx.user, "porterchain_user_id", None)
    if not user_id:
        raise PermissionError(f"merchant_forbidden:{module}:unlinked_user")

    client = get_authz_client()
    if client.check(
        resource_type="organization",
        resource_id=ctx.merchant.id,
        permission=module,
        subject_id=user_id,
    ):
        return
    raise PermissionError(f"merchant_forbidden:{module}")


def require_owner(ctx: MerchantContext) -> None:
    """Owner-only actions: go-live preference off, mint production API keys."""
    if ctx.role != MerchantRole.OWNER:
        raise PermissionError("merchant_forbidden:owner_only")


def parse_merchant_role(role_str: str) -> MerchantRole:
    for role in MerchantRole:
        if role.value == role_str or role.name.lower() == role_str:
            return role
    return MerchantRole.OPS
