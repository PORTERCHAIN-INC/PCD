from porterchain_api.config import Settings
from porterchain_api.models import Customer, Quote

import stripe


def _checkout_urls(settings: Settings, checkout_channel: str) -> tuple[str, str]:
    if checkout_channel == "customer":
        return settings.customer_checkout_success_url, settings.customer_checkout_cancel_url
    return settings.retail_checkout_success_url, settings.retail_checkout_cancel_url


def ensure_stripe_customer(settings: Settings, customer: Customer) -> str | None:
    """C-18: create or reuse a Stripe Customer and persist the id on the PC row."""
    if not settings.stripe_secret:
        return None
    stripe.api_key = settings.stripe_secret
    if customer.stripe_customer_id:
        return customer.stripe_customer_id
    if not customer.email:
        return None
    created = stripe.Customer.create(
        email=customer.email,
        phone=customer.phone or None,
        metadata={"porterchain_customer_id": customer.id},
    )
    customer.stripe_customer_id = created.id
    return created.id


def create_checkout_session(
    settings: Settings,
    quote: Quote,
    customer: Customer,
    payment_id: str | None = None,
    booking_draft_id: str | None = None,
    *,
    checkout_channel: str = "retail",
) -> tuple[str, str]:
    stripe.api_key = settings.stripe_secret
    metadata = {
        "quote_id": quote.id,
        "customer_id": customer.id,
        "payment_id": payment_id or "",
        "booking_draft_id": booking_draft_id or "",
        "tracking_prefix": "PC",
        "checkout_channel": checkout_channel,
    }
    success_base, cancel_base = _checkout_urls(settings, checkout_channel)
    stripe_customer_id = ensure_stripe_customer(settings, customer)
    session_kwargs: dict = {
        "mode": "payment",
        # Apple Pay & Google Pay are presented automatically by Stripe Checkout
        # when "card" is enabled and the domain is registered — no extra config.
        "payment_method_types": ["card"],
        "phone_number_collection": {"enabled": True},
        "billing_address_collection": "auto",
        "line_items": [
            {
                "price_data": {
                    "currency": quote.currency,
                    "unit_amount": quote.amount_cents,
                    "product_data": {
                        "name": "Porterchain delivery",
                        "description": f"Quote {quote.id}",
                    },
                },
                "quantity": 1,
            }
        ],
        "success_url": f"{success_base}?quote_id={quote.id}",
        "cancel_url": f"{cancel_base}?quote_id={quote.id}",
        "metadata": metadata,
        # Propagate identifiers onto the PaymentIntent for reconciliation.
        "payment_intent_data": {"metadata": metadata},
    }
    if stripe_customer_id:
        session_kwargs["customer"] = stripe_customer_id
    else:
        session_kwargs["customer_email"] = customer.email
    session = stripe.checkout.Session.create(**session_kwargs)
    if not session.url:
        raise RuntimeError("stripe_session_missing_url")
    return session.url, session.id


def handle_checkout_completed(settings: Settings, session: dict) -> dict | None:
    metadata = session.get("metadata") or {}
    total_details = session.get("total_details") or {}
    methods = session.get("payment_method_types") or []
    payment_intent = session.get("payment_intent")
    return {
        "quote_id": metadata.get("quote_id"),
        "customer_id": metadata.get("customer_id"),
        "payment_id": metadata.get("payment_id"),
        "booking_draft_id": metadata.get("booking_draft_id"),
        "payment_intent": payment_intent,
        "transaction_id": payment_intent,
        "receipt_url": session.get("receipt_url"),
        "payment_method": (methods[0] if methods else None),
        "amount_total": session.get("amount_total"),
        "currency": session.get("currency"),
        "tax_cents": total_details.get("amount_tax"),
    }


def create_refund(settings: Settings, order, amount_cents: int | None = None) -> str | None:
    if not settings.stripe_secret or not order.stripe_payment_intent_id:
        return None
    stripe.api_key = settings.stripe_secret
    refund = stripe.Refund.create(
        payment_intent=order.stripe_payment_intent_id,
        amount=amount_cents,
    )
    return refund.id
