"""Stripe helper unit tests."""

from porterchain_api.config import Settings
from porterchain_api.services.stripe_service import handle_checkout_completed


def test_handle_checkout_completed_extracts_metadata() -> None:
    settings = Settings(app_env="local")
    session = {
        "metadata": {
            "quote_id": "quote_abc",
            "customer_id": "cust_abc",
            "payment_id": "pay_abc",
        },
        "payment_intent": "pi_123",
        "payment_method_types": ["card"],
        "amount_total": 4500,
        "currency": "cad",
        "total_details": {"amount_tax": 100},
    }
    meta = handle_checkout_completed(settings, session)
    assert meta is not None
    assert meta["quote_id"] == "quote_abc"
    assert meta["payment_intent"] == "pi_123"
    assert meta["tax_cents"] == 100
