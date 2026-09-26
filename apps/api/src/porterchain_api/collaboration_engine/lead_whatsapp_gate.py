"""WhatsApp outbound gate — consent + 24h care window (no auto-blast)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from porterchain_api.crm_models import CrmLead

CARE_WINDOW = timedelta(hours=24)


class WhatsAppSendBlocked(Exception):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def whatsapp_outbound_status(lead: CrmLead, *, now: datetime | None = None) -> dict[str, Any]:
    """Return whether free-form WhatsApp outbound is allowed for this lead."""
    now = now or datetime.now(UTC)
    consent = lead.consent if isinstance(lead.consent, dict) else {}
    has_consent = consent.get("whatsapp") is True
    last = lead.last_touch_at
    if last is not None and last.tzinfo is None:
        last = last.replace(tzinfo=UTC)
    in_window = bool(last and (now - last) <= CARE_WINDOW)
    allowed = has_consent or in_window
    if has_consent:
        reason = "whatsapp_consent"
    elif in_window:
        reason = "customer_care_window"
    else:
        reason = "missing_whatsapp_consent_and_outside_care_window"
    return {
        "allowed": allowed,
        "reason": reason,
        "whatsapp_consent": has_consent,
        "in_care_window": in_window,
        "last_touch_at": last.isoformat() if last else None,
    }


def assert_whatsapp_outbound_allowed(lead: CrmLead, *, now: datetime | None = None) -> dict[str, Any]:
    """Raise WhatsAppSendBlocked when free-form outbound would violate policy."""
    status = whatsapp_outbound_status(lead, now=now)
    if not status["allowed"]:
        raise WhatsAppSendBlocked(str(status["reason"]))
    return status


__all__ = [
    "CARE_WINDOW",
    "WhatsAppSendBlocked",
    "assert_whatsapp_outbound_allowed",
    "whatsapp_outbound_status",
]
