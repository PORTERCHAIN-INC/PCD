"""Booking → CRM bridge. Writes live in collaboration_engine (§3.2.6)."""

from porterchain_api.collaboration_engine.booking_lead_mirror import (
    mark_booking_lead_converted,
    mirror_booking_lead_to_crm,
)

__all__ = ["mark_booking_lead_converted", "mirror_booking_lead_to_crm"]
