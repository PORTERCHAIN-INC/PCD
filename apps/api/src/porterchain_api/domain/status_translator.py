"""Status maps for old event names. PorterChain order states stay the source."""

from __future__ import annotations

from porterchain_api.domain.states import OrderState
from porterchain_api.domain.order_lifecycle import (
    ASSIGNMENT_EVENTS,
    CLAIM_EVENTS,
    EXCEPTION_EVENTS,
    POD_EVENTS,
    TRACKING_EVENTS,
    FleetbaseLifecycleTranslator,
)


class StatusTranslator:
    @staticmethod
    def to_state(*, event: str | None = None, status: str | None = None) -> OrderState | None:
        mapped = FleetbaseLifecycleTranslator.to_state_str(event=event, status=status)
        if not mapped:
            return None
        try:
            return OrderState(mapped)
        except ValueError:
            return None

    @staticmethod
    def classify(event: str | None) -> str:
        return FleetbaseLifecycleTranslator.classify(event)

    @staticmethod
    def exception_type(event: str | None) -> str:
        return FleetbaseLifecycleTranslator.exception_type(event)
