"""Merchant cycle billing helpers: scheduled run, credit carry-forward, cycle gating."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from porterchain_api.booking_models import Order
from porterchain_api.domain.merchant_states import MerchantStatus
from porterchain_api.merchant_models import Merchant
from porterchain_api.platform.merchant_billing import apply_available_credit

__all__ = ["apply_available_credit", "is_cycle_billed", "run_due_cycles"]

NET_TERMS_CYCLES = frozenset({"WEEKLY", "BIWEEKLY", "MONTHLY"})


def run_due_cycles(svc, db: Session, *, now: datetime | None = None) -> dict[str, int]:
    """Scheduled run: invoice every net-terms merchant for its last closed period.

    Idempotent — orders already on an invoice are excluded, so re-running is a no-op.
    """
    merchants = db.query(Merchant).all()
    processed = invoiced = failed = 0
    for m in merchants:
        cycle = (m.billing_cycle or "").upper()
        terms = (m.payment_terms or "").upper()
        if cycle not in NET_TERMS_CYCLES or terms in ("", "IMMEDIATE", "PREPAID"):
            continue
        if m.status != MerchantStatus.ACTIVE.value:
            continue
        processed += 1
        try:
            from porterchain_api.admin_engine.merchant_ar_service import previous_billing_period_bounds

            start, end = previous_billing_period_bounds(cycle, now)
            out = svc.generate(db, None, merchant_id=m.id, period_start=start, period_end=end)
            invoiced += int(out["created_count"])
        except Exception:  # noqa: BLE001 - one bad merchant must not stop the run
            db.rollback()
            failed += 1
    return {"processed": processed, "invoiced": invoiced, "failed": failed}


def is_cycle_billed(db: Session, order: Order) -> bool:
    """True when a merchant order should wait for the cycle invoice instead of
    getting its own invoice at POD (finance setting ``merchant_cycle_invoicing``)."""
    if not order.merchant_id or order.customer_id:
        return False
    from porterchain_api.admin_engine.platform_settings import merchant_cycle_invoicing_enabled

    if not merchant_cycle_invoicing_enabled(db):
        return False
    terms = (order.payment_terms or "").upper()
    if terms in ("", "IMMEDIATE", "PREPAID"):
        return False
    merchant = db.get(Merchant, order.merchant_id)
    return bool(merchant and (merchant.billing_cycle or "").upper() in NET_TERMS_CYCLES)
