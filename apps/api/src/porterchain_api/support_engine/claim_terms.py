"""B5 claims terms on every new claim: deadline, required records, coverage reference.

Contract merchants (``pricing_config.schedule.contract_schedule``) use their contract's
terms; everyone else gets the platform defaults. Nothing is rejected automatically —
the claim records whether it was filed late and which records are still missing.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.booking_models import Order
from porterchain_api.merchant_models import Merchant
from porterchain_pricing.contract_schedule import load_contract_schedule
from porterchain_pricing.contract_terms import (
    claim_deadline,
    missing_claim_records,
    terms_of,
)


def claim_terms_meta(
    db: Session, order: Order | None, provided_records: list[str] | None = None
) -> dict[str, Any]:
    from porterchain_api.admin_models import SystemConfig

    row = db.get(SystemConfig, "carriage_terms")
    global_terms = (
        row.value if row is not None and isinstance(row.value, dict) else None
    )
    terms = terms_of(None, global_terms)
    schedule_id = None
    if order is not None and order.merchant_id:
        merchant = db.get(Merchant, order.merchant_id)
        sched = (
            ((merchant.pricing_config or {}).get("schedule") or {}) if merchant else {}
        )
        schedule_id = sched.get("contract_schedule")
        if schedule_id:
            terms = terms_of(
                load_contract_schedule(schedule_id, sched.get("contract_overrides")),
                global_terms,
            )
    delivered = (
        getattr(order, "delivered_at", None) or getattr(order, "updated_at", None)
        if order
        else None
    )
    deadline = claim_deadline(terms, (delivered or datetime.now(UTC)).date())
    return {
        "claim_reference": f"CLM-{(order.order_number if order else 'NA')}",
        "contract_schedule": schedule_id,
        "claim_deadline": deadline.isoformat(),
        "filed_late": datetime.now(UTC).date() > deadline,
        "required_records": list(terms["claims"]["required_records"]),
        "missing_records": missing_claim_records(terms, provided_records or []),
        "notify_email": terms["claims"].get("notify_email"),
    }
