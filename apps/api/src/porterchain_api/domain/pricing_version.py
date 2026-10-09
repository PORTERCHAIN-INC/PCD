"""Pricing settings: who may edit them and the version stamped on quotes.

One counter (`system_config.pricing_version`) covers every price input that an
admin edits — the global pricing keys below and any merchant's pricing terms.
Each change bumps it inside the same transaction as the change
(`admin_engine.pricing_versioning.bump_price_version`), and the admin
audit log keeps who / when / old / new / reason. `pricing_engine.repository` loads the
counter into `PricingContext.price_version`, and the engine writes it to every
quote's metadata as `pv-<n>`.
"""

from __future__ import annotations

from typing import Any

from porterchain_api.domain.admin_states import AdminRole

VERSION_KEY = "pricing_version"

#: Storage keys only a super admin may write (settings PUT, restore, import).
PRICING_STORAGE_KEYS = frozenset(
    {
        "pricing_gta_rate",
        "pricing_customer_distance",
        "pricing_tax",
        "pricing_fuel",
        "pricing_rate_card",
        "pricing_book",
        "driver_pay_plan",
    }
)

#: Super-admin-only settings that do not change prices (no price-version bump).
SUPER_ADMIN_SETTING_KEYS = frozenset({"delivery_promise"})

SUPER_ADMIN_ONLY = "pricing_super_admin_only"


def is_super_admin(ctx: Any) -> bool:
    role = getattr(ctx, "role", None)
    return role == AdminRole.SUPER_ADMIN or str(role) == AdminRole.SUPER_ADMIN.value


def assert_pricing_editor(ctx: Any) -> None:
    """Pricing edits are super-admin only; regular admins keep read access."""
    if not is_super_admin(ctx):
        raise PermissionError(SUPER_ADMIN_ONLY)


def format_version(value: Any) -> str:
    n = 0
    if isinstance(value, dict):
        try:
            n = int(value.get("version") or 0)
        except (TypeError, ValueError):
            n = 0
    return f"pv-{n}"
