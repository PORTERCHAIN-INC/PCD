"""Shared support domain helpers — ticket numbers and timeline (no admin_engine imports)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from porterchain_api.admin_models import SupportTicket

TICKET_CATEGORIES = frozenset({
    "general_inquiry",
    "booking_issue",
    "quote_issue",
    "tracking_issue",
    "pickup_issue",
    "delivery_issue",
    "late_delivery",
    "lost_parcel",
    "damaged_parcel",
    "wrong_delivery",
    "billing_issue",
    "invoice_issue",
    "payment_issue",
    "refund_request",
    "merchant_support",
    "driver_support",
    "fleet_issue",
    "technical_issue",
    "api_support",
    "account_issue",
    "complaint",
    "suggestion",
    "claim",
    "internal_request",
    "compliance",
    "other",
})


def ticket_number(ticket_id: str) -> str:
    return f"PCT-{ticket_id[:8].upper()}"


def _ticket_data(ticket: SupportTicket) -> dict[str, Any]:
    return dict(ticket.ticket_data or {})


def append_ticket_timeline(
    ticket: SupportTicket,
    *,
    label: str,
    actor_type: str = "system",
    actor_id: str | None = None,
    payload: dict | None = None,
) -> None:
    data = _ticket_data(ticket)
    timeline = list(data.get("timeline") or [])
    timeline.append(
        {
            "id": str(uuid.uuid4()),
            "label": label,
            "actor_type": actor_type,
            "actor_id": actor_id,
            "occurred_at": datetime.now(UTC).isoformat(),
            "payload": payload or {},
        }
    )
    data["timeline"] = timeline
    ticket.ticket_data = data
