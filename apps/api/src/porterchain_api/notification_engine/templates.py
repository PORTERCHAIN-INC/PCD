"""Notification templates — plain text + branded HTML for email."""

from __future__ import annotations

from typing import Any

from porterchain_api.notification_engine.email_layout import TAGLINE, build_transactional_html

TEMPLATE_META: dict[str, dict[str, str]] = {
    "booking_draft_created": {"category": "booking"},
    "booking_confirmed": {"category": "booking"},
    "consignee_tracking": {"category": "tracking"},
    "checkout_recovery": {"category": "booking"},
    "lead_nurture_intro": {"category": "crm"},
    "lead_nurture_d1": {"category": "crm"},
    "lead_nurture_d7": {"category": "crm"},
    "lead_outbound_followup": {"category": "crm"},
    "lead_outbound_quote_invite": {"category": "crm"},
    "lead_sla_escalation": {"category": "crm"},
    "quote_created": {"category": "booking"},
    "order_created": {"category": "orders"},
    "order_booked": {"category": "orders"},
    "driver_assigned": {"category": "tracking"},
    "job_assigned": {"category": "orders"},
    "order_cancelled": {"category": "orders"},
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
    "merchant_approved": {"category": "security"},
    "merchant_suspended": {"category": "security"},
    "merchant_closed": {"category": "security"},
    "system_alert": {"category": "security"},
    "password_reset": {"category": "security"},
    "staff_activate": {"category": "security"},
    "staff_new_login": {"category": "security"},
    "otp": {"category": "security"},
    "temp_excursion": {"category": "orders"},
    "exception_opened": {"category": "orders"},
    "exception_resolved": {"category": "orders"},
    "order_delayed": {"category": "tracking"},
    "sla_breached": {"category": "orders"},
    "delivery_update": {"category": "tracking"},
}

