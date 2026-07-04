"""Notification event handlers — delegate to Notification Engine only."""

from __future__ import annotations

import logging
from typing import Any

from porterchain_api.notification_engine.event_router import handle_domain_event

logger = logging.getLogger(__name__)


def notify_order_booked(envelope: dict[str, Any]) -> None:
    handle_domain_event(envelope)


def notify_booking_confirmed(envelope: dict[str, Any]) -> None:
    handle_domain_event(envelope)


def notify_claim_opened(envelope: dict[str, Any]) -> None:
    handle_domain_event(envelope)


def notify_support_ticket_created(envelope: dict[str, Any]) -> None:
    handle_domain_event(envelope)
