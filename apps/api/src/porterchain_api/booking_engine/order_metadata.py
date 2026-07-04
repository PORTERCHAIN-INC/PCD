"""Order metadata helpers — source and type classification (masterrule §10)."""

from __future__ import annotations

from porterchain_api.domain.states import OrderSource, OrderType


def resolve_order_type(
    *,
    schedule_mode: str = "now",
    has_contract: bool = False,
    is_recurring: bool = False,
    is_rush: bool = False,
) -> str:
    if is_recurring:
        return OrderType.RECURRING.value
    if has_contract:
        return OrderType.CONTRACT.value
    if schedule_mode == "later":
        return OrderType.SCHEDULED.value
    if is_rush or schedule_mode == "now":
        return OrderType.EXPRESS.value if is_rush else OrderType.INSTANT.value
    return OrderType.INSTANT.value


def retail_order_source() -> str:
    return OrderSource.WEBSITE.value
