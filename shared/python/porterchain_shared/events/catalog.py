"""Domain event catalog — canonical event types for Porterchain event bus."""

from enum import StrEnum

# Bump when adding/removing/renaming events (§3.3.4); keep in sync with packages/events.
CATALOG_VERSION = "1.2.0"


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
    MERCHANT_SUSPENDED = "merchant.suspended"
    MERCHANT_BILLED = "merchant.billed"

    # Payment
    PAYMENT_STARTED = "payment.started"
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
    ORDER_NEAR_DELIVERY = "order.near_delivery"
    ORDER_LOCATION_UPDATED = "order.tracking_updated"
    ORDER_TEMP_EXCURSION = "order.temp_excursion"
    EXCEPTION_OPENED = "exception.opened"
    EXCEPTION_RESOLVED = "exception.resolved"
    ORDER_DELAYED = "order.delayed"
    SLA_BREACHED = "sla.breached"

    # Phase 2 stubs — no consumers yet (ADR-010; Route Center deferred)
    ROUTE_OPTIMIZED = "route.optimized"
    DISPATCH_RECOMMENDATION = "dispatch.recommendation"
    ETA_PREDICTED = "eta.predicted"

    # Optimize lifecycle — PorterChain day plan (OR-Tools)
    OPTIMIZE_ENQUEUED = "optimize.enqueued"
    OPTIMIZE_READY = "optimize.ready"
    OPTIMIZE_APPLIED = "optimize.applied"
    OPTIMIZE_REJECTED = "optimize.rejected"
    OPTIMIZE_ROLLED_BACK = "optimize.rolled_back"

    # Financial
    REFUND_REQUESTED = "refund.requested"
    REFUND_ISSUED = "refund.issued"
    DRIVER_PAYOUT_CREATED = "driver.payout_created"

    # Claims
    CLAIM_OPENED = "claim.opened"
    CLAIM_RESOLVED = "claim.resolved"

    # Support
    SUPPORT_TICKET_CREATED = "support.ticket_created"

    # Privacy / compliance
    PRIVACY_DELETE_REQUESTED = "privacy.delete_requested"

    # Booking draft
    BOOKING_DRAFT_CREATED = "booking_draft.draft_created"

    # Notifications & webhooks
    NOTIFICATION_QUEUED = "notification.queued"
    NOTIFICATION_SENT = "notification.sent"
    WEBHOOK_RECEIVED = "webhook.received"

    # Retired vendor sync names — kept so old envelopes still deserialize.
    # Nothing emits these after the PorterChain day-plan cutover.
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
    "CustomerAuthenticated": DomainEventType.CUSTOMER_AUTHENTICATED,
    "PaymentStarted": DomainEventType.PAYMENT_STARTED,
    "MerchantApproved": DomainEventType.MERCHANT_APPROVED,
    "MerchantSuspended": DomainEventType.MERCHANT_SUSPENDED,
    "PaymentSucceeded": DomainEventType.PAYMENT_SUCCEEDED,
    "BookingConfirmed": DomainEventType.BOOKING_CONFIRMED,
    "OrderCreated": DomainEventType.ORDER_CREATED,
    "FleetbaseOrderCreated": DomainEventType.FLEETBASE_ORDER_CREATED,
    "BookingDraftCreated": DomainEventType.BOOKING_DRAFT_CREATED,
    "SupportTicketCreated": DomainEventType.SUPPORT_TICKET_CREATED,
    "PickupStarted": DomainEventType.DRIVER_ARRIVED_PICKUP,
    "PickedUp": DomainEventType.PARCEL_PICKED_UP,
    "Delivered": DomainEventType.PARCEL_DELIVERED,
    "PODCompleted": DomainEventType.PROOF_COMPLETED,
    "NearDelivery": DomainEventType.ORDER_NEAR_DELIVERY,
    "LocationUpdated": DomainEventType.ORDER_LOCATION_UPDATED,
    "RouteOptimized": DomainEventType.ROUTE_OPTIMIZED,
    "OptimizeEnqueued": DomainEventType.OPTIMIZE_ENQUEUED,
    "OptimizeReady": DomainEventType.OPTIMIZE_READY,
    "OptimizeApplied": DomainEventType.OPTIMIZE_APPLIED,
    "OptimizeRejected": DomainEventType.OPTIMIZE_REJECTED,
    "OptimizeRolledBack": DomainEventType.OPTIMIZE_ROLLED_BACK,
    "FleetbaseSync": DomainEventType.FLEETBASE_STATUS_UPDATED,
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
    "ExceptionOpened": DomainEventType.EXCEPTION_OPENED,
    "ExceptionResolved": DomainEventType.EXCEPTION_RESOLVED,
    "OrderDelayed": DomainEventType.ORDER_DELAYED,
    "SlaBreached": DomainEventType.SLA_BREACHED,
    "NotificationQueued": DomainEventType.NOTIFICATION_QUEUED,
    "NotificationSent": DomainEventType.NOTIFICATION_SENT,
    "WebhookReceived": DomainEventType.WEBHOOK_RECEIVED,
}
