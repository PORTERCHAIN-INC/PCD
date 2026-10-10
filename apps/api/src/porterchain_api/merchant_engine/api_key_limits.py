"""Per-key API rate limits (staff-owned; merchants see them read-only).

Split out of ``integrations_service`` (at its legacy size cap). Out-of-range
values are rejected instead of silently clamped, so the number the admin saves
is the number that applies.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.merchant_models import MerchantApiKey

RATE_LIMIT_MIN = 10
RATE_LIMIT_MAX = 600


def validate_rate_limit(value: Any) -> int:
    try:
        rpm = int(value)
    except (TypeError, ValueError):
        raise ValueError("rate_limit_invalid") from None
    if not RATE_LIMIT_MIN <= rpm <= RATE_LIMIT_MAX:
        raise ValueError("rate_limit_invalid")
    return rpm


def set_rate_limit(db: Session, merchant_id: str, key_id: str, rate_limit_per_minute: Any) -> dict[str, Any]:
    rpm = validate_rate_limit(rate_limit_per_minute)
    record = (
        db.query(MerchantApiKey)
        .filter(MerchantApiKey.id == key_id, MerchantApiKey.merchant_id == merchant_id)
        .first()
    )
    if not record:
        raise LookupError("api_key_not_found")
    record.rate_limit_per_minute = rpm
    db.commit()
    db.refresh(record)
    return {"api_key_id": record.id, "rate_limit_per_minute": record.rate_limit_per_minute}
