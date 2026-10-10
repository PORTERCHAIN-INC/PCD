from porterchain_api.config import Settings
from porterchain_api.booking_models import Customer, Quote
from porterchain_services.stripe import sdk as stripe_sdk

StripeSignatureError = stripe_sdk.StripeSdkSignatureError

_DUMMY_STRIPE_MARKERS = ("_local_", "_mock_")


def is_dummy_stripe_id(value: str | None) -> bool:
    """Local seed placeholders (cus_local_*, acct_mock_*) are not Stripe objects."""
    raw = (value or "").strip()
    if not raw:
        return False
    return any(marker in raw for marker in _DUMMY_STRIPE_MARKERS)


def _checkout_urls(settings: Settings, checkout_channel: str) -> tuple[str, str]:
    if checkout_channel == "customer":
        return settings.customer_checkout_success_url, settings.customer_checkout_cancel_url
    return settings.retail_checkout_success_url, settings.retail_checkout_cancel_url


def ensure_stripe_customer(settings: Settings, customer: Customer) -> str | None:
    """C-18: create or reuse a Stripe Customer and persist the id on the PC row."""
    if not settings.stripe_secret:
        return None
    stripe_sdk.configure(settings.stripe_secret)
    existing = (customer.stripe_customer_id or "").strip() or None
    if existing and not is_dummy_stripe_id(existing):
        return existing
    if not customer.email:
        return None
    created = stripe_sdk.create_customer(
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
    stripe_sdk.configure(settings.stripe_secret)
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
    goods = quote.parcels if isinstance(getattr(quote, "parcels", None), dict) else {}
    if goods.get("booking_mode") == "vehicle":
        description = f"{quote.vehicle_class} · Whole vehicle"
    else:
        count = len(goods.get("items") or [])
        description = f"{quote.vehicle_class} · {count or 1} parcel{'s' if count != 1 else ''}"
    session_kwargs: dict = {
        "mode": "payment",
        # Payment methods come from the Stripe Dashboard. Sending
        # payment_method_types is rejected on current Checkout API versions.
        "phone_number_collection": {"enabled": True},
        "billing_address_collection": "auto",
        "line_items": [
            {
                "price_data": {
                    "currency": quote.currency,
                    "unit_amount": quote.amount_cents,
                    "product_data": {
                        "name": "Porterchain delivery",
                        "description": description,
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
        # Stripe keeps the card. Porterchain never stores the number.
        session_kwargs["saved_payment_method_options"] = {"payment_method_save": "enabled"}
    else:
        session_kwargs["customer_email"] = customer.email
    session = stripe_sdk.create_checkout_session(**session_kwargs)
    if not session.url:
        raise RuntimeError("stripe_session_missing_url")
    return session.url, session.id


def create_invoice_checkout_session(
    settings: Settings,
    *,
    amount_cents: int,
    currency: str,
    invoice_id: str,
    invoice_number: str,
    merchant_id: str,
    payment_id: str,
    customer_email: str | None,
) -> tuple[str, str]:
    """Stripe Checkout for merchant AR invoice pay (server-locked amount)."""
    stripe_sdk.configure(settings.stripe_secret)
    base = settings.merchant_portal_url.rstrip("/")
    success_url = f"{base}/billing?paid=1&invoice_id={invoice_id}"
    cancel_url = f"{base}/billing?cancelled=1&invoice_id={invoice_id}"
    metadata = {
        "invoice_id": invoice_id,
        "invoice_number": invoice_number,
        "merchant_id": merchant_id,
        "payment_id": payment_id,
        "checkout_channel": "merchant_invoice",
    }
    session_kwargs: dict = {
        "mode": "payment",
        "line_items": [
            {
                "price_data": {
                    "currency": (currency or "cad").lower(),
                    "unit_amount": int(amount_cents),
                    "product_data": {
                        "name": f"PorterChain invoice {invoice_number}",
                        "description": f"Invoice {invoice_number}",
                    },
                },
                "quantity": 1,
            }
        ],
        "success_url": success_url,
        "cancel_url": cancel_url,
        "metadata": metadata,
        "payment_intent_data": {"metadata": metadata},
    }
    if customer_email:
        session_kwargs["customer_email"] = customer_email
    session = stripe_sdk.create_checkout_session(**session_kwargs)
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
        "invoice_id": metadata.get("invoice_id"),
        "merchant_id": metadata.get("merchant_id"),
        "checkout_channel": metadata.get("checkout_channel"),
        "kind": metadata.get("kind"),
        "order_id": metadata.get("order_id"),
        "stop_leg": metadata.get("stop_leg"),
        "payment_intent": payment_intent,
        "transaction_id": payment_intent,
        "receipt_url": session.get("receipt_url"),
        "payment_method": (methods[0] if methods else None),
        "amount_total": session.get("amount_total"),
        "currency": session.get("currency"),
        "tax_cents": total_details.get("amount_tax"),
    }


def create_refund(
    settings: Settings,
    order,
    amount_cents: int | None = None,
    *,
    idempotency_key: str | None = None,
) -> str | None:
    if not settings.stripe_secret or not order.stripe_payment_intent_id:
        return None
    stripe_sdk.configure(settings.stripe_secret)
    kwargs: dict = {
        "payment_intent": order.stripe_payment_intent_id,
        "amount": amount_cents,
    }
    if idempotency_key:
        kwargs["idempotency_key"] = idempotency_key
    refund = stripe_sdk.create_refund(**kwargs)
    return refund.id


def list_payout_balance_transactions(settings: Settings, payout_id: str) -> list[dict]:
    """Read-only: balance transactions in a Stripe payout (for reconciliation)."""
    if not settings.stripe_secret:
        return []
    stripe_sdk.configure(settings.stripe_secret)
    return stripe_sdk.list_payout_balance_transactions(payout_id)


def construct_webhook_event(payload: bytes, sig_header: str | None, settings: Settings):
    """Verify Stripe webhook payload. Routers must not import stripe."""
    if not settings.stripe_webhook_secret:
        raise RuntimeError("stripe_webhook_not_configured")
    return stripe_sdk.construct_webhook_event(payload, sig_header, settings.stripe_webhook_secret)


def create_identity_verification_session(
    settings: Settings,
    *,
    driver_id: str,
    return_url: str,
) -> dict:
    """Start Stripe Identity document+selfie session for driver license verification."""
    stripe_sdk.configure(settings.stripe_secret)
    session = stripe_sdk.create_identity_verification_session(
        type="document",
        options={
            "document": {
                "allowed_types": ["driving_license"],
                "require_matching_selfie": True,
            },
        },
        metadata={
            "porterchain_driver_id": driver_id,
            "purpose": "driver_license",
        },
        return_url=return_url,
    )
    return {
        "id": session.id,
        "url": session.url,
        "client_secret": session.client_secret,
        "status": session.status,
    }


def retrieve_identity_verification_session(settings: Settings, session_id: str) -> dict:
    stripe_sdk.configure(settings.stripe_secret)
    session = stripe_sdk.retrieve_identity_verification_session(session_id)
    return session.to_dict() if hasattr(session, "to_dict") else dict(session)


def retrieve_checkout_session(settings: Settings, session_id: str) -> dict:
    stripe_sdk.configure(settings.stripe_secret)
    session = stripe_sdk.retrieve_checkout_session(session_id)
    return session.to_dict()


def retrieve_balance(settings: Settings) -> None:
    stripe_sdk.configure(settings.stripe_secret)
    stripe_sdk.retrieve_balance()


def create_connect_express_account(settings: Settings, *, email: str | None, merchant_id: str) -> str:
    stripe_sdk.configure(settings.stripe_secret)
    account = stripe_sdk.create_connect_account(
        type="express",
        country="CA",
        email=email or None,
        capabilities={
            "card_payments": {"requested": True},
            "transfers": {"requested": True},
        },
        metadata={"porterchain_merchant_id": merchant_id},
    )
    return account.id


def create_connect_account_link(
    settings: Settings,
    *,
    account_id: str,
) -> str:
    stripe_sdk.configure(settings.stripe_secret)
    link = stripe_sdk.create_account_link(
        account=account_id,
        refresh_url=settings.stripe_connect_refresh_url,
        return_url=settings.stripe_connect_return_url,
        type="account_onboarding",
    )
    return link.url


def create_cod_checkout_session(
    settings: Settings,
    *,
    amount_cents: int,
    currency: str,
    application_fee_cents: int,
    destination_account_id: str,
    metadata: dict[str, str],
    success_url: str,
    cancel_url: str,
    product_name: str,
    product_description: str,
) -> tuple[str, str]:
    stripe_sdk.configure(settings.stripe_secret)
    session = stripe_sdk.create_checkout_session(
        mode="payment",
        line_items=[
            {
                "price_data": {
                    "currency": currency,
                    "unit_amount": amount_cents,
                    "product_data": {
                        "name": product_name,
                        "description": product_description,
                    },
                },
                "quantity": 1,
            }
        ],
        success_url=success_url,
        cancel_url=cancel_url,
        metadata=metadata,
        payment_intent_data={
            "metadata": metadata,
            "application_fee_amount": application_fee_cents,
            "transfer_data": {"destination": destination_account_id},
        },
    )
    if not session.url:
        raise RuntimeError("stripe_session_missing_url")
    return session.url, session.id
