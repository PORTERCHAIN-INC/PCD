"""Order list filters — shared by admin and merchant portals."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class OrderFilters:
    state: str | None = None
    payment_status: str | None = None
    invoice_status: str | None = None
    merchant_id: str | None = None
    driver_id: str | None = None
    customer_id: str | None = None
    priority: str | None = None
    service_type: str | None = None
    city: str | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    amount_min_cents: int | None = None
    amount_max_cents: int | None = None
    search: str | None = None
    # Live ops default: hide test bookings. Opt in with include_sandbox=True.
    include_sandbox: bool = False
    # When True, return only sandbox rows (implies include_sandbox).
    sandbox_only: bool = False
    limit: int = 50
    offset: int = 0


# Backward-compatible alias for admin routers/schemas.
AdminOrderFilters = OrderFilters
