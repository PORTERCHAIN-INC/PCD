"""Enterprise support center — Application Service (masterrule §3)."""

from __future__ import annotations

from porterchain_api.domain.support import TICKET_CATEGORIES, ticket_number
from porterchain_api.support_engine.support_context import SupportContextMixin
from porterchain_api.support_engine.support_dashboard import SupportDashboardMixin
from porterchain_api.support_engine.support_helpers import SupportFilters
from porterchain_api.support_engine.support_kb import SupportKbMixin
from porterchain_api.support_engine.support_ticket_actions import (
    SupportTicketActionsMixin,
)
from porterchain_api.support_engine.support_tickets import SupportTicketsMixin

__all__ = ["TICKET_CATEGORIES", "AdminSupportService", "SupportFilters", "ticket_number"]


class AdminSupportService(
    SupportContextMixin,
    SupportTicketsMixin,
    SupportTicketActionsMixin,
    SupportDashboardMixin,
    SupportKbMixin,
):
    pass
