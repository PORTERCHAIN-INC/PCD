"""Postgres-backed Stripe webhook idempotency (DD-23, §2.5.3)."""

from __future__ import annotations

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from porterchain_api.booking_models import StripeWebhookEvent


def claim_stripe_event(db: Session, *, stripe_event_id: str, event_type: str) -> bool:
    """Return True when this worker should process; False when already claimed."""
    stmt = (
        insert(StripeWebhookEvent)
        .values(
            stripe_event_id=stripe_event_id,
            event_type=event_type,
            status="processing",
        )
        .on_conflict_do_nothing(index_elements=["stripe_event_id"])
        .returning(StripeWebhookEvent.id)
    )
    claimed_id = db.execute(stmt).scalar_one_or_none()
    db.flush()
    return claimed_id is not None


def complete_stripe_event(db: Session, *, stripe_event_id: str) -> None:
    db.query(StripeWebhookEvent).filter(StripeWebhookEvent.stripe_event_id == stripe_event_id).update(
        {"status": "processed"}
    )


def release_stripe_event(db: Session, *, stripe_event_id: str) -> None:
    """Allow Stripe retry after a failed processing attempt."""
    db.query(StripeWebhookEvent).filter(StripeWebhookEvent.stripe_event_id == stripe_event_id).delete()
