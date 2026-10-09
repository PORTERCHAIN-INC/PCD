"""Merchant API events per EVENT_FLOW.md.

Canonical billing event for notifications is ``merchant.billed``
(``DomainEventType.MERCHANT_BILLED``). ``merchant.invoice_generated`` is kept as
a compatibility alias and is wired to the same notification router path.
"""

MERCHANT_APPROVED = "merchant.approved"
MERCHANT_ACTIVATED = "merchant.activated"
MERCHANT_SUSPENDED = "merchant.suspended"
MERCHANT_BOOKING_CREATED = "merchant.booking_created"
MERCHANT_BULK_BOOKING_CREATED = "merchant.bulk_booking_created"
# Prefer merchant.billed for new emitters; alias retained for AR/gateway contracts.
MERCHANT_INVOICE_GENERATED = "merchant.invoice_generated"
MERCHANT_BILLED = "merchant.billed"
MERCHANT_PAYMENT_RECEIVED = "merchant.payment_received"
MERCHANT_PARCELS_AMENDED = "merchant.parcels_amended"
API_KEY_GENERATED = "merchant.api_key_generated"
