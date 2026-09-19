"""Shared constants and filters for claims management."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from porterchain_api.admin_models import Claim

CLAIM_STATUSES = frozenset({
    "new",
    "assigned",
    "under_investigation",
    "waiting_customer",
    "waiting_merchant",
    "waiting_driver",
    "waiting_insurance",
    "approved",
    "rejected",
    "compensated",
    "closed",
    "archived",
    # legacy
    "open",
    "investigating",
    "resolved",
})

LEGACY_STATUS_MAP = {
    "open": "new",
    "investigating": "under_investigation",
    "resolved": "compensated",
}


def normalize_status(status: str) -> str:
    return LEGACY_STATUS_MAP.get(status, status)


def claim_meta(claim: Claim) -> dict[str, Any]:
    return dict((claim.evidence or {}).get("_meta") or {})


def set_claim_meta(claim: Claim, **updates: Any) -> None:
    ev = dict(claim.evidence or {})
    meta = dict(ev.get("_meta") or {})
    meta.update(updates)
    ev["_meta"] = meta
    claim.evidence = ev


@dataclass
class ClaimFilters:
    status: str | None = None
    claim_type: str | None = None
    priority: str | None = None
    investigator_id: str | None = None
    merchant_id: str | None = None
    driver_id: str | None = None
    customer_id: str | None = None
    insurance: bool | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    amount_min_cents: int | None = None
    amount_max_cents: int | None = None
    risk_min: int | None = None
    search: str | None = None
    limit: int = 500
