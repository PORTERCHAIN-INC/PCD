"""Idempotent claim helpers for Clerk webhook events."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from porterchain_api.auth.clerk_webhook_models import ClerkWebhookEvent


def claim_clerk_event(db: Session, *, clerk_event_id: str, event_type: str) -> bool:
    """Return True when this worker should process; False on duplicate delivery."""
    stmt = (
        insert(ClerkWebhookEvent)
        .values(
            clerk_event_id=clerk_event_id,
            event_type=event_type,
            status="processing",
        )
        .on_conflict_do_nothing(index_elements=["clerk_event_id"])
        .returning(ClerkWebhookEvent.id)
    )
    claimed_id = db.execute(stmt).scalar_one_or_none()
    db.flush()
    return claimed_id is not None


def complete_clerk_event(db: Session, *, clerk_event_id: str) -> None:
    db.query(ClerkWebhookEvent).filter(ClerkWebhookEvent.clerk_event_id == clerk_event_id).update(
        {"status": "processed", "processed_at": datetime.now(UTC)}
    )


def release_clerk_event(db: Session, *, clerk_event_id: str) -> None:
    db.query(ClerkWebhookEvent).filter(ClerkWebhookEvent.clerk_event_id == clerk_event_id).delete()
