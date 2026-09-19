from enum import StrEnum


class QuoteState(StrEnum):
    DRAFT = "DRAFT"
    QUOTE = "QUOTE"
    QUOTE_EXPIRED = "QUOTE_EXPIRED"
    BOOKING_PENDING = "BOOKING_PENDING"
    PAYMENT_PENDING = "PAYMENT_PENDING"
    CANCELLED = "CANCELLED"


class BookingState(StrEnum):
    BOOKED = "BOOKED"
    CANCELLED = "CANCELLED"
    REFUNDED = "REFUNDED"


class PaymentStatus(StrEnum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class OrderState(StrEnum):
    BOOKED = "BOOKED"
    DISPATCH_READY = "DISPATCH_READY"
    DRIVER_ASSIGNED = "DRIVER_ASSIGNED"
    DRIVER_ACCEPTED = "DRIVER_ACCEPTED"
    DRIVER_REJECTED = "DRIVER_REJECTED"
    DRIVER_EN_ROUTE = "DRIVER_EN_ROUTE"
    AT_PICKUP = "AT_PICKUP"
    PICKED_UP = "PICKED_UP"
    IN_TRANSIT = "IN_TRANSIT"
    AT_DESTINATION = "AT_DESTINATION"
    DELIVERED = "DELIVERED"
    POD_COMPLETED = "POD_COMPLETED"
    INVOICED = "INVOICED"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"
    RETURN_TO_SENDER = "RETURN_TO_SENDER"
    DAMAGED = "DAMAGED"
    LOST = "LOST"
    CLAIM_OPEN = "CLAIM_OPEN"
    REFUNDED = "REFUNDED"


# Terminal / no-dispatch states — not in the live Fleetbase link SLO.
FLEETBASE_SYNC_EXCLUDED_STATES: frozenset[str] = frozenset(
    {
        OrderState.CANCELLED.value,
        OrderState.REFUNDED.value,
        OrderState.DELIVERED.value,
        OrderState.INVOICED.value,
        OrderState.CLOSED.value,
        OrderState.FAILED.value,
        OrderState.POD_COMPLETED.value,
    }
)


class BookingDraftState(StrEnum):
    DRAFT = "DRAFT"
    QUOTE_GENERATED = "QUOTE_GENERATED"
    CUSTOMER_IDENTIFIED = "CUSTOMER_IDENTIFIED"
    AUTHENTICATED = "AUTHENTICATED"
    PAYMENT_PENDING = "PAYMENT_PENDING"
    PAYMENT_FAILED = "PAYMENT_FAILED"
    PAYMENT_COMPLETED = "PAYMENT_COMPLETED"
    BOOKING_CONFIRMED = "BOOKING_CONFIRMED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


class PaymentTerms(StrEnum):
    IMMEDIATE = "IMMEDIATE"
    NET_7 = "NET_7"
    NET_14 = "NET_14"
    NET_15 = "NET_15"
    NET_30 = "NET_30"
    NET_45 = "NET_45"
    CUSTOM = "CUSTOM"


class CodStatus(StrEnum):
    """Cash-on-delivery collection state (Stripe Connect Payment Link path)."""

    NONE = "none"
    PENDING_COLLECTION = "pending_collection"
    LINK_ISSUED = "link_issued"
    COLLECTED = "collected"
    PAYOUT_PROCESSED = "payout_processed"
    FAILED = "failed"


class OrderSource(StrEnum):
    WEBSITE = "WEBSITE"
    MERCHANT = "MERCHANT"
    API = "API"
    CSV = "CSV"
    ADMIN = "ADMIN"
    PHONE = "PHONE"
    PARTNER = "PARTNER"
    SHOPIFY = "SHOPIFY"


class OrderType(StrEnum):
    INSTANT = "INSTANT"
    CONTRACT = "CONTRACT"
    RECURRING = "RECURRING"
    EXPRESS = "EXPRESS"
    SCHEDULED = "SCHEDULED"


class BillingCycle(StrEnum):
    ON_DELIVERY = "ON_DELIVERY"
    WEEKLY = "WEEKLY"
    BIWEEKLY = "BIWEEKLY"
    MONTHLY = "MONTHLY"


class ExceptionType(StrEnum):
    DRIVER_REJECT = "DRIVER_REJECT"
    DRIVER_TIMEOUT = "DRIVER_TIMEOUT"
    DRIVER_UNAVAILABLE = "DRIVER_UNAVAILABLE"
    VEHICLE_BREAKDOWN = "VEHICLE_BREAKDOWN"
    DRIVER_CANCEL = "DRIVER_CANCEL"
    CUSTOMER_UNAVAILABLE = "CUSTOMER_UNAVAILABLE"
    WRONG_ADDRESS = "WRONG_ADDRESS"
    PARCEL_DAMAGED = "PARCEL_DAMAGED"
    PARCEL_LOST = "PARCEL_LOST"
    FAILED_DELIVERY = "FAILED_DELIVERY"
    RETURN_TO_SENDER = "RETURN_TO_SENDER"
    INSURANCE_CLAIM = "INSURANCE_CLAIM"
    REFUND_REQUEST = "REFUND_REQUEST"
    OPS_ESCALATION = "OPS_ESCALATION"


# Valid order state transitions per ORDER_LIFECYCLE.md
ORDER_TRANSITIONS: dict[OrderState, set[OrderState]] = {
    OrderState.BOOKED: {OrderState.DISPATCH_READY, OrderState.CANCELLED},
    OrderState.DISPATCH_READY: {OrderState.DRIVER_ASSIGNED, OrderState.CANCELLED},
    OrderState.DRIVER_ASSIGNED: {
        OrderState.DRIVER_ACCEPTED,
        OrderState.DRIVER_REJECTED,
        OrderState.CANCELLED,
    },
    OrderState.DRIVER_REJECTED: {OrderState.DRIVER_ASSIGNED, OrderState.DISPATCH_READY},
    OrderState.DRIVER_ACCEPTED: {OrderState.DRIVER_EN_ROUTE, OrderState.CANCELLED},
    OrderState.DRIVER_EN_ROUTE: {OrderState.AT_PICKUP, OrderState.FAILED},
    OrderState.AT_PICKUP: {OrderState.PICKED_UP, OrderState.FAILED},
    OrderState.PICKED_UP: {OrderState.IN_TRANSIT, OrderState.FAILED},
    OrderState.IN_TRANSIT: {OrderState.AT_DESTINATION, OrderState.FAILED},
    OrderState.AT_DESTINATION: {OrderState.DELIVERED, OrderState.FAILED},
    OrderState.DELIVERED: {OrderState.POD_COMPLETED, OrderState.DAMAGED, OrderState.LOST, OrderState.FAILED},
    OrderState.POD_COMPLETED: {OrderState.INVOICED},
    OrderState.INVOICED: {OrderState.CLOSED},
    OrderState.FAILED: {
        OrderState.DISPATCH_READY,
        OrderState.RETURN_TO_SENDER,
        OrderState.LOST,
        OrderState.CANCELLED,
    },
    OrderState.DAMAGED: {OrderState.CLAIM_OPEN},
    OrderState.LOST: {OrderState.CLAIM_OPEN},
    OrderState.CLAIM_OPEN: {OrderState.REFUNDED, OrderState.CLOSED},
    OrderState.RETURN_TO_SENDER: {OrderState.CLOSED, OrderState.CLAIM_OPEN},
}


def can_transition_order(from_state: OrderState, to_state: OrderState) -> bool:
    if from_state == to_state:
        return True
    allowed = ORDER_TRANSITIONS.get(from_state, set())
    return to_state in allowed


QUOTE_TRANSITIONS: dict[QuoteState, set[QuoteState]] = {
    QuoteState.DRAFT: {QuoteState.QUOTE, QuoteState.CANCELLED},
    QuoteState.QUOTE: {QuoteState.QUOTE_EXPIRED, QuoteState.BOOKING_PENDING, QuoteState.CANCELLED},
    QuoteState.QUOTE_EXPIRED: {QuoteState.QUOTE},
    QuoteState.BOOKING_PENDING: {QuoteState.PAYMENT_PENDING, QuoteState.QUOTE_EXPIRED, QuoteState.CANCELLED},
    QuoteState.PAYMENT_PENDING: {QuoteState.QUOTE_EXPIRED, QuoteState.CANCELLED},
}


def can_transition_quote(from_state: QuoteState, to_state: QuoteState) -> bool:
    if from_state == to_state:
        return True
    return to_state in QUOTE_TRANSITIONS.get(from_state, set())


BOOKING_DRAFT_TERMINAL: frozenset[BookingDraftState] = frozenset(
    {BookingDraftState.BOOKING_CONFIRMED, BookingDraftState.CANCELLED}
)

BOOKING_DRAFT_TRANSITIONS: dict[BookingDraftState, set[BookingDraftState]] = {
    BookingDraftState.DRAFT: {
        BookingDraftState.QUOTE_GENERATED,
        BookingDraftState.CANCELLED,
        BookingDraftState.EXPIRED,
    },
    BookingDraftState.QUOTE_GENERATED: {
        BookingDraftState.CUSTOMER_IDENTIFIED,
        BookingDraftState.AUTHENTICATED,
        BookingDraftState.PAYMENT_PENDING,
        BookingDraftState.CANCELLED,
        BookingDraftState.EXPIRED,
    },
    BookingDraftState.CUSTOMER_IDENTIFIED: {
        BookingDraftState.AUTHENTICATED,
        BookingDraftState.PAYMENT_PENDING,
        BookingDraftState.CANCELLED,
        BookingDraftState.EXPIRED,
    },
    BookingDraftState.AUTHENTICATED: {
        BookingDraftState.PAYMENT_PENDING,
        BookingDraftState.CANCELLED,
        BookingDraftState.EXPIRED,
    },
    BookingDraftState.PAYMENT_PENDING: {
        BookingDraftState.PAYMENT_FAILED,
        BookingDraftState.PAYMENT_COMPLETED,
        BookingDraftState.CANCELLED,
        BookingDraftState.EXPIRED,
    },
    BookingDraftState.PAYMENT_FAILED: {
        BookingDraftState.PAYMENT_PENDING,
        BookingDraftState.CANCELLED,
        BookingDraftState.EXPIRED,
    },
    BookingDraftState.PAYMENT_COMPLETED: {BookingDraftState.BOOKING_CONFIRMED},
    BookingDraftState.EXPIRED: {
        BookingDraftState.DRAFT,
        BookingDraftState.QUOTE_GENERATED,
        BookingDraftState.PAYMENT_PENDING,
        BookingDraftState.PAYMENT_FAILED,
        # Verified Stripe webhook may arrive after TTL — finalize payment (masterrule §14)
        BookingDraftState.PAYMENT_COMPLETED,
    },
}


def can_transition_booking_draft(from_state: BookingDraftState, to_state: BookingDraftState) -> bool:
    if from_state == to_state:
        return True
    if from_state in BOOKING_DRAFT_TERMINAL:
        return False
    return to_state in BOOKING_DRAFT_TRANSITIONS.get(from_state, set())
