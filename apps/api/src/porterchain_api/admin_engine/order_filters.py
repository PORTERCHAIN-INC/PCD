"""Admin order-list filter building (split from ``orders_service``, ENG-G2 ≤500 LOC)."""

from __future__ import annotations

from datetime import datetime

from porterchain_api.platform.engine_ports.merchant_engine__toronto import parse_toronto_day_bound
from porterchain_api.platform.engine_ports.order_engine__filters import OrderFilters


def _list_date_bound(value: str | None, *, end: bool, date_field: str | None) -> datetime | None:
    if not value:
        return None
    if date_field == "scheduled":
        parsed = parse_toronto_day_bound(value, end=end)
        if parsed is None:
            raise ValueError("invalid_date")
        return parsed
    return datetime.fromisoformat(value)


def build_admin_order_filters(
    *,
    state: str | None,
    payment_status: str | None,
    invoice_status: str | None,
    merchant_id: str | None,
    driver_id: str | None,
    customer_id: str | None,
    priority: str | None,
    service_type: str | None,
    city: str | None,
    search: str | None,
    date_from: str | None,
    date_to: str | None,
    date_field: str | None,
    queue: str | None,
    include_carryover: bool,
    amount_min_cents: int | None,
    amount_max_cents: int | None,
    include_sandbox: bool,
    sandbox_only: bool,
    limit: int,
    offset: int,
) -> OrderFilters:
    return OrderFilters(
        state=state,
        payment_status=payment_status,
        invoice_status=invoice_status,
        merchant_id=merchant_id,
        driver_id=driver_id,
        customer_id=customer_id,
        priority=priority,
        service_type=service_type,
        city=city,
        search=search,
        date_from=_list_date_bound(date_from, end=False, date_field=date_field),
        date_to=_list_date_bound(date_to, end=True, date_field=date_field),
        date_field=date_field,
        queue=queue,
        include_carryover=include_carryover,
        amount_min_cents=amount_min_cents,
        amount_max_cents=amount_max_cents,
        include_sandbox=include_sandbox or sandbox_only,
        sandbox_only=sandbox_only,
        limit=limit,
        offset=offset,
    )
