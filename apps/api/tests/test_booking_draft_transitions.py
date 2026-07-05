"""Booking draft state machine tests."""

from porterchain_api.domain.states import (
    BOOKING_DRAFT_TERMINAL,
    BookingDraftState,
    can_transition_booking_draft,
)


def test_terminal_drafts_cannot_transition() -> None:
    for terminal in BOOKING_DRAFT_TERMINAL:
        for target in BookingDraftState:
            if target == terminal:
                continue
            assert can_transition_booking_draft(terminal, target) is False


def test_draft_to_quote_generated() -> None:
    assert can_transition_booking_draft(BookingDraftState.DRAFT, BookingDraftState.QUOTE_GENERATED) is True


def test_payment_completed_to_booking_confirmed() -> None:
    assert (
        can_transition_booking_draft(
            BookingDraftState.PAYMENT_COMPLETED,
            BookingDraftState.BOOKING_CONFIRMED,
        )
        is True
    )
