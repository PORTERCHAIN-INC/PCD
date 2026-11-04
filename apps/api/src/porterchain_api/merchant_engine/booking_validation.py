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

#: 2026-10-31 standard pricing (no contract schedule): plain wording.
STANDARD_CUSTOM_QUOTE_MESSAGE = "This delivery needs a custom quote ({reason}). Contact PorterChain to book it."


def assert_not_fsa_refused(breakdown: Any) -> None:
    """A refused FSA miss finalizes at $0 — never preview, book, or build it as a price."""
    meta = getattr(breakdown, "metadata", None)
    if isinstance(meta, dict) and meta.get("fsa_refused"):
        if meta.get("custom_quote"):
            reason = str(meta.get("custom_quote_reason") or "custom_quote").replace("_", " ")
            standard = meta.get("pricing") in ("parcel_v2", "vehicle_hourly")
            msg = STANDARD_CUSTOM_QUOTE_MESSAGE if standard else CUSTOM_QUOTE_MESSAGE
            raise BookingValidationError("fsa_refused", msg.format(reason=reason))
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
            # L139 (decided 14:17): an admin-set custom price or the standard price needs no contract
            # on file, so a missing contract is not a user-facing warning.

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


def check_declarations(body: Any) -> None:
    """C13/C15: dangerous goods need written approval first; prohibited articles are refused."""
    from porterchain_pricing.contract_terms import DEFAULT_TERMS, declaration_problem

    from porterchain_api.ops_rules.rules import alcohol_problem, lq_check

    text = " ".join(str(getattr(body, k, "") or "") for k in ("item_category", "dangerous_goods_description"))
    if alcohol_problem(contains_alcohol=bool(getattr(body, "contains_alcohol", False)), text=text) or \
            "alcohol" in (getattr(body, "prohibited_articles", None) or []):
        raise BookingValidationError("alcohol_not_carried", "We don't carry alcohol.")
    lq = getattr(body, "dg_limited_quantity", None)
    if lq:
        res = lq_check(list(lq.get("items") or []), package_gross_kg=float(lq.get("package_gross_kg") or 0),
                       lq_mark_photo=lq.get("lq_mark_photo"), mark_side_mm=lq.get("mark_side_mm"),
                       small_package=bool(lq.get("small_package")))
        if not res["ok"]:
            raise BookingValidationError("dg_limited_quantity_rejected", "; ".join(res["problems"]))
        return  # TDG limited quantity (perfume/aerosol) is accepted without written approval
    problem = declaration_problem(
        DEFAULT_TERMS,
        dangerous_goods=bool(getattr(body, "dangerous_goods", False)),
        prohibited=list(getattr(body, "prohibited_articles", None) or []),
    )
    if problem == "prohibited_article":
        raise BookingValidationError(problem, "Prohibited articles can't be carried without written approval.")
    if problem:
        raise BookingValidationError(
            problem, "Dangerous goods need written approval and permits before booking. Contact us for a quote."
        )


_COVER_MSG = {
    "declared_value_cover_unavailable": "Declared-value cover isn't available yet. Standard liability is $4.41/kg.",
    "declared_value_required": "Enter the declared value of each parcel to buy cover.",
    "declared_value_over_max": "Declared value is above the $2,500 per-parcel maximum. Contact us before booking.",
    "declared_value_excluded_goods": "Cash, jewellery, medicines and perishables can't be covered.",
}


def declared_value_block(coverage: dict | None) -> tuple[str, str] | None:
    """Doc 72 §8 / doc 84: cover was asked for but can't be sold -> (code, message). Plain bookings never block."""
    cov = coverage or {}
    if not cov.get("requested") or not cov.get("unavailable"):
        return None
    code = cov["unavailable"][0]
    return code, _COVER_MSG.get(code, "Declared-value cover can't be added to this booking.")
