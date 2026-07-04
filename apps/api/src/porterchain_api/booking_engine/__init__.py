"""Porterchain booking engine — retail quote to delivery entry point."""

from porterchain_api.booking_engine.booking_service import BookingService
from porterchain_api.booking_engine.confirmation_service import BookingConfirmationService
from porterchain_api.booking_engine.customer_service import CustomerService
from porterchain_api.booking_engine.payment_service import PaymentService
from porterchain_api.booking_engine.quote_service import QuoteService
from porterchain_api.booking_engine.tracking_service import TrackingService
from porterchain_api.booking_engine.visitor_tracking_service import VisitorTrackingService
from porterchain_api.booking_engine.booking_draft_service import BookingDraftService

__all__ = [
    "BookingDraftService",
    "BookingConfirmationService",
    "BookingService",
    "CustomerService",
    "PaymentService",
    "QuoteService",
    "TrackingService",
    "VisitorTrackingService",
]


def __getattr__(name: str):
    if name == "NotificationService":
        from porterchain_api.booking_engine.notification_service import NotificationService

        return NotificationService
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
