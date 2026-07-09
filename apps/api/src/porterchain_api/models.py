"""Backward-compatible re-exports — prefer `booking_models` in new code (§3.2.1)."""

from porterchain_api.booking_models import (
    AbandonedCheckout,
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
