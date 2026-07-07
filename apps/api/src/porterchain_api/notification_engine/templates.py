"""Notification templates — single source for worker + API."""

from __future__ import annotations

from typing import Any

TEMPLATE_META: dict[str, dict[str, str]] = {
    "booking_draft_created": {"category": "booking"},
    "booking_confirmed": {"category": "booking"},
    "checkout_recovery": {"category": "booking"},
    "quote_created": {"category": "booking"},
    "order_created": {"category": "orders"},
    "order_booked": {"category": "orders"},
    "driver_assigned": {"category": "tracking"},
    "driver_accepted": {"category": "tracking"},
    "driver_rejected": {"category": "tracking"},
    "pickup_started": {"category": "tracking"},
    "parcel_picked_up": {"category": "tracking"},
    "in_transit": {"category": "tracking"},
    "near_delivery": {"category": "tracking"},
    "delivered": {"category": "tracking"},
    "tracking_update": {"category": "tracking"},
    "pod_uploaded": {"category": "tracking"},
    "driver_alert": {"category": "orders"},
    "driver_route_changed": {"category": "tracking"},
    "payment_started": {"category": "payments"},
    "payment_receipt": {"category": "payments"},
    "payment_failed": {"category": "payments"},
    "invoice_ready": {"category": "invoices"},
    "merchant_invoice_ready": {"category": "invoices"},
    "refund_processed": {"category": "payments"},
    "claim_opened": {"category": "claims"},
    "claim_updated": {"category": "claims"},
    "support_ticket_created": {"category": "support"},
    "support_reply": {"category": "support"},
    "merchant_welcome": {"category": "marketing"},
    "system_alert": {"category": "security"},
    "password_reset": {"category": "security"},
    "otp": {"category": "security"},
    "delivery_update": {"category": "tracking"},
}

TEMPLATES: dict[str, dict[str, str]] = {
    "booking_draft_created": {
        "subject": "Booking draft saved",
        "body": "Your booking draft is saved. Continue when ready.",
    },
    "booking_confirmed": {
        "subject": "Your Porterchain delivery is confirmed",
        "body": "Thanks for booking with Porterchain.\n\nTracking: {tracking_number}\nOrder: {order_number}",
    },
    "checkout_recovery": {
        "subject": "Complete your Porterchain booking",
        "body": "Resume checkout: {recovery_url}\nQuote: {quote_id}",
    },
    "quote_created": {"subject": "Quote created", "body": "Quote {quote_id} is ready for review."},
    "order_created": {"subject": "Order created", "body": "Order {order_number} has been created."},
    "order_booked": {
        "subject": "Order booked",
        "body": "Order {order_number} is booked. Tracking: {tracking_number}",
    },
    "payment_started": {"subject": "Payment started", "body": "Payment processing for order {order_number}."},
    "payment_receipt": {
        "subject": "Porterchain payment receipt",
        "body": "Payment received for order {order_number}. Amount: {amount_display}",
    },
    "payment_failed": {
        "subject": "Payment failed",
        "body": "Payment for order {order_number} could not be completed.",
    },
    "driver_assigned": {
        "subject": "Driver assigned",
        "body": "A driver has been assigned to {tracking_number}.",
    },
    "driver_accepted": {"subject": "Driver accepted job", "body": "Driver accepted order {order_number}."},
    "driver_rejected": {"subject": "Driver rejected job", "body": "Driver rejected order {order_number}."},
    "pickup_started": {"subject": "Driver arrived for pickup", "body": "Driver arrived for order {order_number}."},
    "parcel_picked_up": {"subject": "Parcel picked up", "body": "Parcel picked up for {tracking_number}."},
    "in_transit": {"subject": "In transit", "body": "Your delivery {tracking_number} is in transit."},
    "near_delivery": {"subject": "Near delivery", "body": "Driver is near the dropoff for {tracking_number}."},
    "delivered": {"subject": "Delivered", "body": "Order {order_number} has been delivered."},
    "tracking_update": {"subject": "Tracking update", "body": "{message}"},
    "pod_uploaded": {"subject": "Proof of delivery uploaded", "body": "POD uploaded for {order_number}."},
    "driver_alert": {"subject": "{title}", "body": "{body}"},
    "driver_route_changed": {
        "subject": "Route updated",
        "body": "Your route {route_id} has been updated. {stops_count} stops assigned.",
    },
    "invoice_ready": {"subject": "Invoice ready", "body": "Invoice {invoice_number} is available."},
    "merchant_invoice_ready": {
        "subject": "Merchant invoice ready",
        "body": "Statement {invoice_number} is ready for merchant {merchant_name}.",
    },
    "refund_processed": {"subject": "Refund processed", "body": "Refund processed for order {order_number}."},
    "claim_opened": {
        "subject": "Claim opened — {claim_number}",
        "body": "Claim ({claim_type}) opened for order {order_number}.",
    },
    "claim_updated": {"subject": "Claim updated", "body": "Claim {claim_number} status: {status}."},
    "support_ticket_created": {
        "subject": "Support ticket {ticket_number}",
        "body": "Ticket created: {subject}",
    },
    "support_reply": {"subject": "Support reply", "body": "New reply on ticket {ticket_number}."},
    "merchant_welcome": {"subject": "Welcome to Porterchain Merchant", "body": "Your merchant account is ready."},
    "system_alert": {"subject": "System alert", "body": "{message}"},
    "password_reset": {"subject": "Password reset", "body": "Reset your password: {reset_url}"},
    "otp": {"subject": "Verification code", "body": "Your code: {code}"},
    "delivery_update": {"subject": "Delivery update", "body": "{message}"},
}


def template_meta(template: str) -> dict[str, str]:
    return TEMPLATE_META.get(template, {"category": "operational"})


def render_template(template: str, context: dict[str, Any]) -> tuple[str, str]:
    spec = TEMPLATES.get(template, {"subject": "Porterchain notification", "body": "{message}"})
    safe = {k: str(v) for k, v in context.items()}
    try:
        return spec["subject"].format(**safe), spec["body"].format(**safe)
    except KeyError:
        return spec["subject"], spec["body"]
