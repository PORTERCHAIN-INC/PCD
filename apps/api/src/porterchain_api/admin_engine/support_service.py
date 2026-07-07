"""Backward-compatible re-export — prefer `support_engine.support_service`."""

from porterchain_api.support_engine.support_service import *  # noqa: F403
from porterchain_api.support_engine.support_service import (
    AdminSupportService,
    SupportFilters,
    TICKET_CATEGORIES,
    ticket_number,
)

__all__ = ["AdminSupportService", "SupportFilters", "TICKET_CATEGORIES", "ticket_number"]
