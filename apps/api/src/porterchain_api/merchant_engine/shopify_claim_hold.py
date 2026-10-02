"""Read-only chargeback lookup for Shopify buyer erasure holds."""

from __future__ import annotations

from sqlalchemy.orm import Session

from porterchain_api.admin_models import Claim

_OPEN = ("open", "investigating")
_DISPUTE = ("chargeback", "payment_dispute")


def open_payment_dispute(db: Session, order_id: str) -> bool:
    return (
        db.query(Claim.id)
        .filter(
            Claim.order_id == order_id,
            Claim.claim_type.in_(_DISPUTE),
            Claim.status.in_(_OPEN),
        )
        .first()
        is not None
    )
