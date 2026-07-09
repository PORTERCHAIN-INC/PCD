"""Backward-compatible re-exports — prefer `booking_models` in new code (§3.2.1)."""

from porterchain_api.booking_models import (
    AbandonedCheckout,
    AnalyticsEvent,
    AnalyticsStopLeg,
    Booking,
    Customer,
    DomainEvent,
    Invoice,
    Lead,
    Order,
    OrderEvent,
    OrderException,
    Payment,
    Quote,
    VisitorSession,
)

__all__ = [
    "AbandonedCheckout",
    "AnalyticsEvent",
    "AnalyticsStopLeg",
    "Booking",
    "Customer",
    "DomainEvent",
    "Invoice",
    "Lead",
    "Order",
    "OrderEvent",
    "OrderException",
    "Payment",
    "Quote",
    "VisitorSession",
]
