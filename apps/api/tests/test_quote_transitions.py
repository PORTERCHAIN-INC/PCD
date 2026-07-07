"""Quote state machine tests."""

from porterchain_api.domain.states import QUOTE_TRANSITIONS, QuoteState, can_transition_quote


def test_quote_same_state_allowed() -> None:
    for state in QuoteState:
        assert can_transition_quote(state, state) is True


def test_quote_valid_edges() -> None:
    for from_state, targets in QUOTE_TRANSITIONS.items():
        for to_state in targets:
            assert can_transition_quote(from_state, to_state) is True


def test_quote_cancelled_from_draft() -> None:
    assert can_transition_quote(QuoteState.DRAFT, QuoteState.CANCELLED) is True
    assert can_transition_quote(QuoteState.CANCELLED, QuoteState.QUOTE) is False
