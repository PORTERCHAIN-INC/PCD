"""Backward-compatible re-export — prefer `support_engine.support_service`."""

from porterchain_api.support_engine.support_service import *
from porterchain_api.support_engine.support_service import (
    TICKET_CATEGORIES,
    AdminSupportService,
    SupportFilters,
    ticket_number,
)

__all__ = ["TICKET_CATEGORIES", "AdminSupportService", "SupportFilters", "ticket_number"]
