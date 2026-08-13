"""Stripe checkout URL channel routing."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from porterchain_api.config import Settings
from porterchain_api.models import Customer, Quote
from porterchain_api.services.stripe_service import create_checkout_session


def test_create_checkout_session_customer_channel() -> None:
    settings = Settings(
        stripe_secret="sk_test_x",
        retail_checkout_success_url="http://localhost:3000/en/book/success",
        retail_checkout_cancel_url="http://localhost:3000/en/book/continue",
        customer_portal_url="http://localhost:3004",
    )
    quote = Quote(id="q-1", amount_cents=1000, currency="cad")
    customer = Customer(id="c-1", email="test@example.com", stripe_customer_id="cus_test")

    session = MagicMock()
    session.url = "https://checkout.stripe.test/session"
    session.id = "cs_test"

    with patch("porterchain_api.services.stripe_service.stripe.checkout.Session.create", return_value=session) as create:
        create_checkout_session(settings, quote, customer, checkout_channel="customer")

    kwargs = create.call_args.kwargs
    assert kwargs["success_url"] == "http://localhost:3004/book/success?quote_id=q-1"
    assert kwargs["cancel_url"] == "http://localhost:3004/book?quote_id=q-1"
    assert kwargs["metadata"]["checkout_channel"] == "customer"
