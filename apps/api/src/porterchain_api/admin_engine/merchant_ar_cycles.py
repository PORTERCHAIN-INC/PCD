"""Merchant cycle billing helpers: scheduled run, credit carry-forward, cycle gating."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from porterchain_api.booking_models import Order
from porterchain_api.domain.merchant_states import MerchantStatus
from porterchain_api.merchant_models import Merchant
from porterchain_api.platform.merchant_billing import apply_available_credit

__all__ = ["apply_available_credit", "is_cycle_billed", "is_weekly_billed_merchant", "run_due_cycles"]

NET_TERMS_CYCLES = frozenset({"WEEKLY", "BIWEEKLY", "MONTHLY"})


def run_due_cycles(svc, db: Session, *, now: datetime | None = None) -> dict[str, int]:
    """Scheduled run: invoice every net-terms merchant for its last closed period.

    Idempotent — orders already on an invoice are excluded, so re-running is a no-op.
    """
    from porterchain_api.billing_engine import weekly_billing

    # Weekly billing (Ravi 2026-10-31): last Mon-Sun Toronto week, invoiced from Wednesday.
    if not weekly_billing.invoice_day_reached(now):
        return {"processed": 0, "invoiced": 0, "failed": 0}
    merchants = db.query(Merchant).all()
    processed = invoiced = failed = 0
    for m in merchants:
        if not is_weekly_billed_merchant(m):
            continue
        if m.status not in (MerchantStatus.ACTIVE.value, MerchantStatus.SUSPENDED.value):
            continue
        processed += 1
        try:
            start, end = weekly_billing.previous_week_bounds(now)
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
    if (order.payment_terms or "").upper() == "PREPAID":
        return False
    merchant = db.get(Merchant, order.merchant_id)
    return bool(merchant and is_weekly_billed_merchant(merchant))


def is_weekly_billed_merchant(merchant: Merchant) -> bool:
    """Every merchant is billed weekly, except one that prepays by card at booking."""
    return (getattr(merchant, "payment_terms", None) or "").upper() != "PREPAID"
