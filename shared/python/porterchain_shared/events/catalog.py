"""Domain event catalog — canonical event types for Porterchain event bus."""

from enum import StrEnum


class DomainEventType(StrEnum):
    # Visitor
    VISITOR_CREATED = "visitor.created"
    VISITOR_SESSION_STARTED = "visitor.session_started"
    SESSION_MERGED = "visitor.session_merged"

    # Quote & booking
    QUOTE_CREATED = "quote.created"
    QUOTE_ACCEPTED = "quote.accepted"
    QUOTE_EXPIRED = "quote.expired"
    BOOKING_STARTED = "booking.started"
    BOOKING_CONFIRMED = "booking.confirmed"
    CHECKOUT_STARTED = "checkout.started"
    CHECKOUT_ABANDONED = "checkout.abandoned"

    # Customer
    CUSTOMER_REGISTERED = "customer.registered"
    CUSTOMER_AUTHENTICATED = "customer.authenticated"

    # Merchant
    MERCHANT_LEAD_CREATED = "merchant.lead_created"
    MERCHANT_APPROVED = "merchant.approved"
    MERCHANT_ACTIVATED = "merchant.activated"
    MERCHANT_BILLED = "merchant.billed"

    # Payment
    PAYMENT_SUCCEEDED = "payment.succeeded"
    PAYMENT_FAILED = "payment.failed"

    # Orders
    ORDER_CREATED = "order.created"
    ORDER_BOOKED = "order.booked"
    ORDER_DISPATCH_READY = "order.dispatch_ready"
    DISPATCH_REQUESTED = "order.dispatch_requested"
    DRIVER_ASSIGNED = "order.driver_assigned"
    DRIVER_ACCEPTED = "order.driver_accepted"
    DRIVER_ARRIVED_PICKUP = "order.arrived_pickup"
    PARCEL_PICKED_UP = "order.pickup_completed"
    DELIVERY_STARTED = "order.in_transit"
    PARCEL_DELIVERED = "order.delivered"
    PROOF_COMPLETED = "order.pod_completed"
    INVOICE_GENERATED = "order.invoiced"
    ORDER_CLOSED = "order.closed"
    ORDER_CANCELLED = "order.cancelled"
    DRIVER_REJECTED = "order.driver_rejected"

    # Financial
    REFUND_REQUESTED = "refund.requested"
    REFUND_ISSUED = "refund.issued"
    DRIVER_PAYOUT_CREATED = "driver.payout_created"

    # Claims
    CLAIM_OPENED = "claim.opened"
    CLAIM_RESOLVED = "claim.resolved"

    # Notifications & webhooks
    NOTIFICATION_QUEUED = "notification.queued"
    NOTIFICATION_SENT = "notification.sent"
    WEBHOOK_RECEIVED = "webhook.received"

    # Fleetbase sync
    FLEETBASE_ORDER_CREATED = "fleetbase.order_created"
    FLEETBASE_STATUS_UPDATED = "fleetbase.status_updated"
    FLEETBASE_POD_RECEIVED = "fleetbase.pod_received"
    FLEETBASE_SYNC_FAILED = "fleetbase.sync_failed"

    # CRM
    LEAD_CREATED = "lead.created"


# PascalCase aliases for documentation / codegen
EVENT_ALIASES: dict[str, str] = {
    "VisitorCreated": DomainEventType.VISITOR_CREATED,
    "QuoteCreated": DomainEventType.QUOTE_CREATED,
    "QuoteAccepted": DomainEventType.QUOTE_ACCEPTED,
    "CustomerRegistered": DomainEventType.CUSTOMER_REGISTERED,
    "MerchantApproved": DomainEventType.MERCHANT_APPROVED,
    "PaymentSucceeded": DomainEventType.PAYMENT_SUCCEEDED,
    "BookingConfirmed": DomainEventType.BOOKING_CONFIRMED,
    "OrderCreated": DomainEventType.ORDER_CREATED,
    "DispatchRequested": DomainEventType.DISPATCH_REQUESTED,
    "DriverAssigned": DomainEventType.DRIVER_ASSIGNED,
    "DriverAccepted": DomainEventType.DRIVER_ACCEPTED,
    "DriverArrivedPickup": DomainEventType.DRIVER_ARRIVED_PICKUP,
    "ParcelPickedUp": DomainEventType.PARCEL_PICKED_UP,
    "DeliveryStarted": DomainEventType.DELIVERY_STARTED,
    "ParcelDelivered": DomainEventType.PARCEL_DELIVERED,
    "ProofCompleted": DomainEventType.PROOF_COMPLETED,
    "InvoiceGenerated": DomainEventType.INVOICE_GENERATED,
    "MerchantBilled": DomainEventType.MERCHANT_BILLED,
    "DriverPayoutCreated": DomainEventType.DRIVER_PAYOUT_CREATED,
    "RefundRequested": DomainEventType.REFUND_REQUESTED,
    "ClaimOpened": DomainEventType.CLAIM_OPENED,
    "ClaimResolved": DomainEventType.CLAIM_RESOLVED,
    "NotificationQueued": DomainEventType.NOTIFICATION_QUEUED,
    "NotificationSent": DomainEventType.NOTIFICATION_SENT,
    "WebhookReceived": DomainEventType.WEBHOOK_RECEIVED,
}
