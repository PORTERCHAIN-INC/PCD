"""Shared constants, filters, and ticket-data helpers for support."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

from porterchain_api.admin_models import SupportTicket
from porterchain_api.domain.support import append_ticket_timeline


class SupportActorUser(Protocol):
    id: str


class SupportActor(Protocol):
    user: SupportActorUser

TICKET_STATUSES = frozenset({
    "new",
    "open",
    "assigned",
    "waiting_customer",
    "waiting_merchant",
    "waiting_driver",
    "waiting_internal",
    "escalated",
    "resolved",
    "closed",
    "archived",
    # legacy
    "in_progress",
})

LEGACY_STATUS_MAP = {
    "in_progress": "assigned",
    "open": "open",
}

OPEN_STATUSES = frozenset({
    "new",
    "open",
    "assigned",
    "waiting_customer",
    "waiting_merchant",
    "waiting_driver",
    "waiting_internal",
    "escalated",
    "in_progress",
})

DEFAULT_SLA = {
    "first_response_hours": 4,
    "resolution_hours": 24,
    "escalation_hours": 48,
    "business_hours_only": True,
    "holidays": [],
}


def normalize_status(status: str) -> str:
    return LEGACY_STATUS_MAP.get(status, status)


def ticket_data(ticket: SupportTicket) -> dict[str, Any]:
    return dict(ticket.ticket_data or {})


def set_ticket_data(ticket: SupportTicket, **updates: Any) -> None:
    data = ticket_data(ticket)
    data.update(updates)
    ticket.ticket_data = data


def append_timeline(
    ticket: SupportTicket,
    *,
    label: str,
    actor_type: str = "system",
    actor_id: str | None = None,
    payload: dict | None = None,
) -> None:
    append_ticket_timeline(
        ticket,
        label=label,
        actor_type=actor_type,
        actor_id=actor_id,
        payload=payload,
    )


@dataclass
class SupportFilters:
    status: str | None = None
    category: str | None = None
    priority: str | None = None
    agent_id: str | None = None
    merchant_id: str | None = None
    driver_id: str | None = None
    customer_id: str | None = None
    sla: str | None = None
    module: str | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    search: str | None = None
    limit: int = 500
