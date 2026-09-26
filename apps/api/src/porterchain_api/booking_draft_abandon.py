"""Booking-draft inactivity abandonment — shared by admin + collaboration (non-engine)."""

from __future__ import annotations

from datetime import datetime, timedelta

from porterchain_api.booking_draft_models import BookingDraft
from porterchain_api.domain.states import BOOKING_DRAFT_TERMINAL, BookingDraftState

ABANDONED_AFTER_MINUTES = 30
ACTIVE_PRE_CONFIRM = tuple(
    s.value
    for s in BookingDraftState
    if s not in BOOKING_DRAFT_TERMINAL and s != BookingDraftState.EXPIRED
)


def is_abandoned(draft: BookingDraft, now: datetime) -> bool:
    if draft.state in {s.value for s in BOOKING_DRAFT_TERMINAL}:
        return False
    if draft.state == BookingDraftState.EXPIRED.value:
        return True
    threshold = now - timedelta(minutes=ABANDONED_AFTER_MINUTES)
    updated = draft.updated_at.replace(tzinfo=None) if draft.updated_at.tzinfo else draft.updated_at
    return updated < threshold and draft.state in ACTIVE_PRE_CONFIRM


__all__ = ["ABANDONED_AFTER_MINUTES", "ACTIVE_PRE_CONFIRM", "is_abandoned"]