TEMPLATES: dict[str, dict[str, str]] = {
    "booking_draft_created": {
        "subject": "Booking draft saved",
        "body": "Your booking draft is saved. Continue when ready.",
    },
    "booking_confirmed": {
        "subject": "Your PorterChain delivery is confirmed",
        "body": (
            f"Thanks for booking with PorterChain — {TAGLINE}.\n\n"
            "Tracking: {tracking_number}\nOrder: {order_number}"
        ),
    },
    "consignee_tracking": {
        "subject": "Track your delivery {tracking_number}",
        "body": (
            "A shipment is on the way to you.\n\n"
            "Tracking: {tracking_number}\n"
            "Order: {order_number}\n"
            "Track: {public_track_url}"
        ),
    },
    "checkout_recovery": {
        "subject": "Complete your PorterChain booking",
        "body": "Resume checkout: {recovery_url}\nQuote: {quote_id}",
    },
    "lead_nurture_intro": {
        "subject": "Thanks for reaching out — PorterChain capacity",
        "body": (
            "Hi {contact_name},\n\n"
            "Thanks for your interest in vehicle-and-driver capacity for {company_name}.\n"
            "Reply to this email or continue here: {quote_url}\n\n"
            "Unsubscribe: {unsubscribe_url}\n"
            "— PorterChain"
        ),
    },
    "lead_nurture_d1": {
        "subject": "Next step: reserve capacity with PorterChain",
        "body": (
            "Hi {contact_name},\n\n"
            "Following up on {company_name}'s capacity request.\n"
            "Get a quote: {quote_url}\n\n"
            "Unsubscribe: {unsubscribe_url}\n"
            "— PorterChain"
        ),
    },
    "lead_nurture_d7": {
        "subject": "Still need capacity? PorterChain is ready",
        "body": (
            "Hi {contact_name},\n\n"
            "Checking back on {company_name}'s capacity request.\n"
            "If timing is better now, get a quote: {quote_url}\n\n"
            "Unsubscribe: {unsubscribe_url}\n"
            "— PorterChain"
        ),
    },
    "lead_outbound_followup": {
        "subject": "Following up — PorterChain capacity",
        "body": (
            "Hi {contact_name},\n\n"
            "Thanks for taking my call about vehicle-and-driver capacity for {company_name}.\n"
            "When you're ready, get a quote here: {quote_url}\n\n"
            "Unsubscribe: {unsubscribe_url}\n"
            "— PorterChain"
        ),
    },
    "lead_outbound_quote_invite": {
        "subject": "Your PorterChain capacity quote",
        "body": (
            "Hi {contact_name},\n\n"
            "As discussed, here's the next step for {company_name}:\n"
            "{quote_url}\n\n"
            "Unsubscribe: {unsubscribe_url}\n"
            "— PorterChain"
        ),
    },
    "lead_sla_escalation": {
        "subject": "Unassigned {priority} lead: {company_name}",
        "body": (
            "Lead {lead_id} ({company_name}) is unassigned at {priority} priority.\n"
            "Source: {source} / {channel}\n"
            "Open: {deep_link}"
        ),
    },
    "quote_created": {"subject": "Quote created", "body": "Quote {quote_id} is ready for review."},
    "order_created": {"subject": "Order created", "body": "Order {order_number} has been created."},
    "order_booked": {
        "subject": "Order booked",
        "body": "Order {order_number} is booked. Tracking: {tracking_number}",
    },
    "payment_started": {"subject": "Payment started", "body": "Payment processing for order {order_number}."},
    "payment_receipt": {
        "subject": "PorterChain payment receipt",
        "body": (
            f"Payment successful — PorterChain · {TAGLINE}\n\n"
            "Order: {order_number}\nAmount: {amount_display}\n"
            "Receipt: {receipt_number}\nView: {receipt_url}"
        ),
    },
    "payment_failed": {
        "subject": "Payment failed",
        "body": "Payment for order {order_number} could not be completed.",
    },
    "driver_assigned": {
        "subject": "Driver assigned",
        "body": "A driver has been assigned to {tracking_number}.",
    },
    "job_assigned": {
        "subject": "New job — tap to accept",
        "body": "Job {order_number} ({tracking_number}) is waiting. Open the app to accept.",
    },
    "order_cancelled": {
        "subject": "Order cancelled",
        "body": "Order {order_number} ({tracking_number}) has been cancelled.",
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
    "invoice_ready": {
        "subject": "Invoice {invoice_number} ready",
        "body": (
            f"Invoice ready — PorterChain · {TAGLINE}\n\n"
            "Invoice: {invoice_number}\nOrder: {order_number}\n"
            "Amount: {amount_display}\n"
            "Pay now: {pay_url}\nReceipt: {receipt_url}"
        ),
    },
    "merchant_invoice_ready": {
        "subject": "Merchant invoice {invoice_number} ready",
        "body": (
            f"Merchant invoice ready — PorterChain · {TAGLINE}\n\n"
            "Invoice: {invoice_number}\nMerchant: {merchant_name}\n"
            "Order: {order_number}\nAmount: {amount_display}\n"
            "Pay now: {pay_url}\nReceipt: {receipt_url}"
        ),
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
    "merchant_welcome": {
        "subject": "Welcome to PorterChain Merchant",
        "body": f"Your merchant account is ready — PorterChain · {TAGLINE}",
    },
    "merchant_approved": {
        "subject": "Merchant approved",
        "body": "Merchant {company_name} is now ACTIVE (id {merchant_id}).",
    },
    "merchant_suspended": {
        "subject": "Merchant suspended",
        "body": "Merchant {company_name} was suspended (id {merchant_id}).",
    },
    "merchant_closed": {
        "subject": "Merchant account closed",
        "body": (
            "Merchant {company_name} was closed (id {merchant_id})."
            "{reason_line}"
        ),
    },
    "system_alert": {"subject": "System alert", "body": "{message}"},
    "password_reset": {"subject": "Password reset", "body": "Reset your password: {reset_url}"},
    "staff_activate": {
        "subject": "PorterChain staff sign-in",
        "body": (
            f"PorterChain staff sign-in — {TAGLINE}\n\n"
            "Open this one-time link to sign in to Admin:\n\n{activate_url}\n\n"
            "Expires soon. If you did not request this, ignore this email."
        ),
    },
    "staff_new_login": {
        "subject": "New PorterChain Admin sign-in",
        "body": (
            "A new device signed in to your PorterChain Admin account.\n\n"
            "Device: {device_label}\n"
            "IP: {client_ip}\n\n"
            "If this was you, no action needed. Otherwise revoke sessions here:\n"
            "{security_url}\n"
        ),
    },
    "otp": {"subject": "Verification code", "body": "Your code: {code}"},
    "temp_excursion": {
        "subject": "Temperature excursion — {tracking_number}",
        "body": "Order {order_number} recorded {celsius}°C outside cold-chain limits.",
    },
    "exception_opened": {
        "subject": "Delivery exception — {tracking_number}",
        "body": "Exception ({exception_type}) opened for order {order_number}. {message}",
    },
    "exception_resolved": {
        "subject": "Exception resolved — {tracking_number}",
        "body": "Exception on order {order_number} has been resolved. {message}",
    },
    "order_delayed": {
        "subject": "Delivery delayed — {tracking_number}",
        "body": "Your delivery {tracking_number} is delayed. {message}",
    },
    "sla_breached": {
        "subject": "SLA breached — {tracking_number}",
        "body": "SLA breached for order {order_number}. {message}",
    },
    "delivery_update": {"subject": "Delivery update", "body": "{message}"},
}


def _g(ctx: dict[str, Any], *keys: str, default: str = "") -> str:
    for key in keys:
        val = ctx.get(key)
        if val is not None and str(val).strip() and str(val) != "None":
            return str(val)
    return default


def _html_for(template: str, ctx: dict[str, Any], *, subject: str, body: str) -> str:
    """Build branded HTML for known templates; generic fallback otherwise."""
    order = _g(ctx, "order_number")
    tracking = _g(ctx, "tracking_number")
    amount = _g(ctx, "amount_display")
    invoice = _g(ctx, "invoice_number")
    receipt_no = _g(ctx, "receipt_number")
    receipt_url = _g(ctx, "receipt_url", "invoice_pdf_url")
    pay_url = _g(ctx, "pay_url")
    merchant = _g(ctx, "merchant_name", default="your account")

    if template == "payment_receipt":
        return build_transactional_html(
            eyebrow="Payment confirmed",
            headline="Your payment was successful",
            lead=f"Thank you. PorterChain received your payment. {TAGLINE}.",
            rows=[
                ("Order", order),
                ("Tracking", tracking),
                ("Amount", amount),
                ("Receipt #", receipt_no),
            ],
            cta_label="View receipt" if receipt_url else "",
            cta_url=receipt_url,
            note="Keep this email for your records. A matching invoice appears in your portal.",
            preheader=f"Payment received {amount} for {order or tracking}".strip(),
        )

    if template in ("invoice_ready", "merchant_invoice_ready"):
        who = "your delivery" if template == "invoice_ready" else merchant
        portal = _g(
            ctx,
            "customer_deep_link" if template == "invoice_ready" else "merchant_deep_link",
            "deep_link",
        )
        cta_url = pay_url or portal or receipt_url
        cta_label = "Pay now" if pay_url else ("Open invoice" if cta_url else "")
        return build_transactional_html(
            eyebrow="Invoice ready",
            headline=f"Invoice {invoice or 'is ready'}",
            lead=f"An invoice for {who} is ready to view. {TAGLINE}.",
            rows=[
                ("Invoice", invoice),
                ("Order", order),
                ("Tracking", tracking),
                ("Merchant", merchant if template == "merchant_invoice_ready" else ""),
                ("Amount", amount),
                ("Receipt #", receipt_no),
            ],
            cta_label=cta_label,
            cta_url=cta_url,
            note="Questions about this charge? Reply to this email and our team will help.",
            preheader=f"Invoice {invoice} · {amount}".strip(),
        )

    if template == "booking_confirmed":
        return build_transactional_html(
            eyebrow="Booking confirmed",
            headline="Your capacity is reserved",
            lead=f"Thanks for booking with PorterChain. {TAGLINE}.",
            rows=[
                ("Tracking", tracking),
                ("Order", order),
                ("Invoice", invoice),
                ("Amount", amount),
            ],
            note="We’ll notify you when a driver is assigned.",
            preheader=f"Booking confirmed · {tracking or order}",
        )

    if template == "consignee_tracking":
        track_url = _g(ctx, "public_track_url")
        shipper = _g(ctx, "merchant_name")
        return build_transactional_html(
            eyebrow="Shipment update",
            headline="Track your delivery",
            lead=(
                f"{shipper} booked a delivery to you. {TAGLINE}."
                if shipper
                else f"A delivery is booked for you. {TAGLINE}."
            ),
            rows=[("Tracking", tracking), ("Order", order)],
            cta_label="Track this shipment" if track_url else "",
            cta_url=track_url,
            note="This link opens the public track page. You do not need a login.",
            preheader=f"Track {tracking or order}",
        )

    if template == "staff_activate":
        url = _g(ctx, "activate_url")
        return build_transactional_html(
            eyebrow="Staff access",
            headline="Sign in to PorterChain Admin",
            lead=f"Use the secure one-time link below to activate your staff session. {TAGLINE}.",
            cta_label="Activate staff sign-in",
            cta_url=url,
            note="This link expires soon. If you did not request it, you can ignore this email.",
            preheader="Your PorterChain staff sign-in link",
        )

    if template == "staff_new_login":
        security = _g(ctx, "security_url")
        return build_transactional_html(
            eyebrow="Security alert",
            headline="New Admin sign-in detected",
            lead="A device we have not seen recently signed in to your staff account.",
            rows=[
                ("Device", _g(ctx, "device_label") or "Unknown"),
                ("IP", _g(ctx, "client_ip") or "unknown"),
            ],
            cta_label="Review sessions",
            cta_url=security,
            note="If this was not you, revoke other devices immediately and re-enroll a passkey.",
            preheader="New PorterChain Admin sign-in",
        )

    if template == "delivered":
        return build_transactional_html(
            eyebrow="Delivered",
            headline="Your shipment has arrived",
            lead=f"Order {order or tracking} was delivered successfully. {TAGLINE}.",
            rows=[("Order", order), ("Tracking", tracking)],
            cta_label="Track this shipment" if _g(ctx, "public_track_url") else "",
            cta_url=_g(ctx, "public_track_url"),
            preheader=f"Delivered · {tracking or order}",
        )

    if template == "payment_failed":
        return build_transactional_html(
            eyebrow="Payment issue",
            headline="We couldn’t complete your payment",
            lead="Please retry checkout or use another card. Your quote may still be available.",
            rows=[("Order", order)],
            note="Need help? Reply to this email.",
            preheader="Payment failed — action needed",
        )

    if template == "merchant_welcome":
        return build_transactional_html(
            eyebrow="Welcome",
            headline="Your merchant account is ready",
            lead=f"You can book capacity, import routes, and track deliveries in the merchant portal. {TAGLINE}.",
            preheader="Welcome to PorterChain Merchant",
        )

    if template == "password_reset":
        url = _g(ctx, "reset_url")
        return build_transactional_html(
            eyebrow="Security",
            headline="Reset your password",
            lead="Use the button below to choose a new password.",
            cta_label="Reset password",
            cta_url=url,
            note="If you did not request this, ignore this email.",
            preheader="Password reset link",
        )

    if template == "checkout_recovery":
        url = _g(ctx, "recovery_url")
        return build_transactional_html(
            eyebrow="Finish booking",
            headline="Your quote is waiting",
            lead=f"Complete checkout to reserve capacity. {TAGLINE}.",
            rows=[("Quote", _g(ctx, "quote_id"))],
            cta_label="Resume checkout",
            cta_url=url,
            preheader="Complete your PorterChain booking",
        )

    if template in (
        "lead_nurture_intro",
        "lead_nurture_d1",
        "lead_nurture_d7",
        "lead_outbound_followup",
        "lead_outbound_quote_invite",
    ):
        url = _g(ctx, "quote_url")
        company = _g(ctx, "company_name") or "your business"
        unsub = _g(ctx, "unsubscribe_url")
        headline = {
            "lead_nurture_intro": "Vehicle + driver capacity",
            "lead_nurture_d1": "Ready for a quote?",
            "lead_nurture_d7": "Still planning capacity?",
            "lead_outbound_followup": "Thanks for the call",
            "lead_outbound_quote_invite": "Your next step",
        }.get(template, "Ready for a quote?")
        return build_transactional_html(
            eyebrow="Capacity network",
            headline=headline,
            lead=f"PorterChain for {company}. {TAGLINE}.",
            rows=[
                ("Contact", _g(ctx, "contact_name")),
                ("Company", company),
            ],
            cta_label="Get a quote",
            cta_url=url,
            note=f"Unsubscribe: {unsub}" if unsub else "",
            preheader="PorterChain capacity follow-up",
        )

    if template == "lead_sla_escalation":
        headline = str(ctx.get("title") or f"Unassigned {_g(ctx, 'priority')} lead")
        return build_transactional_html(
            eyebrow="Lead Agent",
            headline=headline,
            lead=f"{_g(ctx, 'company_name') or 'Lead'} needs assignment.",
            rows=[
                ("Lead", _g(ctx, "lead_id")),
                ("Source", _g(ctx, "source")),
                ("Channel", _g(ctx, "channel")),
            ],
            cta_label="Open lead",
            cta_url=_g(ctx, "deep_link") or "#",
            preheader="Unassigned high-priority lead",
        )

    parcel_mail = {
        "order_booked": ("Booked", "Your delivery is booked"),
        "parcel_picked_up": ("Picked up", "Your parcel has been picked up"),
        "order_cancelled": ("Cancelled", "This delivery was cancelled"),
        "exception_opened": ("Exception", "There is a problem with this delivery"),
        "order_delayed": ("Delayed", "This delivery is running late"),
        "sla_breached": ("SLA", "This delivery missed its promise"),
    }
    if template in parcel_mail:
        eyebrow, headline = parcel_mail[template]
        track_url = _g(ctx, "public_track_url")
        return build_transactional_html(
            eyebrow=eyebrow,
            headline=headline,
            lead=body or headline,
            rows=[("Order", order), ("Tracking", tracking)],
            cta_label="Track this shipment" if track_url else "",
            cta_url=track_url,
            preheader=f"{headline} · {tracking or order}",
        )

    # Generic branded shell for remaining templates
    first_line = body.split("\n", 1)[0].strip() if body else subject
    return build_transactional_html(
        eyebrow="PorterChain",
        headline=subject,
        lead=first_line or TAGLINE,
        rows=[
            ("Order", order),
            ("Tracking", tracking),
            ("Details", body if body and body != first_line else ""),
        ],
        note=TAGLINE,
        preheader=first_line or subject,
    )


def template_meta(template: str) -> dict[str, str]:
    return TEMPLATE_META.get(template, {"category": "operational"})


def render_template(template: str, context: dict[str, Any]) -> tuple[str, str]:
    """Return (subject, plain_text) — used by SMS/push and legacy callers."""
    subject, text, _html = render_email(template, context)
    return subject, text


def render_email(template: str, context: dict[str, Any]) -> tuple[str, str, str]:
    """Return (subject, plain_text, html)."""
    spec = TEMPLATES.get(template, {"subject": "PorterChain notification", "body": "{message}"})
    safe = {k: ("" if v is None else str(v)) for k, v in context.items()}
    # Ensure HTML format placeholders never KeyError
    for key in (
        "order_number",
        "tracking_number",
        "amount_display",
        "invoice_number",
        "receipt_number",
        "receipt_url",
        "pay_url",
        "merchant_name",
        "activate_url",
        "reset_url",
        "recovery_url",
        "public_track_url",
        "quote_id",
        "message",
        "title",
        "body",
        "code",
        "claim_number",
        "claim_type",
        "ticket_number",
        "subject",
        "status",
        "celsius",
        "route_id",
        "stops_count",
        "company_name",
        "merchant_id",
        "reason",
        "reason_line",
        "unsubscribe_url",
        "contact_name",
        "quote_url",
        "lead_id",
        "priority",
        "source",
        "channel",
        "deep_link",
    ):
        safe.setdefault(key, "")
    try:
        subject = spec["subject"].format(**safe)
        body = spec["body"].format(**safe)
    except KeyError:
        subject = spec["subject"]
        body = spec["body"]
    if template == "lead_sla_escalation" and context.get("title"):
        subject = str(context["title"])
    if template == "lead_sla_escalation" and "notice_body" in context:
        body = str(context["notice_body"])
    track = context.get("public_track_url")
    if isinstance(track, str) and track.startswith("http") and track not in body:
        body = f"{body}\n\nTrack: {track}"
    html_body = _html_for(template, context, subject=subject, body=body)
    return subject, body, html_body
