"""Finance Center read compose — dashboard, collections, reports, GL export."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from porterchain_api.admin_models import Driver, DriverPayout
from porterchain_api.platform.merchant_billing import merchant_credit_total_cents
from porterchain_api.booking_models import Customer, Invoice, Order, Payment
from porterchain_api.domain.states import OrderState
from porterchain_api.driver_models import DriverWalletTransaction


def revenue_summary_payload(svc: Any, db: Session) -> dict:
    dash = dashboard_payload(svc, db)
    return {
        "monthly_revenue_cents": dash["month_revenue_cents"],
        "invoice_total_cents": dash["outstanding_invoices_cents"] + dash["paid_invoices_cents"],
        "refund_count": dash["refunds_count"],
    }


def dashboard_payload(svc: Any, db: Session) -> dict[str, Any]:
    now = svc._now()
    sod = svc._sod()
    month_start = svc._month_start()
    cancelled = [OrderState.CANCELLED.value, OrderState.REFUNDED.value]

    live = Order.is_sandbox.is_(False)
    today_revenue = (
        db.query(func.coalesce(func.sum(Order.amount_cents), 0))
        .filter(live, Order.created_at >= sod, Order.state.notin_(cancelled))
        .scalar()
        or 0
    )
    month_revenue = (
        db.query(func.coalesce(func.sum(Order.amount_cents), 0))
        .filter(live, Order.created_at >= month_start, Order.state.notin_(cancelled))
        .scalar()
        or 0
    )

    paid_total = 0
    outstanding_total = 0
    overdue_count = 0
    outstanding_count = 0
    paid_count = 0
    merchant_ar_cents = 0
    for inv in db.query(Invoice).all():
        order = db.query(Order).filter(Order.id == inv.order_id).first()
        if order is not None and bool(getattr(order, "is_sandbox", False)):
            continue
        payment = svc._payment_for_order(db, inv.order_id)
        st = svc._invoice_status(inv, order, payment)
        outstanding = svc._outstanding_cents(inv, st)
        if st == "paid":
            paid_total += inv.amount_cents
            paid_count += 1
        else:
            outstanding_total += outstanding
            if outstanding > 0:
                outstanding_count += 1
            if inv.merchant_id and not inv.customer_id:
                merchant_ar_cents += outstanding
        if st == "overdue":
            overdue_count += 1

    pending_payments = (
        db.query(func.count(Payment.id)).filter(Payment.status.in_(("PENDING", "PROCESSING"))).scalar() or 0
    )
    succeeded = db.query(func.count(Payment.id)).filter(Payment.status == "SUCCEEDED").scalar() or 0
    total_payments = db.query(func.count(Payment.id)).scalar() or 0
    refunds = db.query(func.count(Payment.id)).filter(Payment.status == "REFUNDED").scalar() or 0
    taxes_collected = db.query(func.coalesce(func.sum(Invoice.tax_cents), 0)).scalar() or 0
    pending_payouts = (
        db.query(func.coalesce(func.sum(DriverPayout.amount_cents), 0))
        .filter(DriverPayout.status == "pending")
        .scalar()
        or 0
    )
    paid_payouts = (
        db.query(func.coalesce(func.sum(DriverPayout.amount_cents), 0))
        .filter(DriverPayout.status == "paid")
        .scalar()
        or 0
    )
    driver_wallets = (
        db.query(func.coalesce(func.sum(DriverWalletTransaction.amount_cents), 0)).scalar() or 0
    )
    profit_estimate = int(month_revenue) - int(pending_payouts) - int(paid_payouts)

    trend: list[dict[str, Any]] = []
    for i in range(6, -1, -1):
        day = sod - timedelta(days=i)
        day_end = day + timedelta(days=1)
        rev = (
            db.query(func.coalesce(func.sum(Order.amount_cents), 0))
            .filter(live, Order.created_at >= day, Order.created_at < day_end)
            .scalar()
            or 0
        )
        trend.append({"date": day.date().isoformat(), "revenue_cents": int(rev)})

    merchants = svc._company_names(db)
    by_merchant: dict[str, int] = {}
    for o in db.query(Order).filter(live, Order.created_at >= month_start).all():
        if o.merchant_id:
            name = merchants.get(o.merchant_id, o.merchant_id)
            by_merchant[name] = by_merchant.get(name, 0) + o.amount_cents
    top_merchants = sorted(by_merchant.items(), key=lambda x: -x[1])[:10]
    ledger_in = svc._ledger_inflow_since(db, now - timedelta(days=30))

    return {
        "today_revenue_cents": int(today_revenue),
        "month_revenue_cents": int(month_revenue),
        "outstanding_invoices_cents": int(outstanding_total),
        "paid_invoices_cents": int(paid_total),
        "outstanding_invoice_count": outstanding_count,
        "paid_invoice_count": paid_count,
        "pending_payments": int(pending_payments),
        "paid_payments_count": int(succeeded),
        "refunds_count": int(refunds),
        "credit_notes_count": svc._credit_notes_count(db),
        # What merchants owe us right now (open B2B invoices, net of partial payments).
        # Was the sum of credit *limits*, which is not a balance.
        "merchant_balances_cents": int(merchant_ar_cents),
        "merchant_credit_balances_cents": int(merchant_credit_total_cents(db)),
        "driver_payouts_pending_cents": int(pending_payouts),
        "driver_payouts_paid_cents": int(paid_payouts),
        "driver_wallets_cents": int(driver_wallets),
        "taxes_collected_cents": int(taxes_collected),
        "profit_estimate_cents": max(0, profit_estimate),
        "payment_success_rate": round((succeeded / total_payments * 100) if total_payments else 100.0, 1),
        "overdue_invoices_count": overdue_count,
        "revenue_trend": trend,
        "cash_flow_cents": int(ledger_in or month_revenue),
        "top_merchants": [{"name": n, "revenue_cents": c} for n, c in top_merchants],
        "revenue_forecast_cents": int(month_revenue * 1.08),
    }


def collections_payload(svc: Any, db: Session) -> list[dict[str, Any]]:
    """Every open delivery invoice, oldest debt first (BL)."""
    collectable: list[dict[str, Any]] = []
    ap_cache: dict[str, dict[str, Any]] = {}
    for inv in db.query(Invoice).order_by(Invoice.created_at.asc()).all():
        order = db.query(Order).filter(Order.id == inv.order_id).first()
        if order is not None and bool(getattr(order, "is_sandbox", False)):
            continue
        payment = svc._payment_for_order(db, inv.order_id)
        st = svc._invoice_status(inv, order, payment)
        if st not in ("overdue", "sent", "pending", "partial") or svc._outstanding_cents(inv, st) <= 0:
            continue
        row = svc._invoice_row(db, inv)
        row["days_overdue"] = svc._days_overdue(row.get("due_date"), st)
        row["aging_bucket"] = svc._aging_bucket(row["days_overdue"])
        row["ap_contact"] = svc._ap_contact(db, row.get("merchant_id"), ap_cache)
        collectable.append(row)
    collectable.sort(key=lambda r: (-int(r["days_overdue"]), -int(r["outstanding_cents"])))
    return collectable


def reports_payload(svc: Any, db: Session) -> dict[str, Any]:
    month_start = svc._month_start()
    dash = dashboard_payload(svc, db)
    refunds_amount = (
        db.query(func.coalesce(func.sum(Payment.amount_cents), 0))
        .filter(Payment.status == "REFUNDED", Payment.created_at >= month_start)
        .scalar()
        or 0
    )
    return {
        "revenue_cents": dash["month_revenue_cents"],
        "profit_estimate_cents": dash["profit_estimate_cents"],
        "outstanding_cents": dash["outstanding_invoices_cents"],
        "collections_count": len(collections_payload(svc, db)),
        "tax_summary_cents": dash["taxes_collected_cents"],
        "refund_analysis_cents": int(refunds_amount),
        "driver_payouts_cents": dash["driver_payouts_pending_cents"] + dash["driver_payouts_paid_cents"],
        "top_merchants": dash["top_merchants"],
        "payment_success_rate": dash["payment_success_rate"],
    }


def export_gl_payload(svc: Any, db: Session) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for inv in db.query(Invoice).order_by(Invoice.created_at.asc()).all():
        order = db.query(Order).filter(Order.id == inv.order_id).first() if inv.order_id else None
        if order is not None and bool(getattr(order, "is_sandbox", False)):
            continue
        row = svc._invoice_row(db, inv)
        rows.append(
            {
                "date": str(inv.created_at.date()) if inv.created_at else "",
                "type": "invoice",
                "reference": inv.invoice_number,
                "description": f"Invoice {inv.invoice_number}",
                "debit_cents": row["outstanding_cents"],
                "credit_cents": inv.amount_cents if row["status"] == "paid" else 0,
                "tax_cents": inv.tax_cents,
                "currency": inv.currency,
            }
        )
    for p in db.query(Payment).filter(Payment.status == "SUCCEEDED").order_by(Payment.created_at.asc()).all():
        rows.append(
            {
                "date": str(p.created_at.date()) if p.created_at else "",
                "type": "payment",
                "reference": p.payment_reference or p.id,
                "description": f"Payment {p.payment_method or 'stripe'}",
                "debit_cents": 0,
                "credit_cents": p.amount_cents,
                "tax_cents": 0,
                "currency": p.currency,
            }
        )
    for p in db.query(DriverPayout).order_by(DriverPayout.created_at.asc()).all():
        rows.append(
            {
                "date": str(p.created_at.date()) if p.created_at else "",
                "type": "driver_payout",
                "reference": p.reference or p.id,
                "description": f"Driver payout {p.status}",
                "debit_cents": p.amount_cents,
                "credit_cents": 0,
                "tax_cents": 0,
                "currency": p.currency,
            }
        )
    return rows


def payments_page_payload(svc: Any, db: Session, filters: Any) -> dict[str, Any]:
    from porterchain_api.platform.pagination import as_page, clamp_page

    limit, offset = clamp_page(filters.limit, filters.offset)
    q = db.query(Payment).order_by(Payment.created_at.desc(), Payment.id.desc())
    if filters.status:
        q = q.filter(Payment.status == filters.status.upper())
    if filters.payment_method:
        q = q.filter(Payment.payment_method == filters.payment_method)
    if filters.date_from:
        q = q.filter(Payment.created_at >= filters.date_from)
    if filters.search:
        like = f"%{filters.search}%"
        q = q.filter(
            or_(
                Payment.stripe_payment_intent_id.ilike(like),
                Payment.payment_reference.ilike(like),
                Payment.transaction_id.ilike(like),
            )
        )
    total = q.count()
    rows = []
    for p in q.offset(offset).limit(limit).all():
        order = db.query(Order).filter(Order.id == p.order_id).first() if p.order_id else None
        customer = db.query(Customer).filter(Customer.id == p.customer_id).first() if p.customer_id else None
        rows.append(
            {
                "payment_id": p.id,
                "status": p.status,
                "amount_cents": p.amount_cents,
                "currency": p.currency,
                "payment_method": p.payment_method or "stripe",
                "stripe_payment_intent_id": p.stripe_payment_intent_id,
                "payment_reference": p.payment_reference,
                "transaction_id": p.transaction_id,
                "order_id": p.order_id,
                "order_number": order.order_number if order else None,
                "tracking_number": order.tracking_number if order else None,
                "customer_email": customer.email if customer else None,
                "receipt_url": p.receipt_url,
                "failure_reason": p.failure_reason,
                "created_at": p.created_at,
            }
        )
    return as_page(rows, total, limit, offset)


def list_payouts_payload(svc: Any, db: Session, *, status: str | None = None) -> list[dict[str, Any]]:
    q = db.query(DriverPayout).order_by(DriverPayout.created_at.desc())
    if status:
        q = q.filter(DriverPayout.status == status)
    drivers = {d.id: d.full_name for d in db.query(Driver).all()}
    return [
        {
            "payout_id": p.id,
            "driver_id": p.driver_id,
            "driver_name": drivers.get(p.driver_id),
            "amount_cents": p.amount_cents,
            "currency": p.currency,
            "status": p.status,
            "reference": p.reference,
            "created_at": p.created_at,
        }
        for p in q.limit(500).all()
    ]
