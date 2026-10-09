"""MerchantSyncService — validation gate before a merchant booking enters dispatch.

Implements the WORKFLOW pre-conditions: validate merchant → pricing → contract →
payment terms, before an Order/Booking is generated and BookingCreated is
published. A merchant never talks to a vendor console; this is the PorterChain
logistics-engine entry point that guards what is allowed to be dispatched.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.crm_models import CrmCompany, CrmContract
from porterchain_api.domain.merchant_states import MerchantStatus
from porterchain_api.merchant_models import Merchant


class BookingValidationError(Exception):
    """Raised when a merchant booking fails a pre-dispatch validation step."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


FSA_REFUSED_MESSAGE = (
    "No FSA flat rate covers this destination, and this account does not fall back to distance pricing."
)


CUSTOM_QUOTE_MESSAGE = (
    "This route needs a custom quotation under your rate schedule ({reason}). "
    "Contact PorterChain to book it."
)


def assert_not_fsa_refused(breakdown: Any) -> None:
    """A refused FSA miss finalizes at $0 — never preview, book, or build it as a price."""
    meta = getattr(breakdown, "metadata", None)
    if isinstance(meta, dict) and meta.get("fsa_refused"):
        if meta.get("custom_quote"):
            reason = str(meta.get("custom_quote_reason") or "custom_quote").replace("_", " ")
            raise BookingValidationError("fsa_refused", CUSTOM_QUOTE_MESSAGE.format(reason=reason))
        raise BookingValidationError("fsa_refused", FSA_REFUSED_MESSAGE)


@dataclass(frozen=True)
class ValidatedBooking:
    merchant: Merchant
    payment_terms: str
    contract_id: str | None
    warnings: tuple[str, ...]


class MerchantSyncService:
    def validate_booking(
        self,
        db: Session,
        merchant: Merchant,
        *,
        amount_cents: int | None = None,
        require_contract: bool = False,
    ) -> ValidatedBooking:
        warnings: list[str] = []

        # 1. Validate merchant — ONBOARDING may complete the company file, not book.
        if merchant.status == MerchantStatus.SUSPENDED.value:
            raise BookingValidationError("merchant_suspended", "Merchant account is suspended.")
        if merchant.status != MerchantStatus.ACTIVE.value:
            raise BookingValidationError(
                "merchant_not_active", f"Merchant must be ACTIVE to book (status={merchant.status})."
            )

        # 2. Validate pricing
        if amount_cents is not None and amount_cents <= 0:
            raise BookingValidationError("invalid_pricing", "Pricing engine returned a non-positive amount.")

        # 3. Validate contract (active CRM contract on the linked company)
        contract_id: str | None = None
        company = db.query(CrmCompany).filter(CrmCompany.merchant_id == merchant.id).first()
        if company:
            contract = (
                db.query(CrmContract)
                .filter(CrmContract.company_id == company.id, CrmContract.status == "active")
                .order_by(CrmContract.created_at.desc())
                .first()
            )
            if contract:
                contract_id = contract.id
        if not contract_id:
            if require_contract:
                raise BookingValidationError("no_active_contract", "No active merchant contract on file.")
            warnings.append("no_active_contract")

        # 4. Validate payment terms
        terms = merchant.payment_terms
        if not terms:
            raise BookingValidationError("missing_payment_terms", "Merchant has no payment terms configured.")
        if merchant.credit_limit_cents is not None and merchant.credit_limit_cents <= 0 and terms != "IMMEDIATE":
            warnings.append("zero_credit_limit")

        return ValidatedBooking(
            merchant=merchant,
            payment_terms=terms,
            contract_id=contract_id,
            warnings=tuple(warnings),
        )
