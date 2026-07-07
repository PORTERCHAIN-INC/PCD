"""Booking engine domain events — aligned with EVENT_FLOW.md and booking spec."""

# Quote
QUOTE_CREATED = "quote.created"
QUOTE_UPDATED = "quote.updated"
QUOTE_ACCEPTED = "quote.accepted"
QUOTE_EXPIRED = "quote.expired"

# Customer
CUSTOMER_REGISTERED = "customer.registered"
CUSTOMER_AUTHENTICATED = "customer.authenticated"

# Payment
PAYMENT_STARTED = "payment.started"
PAYMENT_SUCCEEDED = "payment.succeeded"
PAYMENT_FAILED = "payment.failed"

# Booking & order
BOOKING_CREATED = "booking.created"
BOOKING_CONFIRMED = "booking.confirmed"
ORDER_CREATED = "order.created"
ORDER_BOOKED = "order.booked"
ORDER_DISPATCH_REQUESTED = "order.dispatch_requested"
ORDER_DISPATCH_READY = "order.dispatch_ready"
ORDER_INVOICED = "order.invoiced"

# Invoice & notifications
INVOICE_CREATED = "invoice.created"
NOTIFICATION_SENT = "notification.sent"

# Checkout
CHECKOUT_STARTED = "checkout.started"
CHECKOUT_ABANDONED = "checkout.abandoned"
BOOKING_STARTED = "booking.started"

# Consent / compliance
BOOKING_CONSENT_RECORDED = "booking.consent_recorded"
BOOKING_DRAFT_RESTORED = "booking.draft_restored"
RECEIPT_GENERATED = "receipt.generated"
DISPATCH_QUEUED = "dispatch.queued"

# Fleetbase
FLEETBASE_ORDER_CREATED = "fleetbase.order_created"

# Visitor
VISITOR_SESSION_STARTED = "visitor.session_started"
SESSION_MERGED = "visitor.session_merged"
LEAD_CREATED = "lead.created"
