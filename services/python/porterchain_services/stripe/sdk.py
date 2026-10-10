"""The only PorterChain module that `import stripe`s.

FastAPI `stripe_service` and the gateway `StripeService` call these helpers.
Do not `import stripe` from engines, routers, or billing policy modules.
"""

from __future__ import annotations

from typing import Any

import stripe


class StripeSdkSignatureError(Exception):
    """Webhook signature did not match."""


def configure(secret: str | None) -> None:
    stripe.api_key = secret


def create_customer(**kwargs: Any) -> Any:
    return stripe.Customer.create(**kwargs)


def create_checkout_session(**kwargs: Any) -> Any:
    return stripe.checkout.Session.create(**kwargs)


def retrieve_checkout_session(session_id: str) -> Any:
    return stripe.checkout.Session.retrieve(session_id)


def create_refund(**kwargs: Any) -> Any:
    return stripe.Refund.create(**kwargs)


def retrieve_balance() -> None:
    stripe.Balance.retrieve()


def create_connect_account(**kwargs: Any) -> Any:
    return stripe.Account.create(**kwargs)


def create_account_link(**kwargs: Any) -> Any:
    return stripe.AccountLink.create(**kwargs)


def construct_webhook_event(payload: bytes, sig_header: str | None, webhook_secret: str) -> Any:
    try:
        return stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except stripe.error.SignatureVerificationError as exc:
        raise StripeSdkSignatureError from exc


def create_identity_verification_session(**kwargs: Any) -> Any:
    return stripe.identity.VerificationSession.create(**kwargs)


def retrieve_identity_verification_session(session_id: str) -> Any:
    return stripe.identity.VerificationSession.retrieve(session_id)


def list_payout_balance_transactions(payout_id: str) -> list[dict[str, Any]]:
    """Every balance transaction settled in one payout (charges, refunds, fees, disputes)."""
    out: list[dict[str, Any]] = []
    page = stripe.BalanceTransaction.list(payout=payout_id, limit=100, expand=["data.source"])
    for txn in page.auto_paging_iter():
        out.append(txn.to_dict() if hasattr(txn, "to_dict") else dict(txn))
    return out
