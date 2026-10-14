"""Admin mark-paid with Interac reference matching."""

from __future__ import annotations

import re
from typing import Any

from porterchain_api.admin_engine.merchant_ar_service import MerchantArService


def _norm_ref(value: str | None) -> str:
    return re.sub(r"[^A-Z0-9]", "", (value or "").upper())


def check_interac_reference(invoice: Any, reference: str | None, *, allow_mismatch: bool = False) -> str | None:
    """Interac mark-paid must carry the invoice's payment reference (the e-Transfer
    message). Blank -> use the invoice reference; mismatch -> reject unless overridden."""
    expected = getattr(invoice, "payment_reference", None)
    if not expected:
        return reference
    if not (reference or "").strip():
        return expected
    if _norm_ref(expected) in _norm_ref(reference) or allow_mismatch:
        return reference
    raise ValueError("payment_reference_mismatch")



def enforce_reference(db: Any, invoice_id: str, method: str, reference: str | None, allow_mismatch: bool) -> str | None:
    """Admin mark-paid: Interac payments must quote the invoice's payment reference."""
    if (method or "").strip().lower() != "interac":
        return reference
    from porterchain_api.booking_models import Invoice

    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    return check_interac_reference(invoice, reference, allow_mismatch=allow_mismatch) if invoice else reference


def record_admin_payment(db: Any, ctx: Any, invoice_id: str, body: Any) -> dict[str, Any]:
    """Admin mark-paid with Interac reference matching (mismatch needs explicit override)."""
    reference = enforce_reference(db, invoice_id, body.method, body.reference, body.allow_reference_mismatch)
    return MerchantArService().record_payment(
        db,
        ctx,
        invoice_id,
        method=body.method,
        amount_cents=body.amount_cents,
        reference=reference,
        paid_at=body.paid_at,
    )
