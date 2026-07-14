"""Finance Center — Application Service (masterrule §11).

Financial truth lives in Porterchain (invoices, payments, ledger, payouts).
Settlement writes go through billing_engine.SettlementService — never Fleetbase.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta
from typing import Any

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from porterchain_api.admin_engine.audit import log_admin_audit
from porterchain_api.admin_engine.rbac import AdminContext
from porterchain_api.admin_models import AdminAuditLog, Driver, DriverPayout
from porterchain_api.billing_engine.merchant_service import invoice_due_date as merchant_invoice_due_date
from porterchain_api.billing_engine.models import BillingLedgerEntry
from porterchain_api.domain.states import OrderState
from porterchain_api.merchant_models import Merchant
from porterchain_api.models import Booking, Customer, DomainEvent, Invoice, Order, Payment


INVOICE_STATUSES = frozenset({
    "draft",
    "pending",
    "sent",
    "paid",
    "partially_paid",
    "overdue",
    "cancelled",
    "void",
})


@dataclass
class FinanceFilters:
    status: str | None = None
    merchant_id: str | None = None
    payment_method: str | None = None
    currency: str | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    amount_min_cents: int | None = None
    amount_max_cents: int | None = None
    outstanding_only: bool = False
    search: str | None = None
    limit: int = 500


class AdminFinanceService:
    def _now(self) -> datetime:
        return datetime.now(UTC).replace(tzinfo=None)

    def _sod(self) -> datetime:
        n = self._now()
        return datetime.combine(n.date(), time.min)

    def _month_start(self) -> datetime:
        n = self._now()
        return datetime(n.year, n.month, 1)

    def _payment_for_order(self, db: Session, order_id: str) -> Payment | None:
        return (
            db.query(Payment)
            .filter(Payment.order_id == order_id)
            .order_by(Payment.created_at.desc())
            .first()
        )

    def _invoice_status(self, invoice: Invoice, order: Order | None, payment: Payment | None) -> str:
        if order and order.state == OrderState.CANCELLED.value:
            return "cancelled"
        if payment:
            if payment.status == "SUCCEEDED":
                return "paid"
            if payment.status == "REFUNDED":
                return "void"
            if payment.status in ("PENDING", "PROCESSING"):
                return "pending"
            if payment.status == "FAILED":
                return "pending"
        terms = order.payment_terms if order else None
        due = None
        if getattr(invoice, "due_at", None):
            due = invoice.due_at.replace(tzinfo=None) if invoice.due_at.tzinfo else invoice.due_at
        else:
            due = merchant_invoice_due_date(
                invoice.created_at.replace(tzinfo=None) if invoice.created_at and invoice.created_at.tzinfo else invoice.created_at,
                terms,
            )
        if due and self._now() > due:
            return "overdue"
        return "sent"

    def _outstanding_cents(self, invoice: Invoice, status: str) -> int:
        if status in ("paid", "void", "cancelled"):
            return 0
        return invoice.amount_cents

    # ------------------------------------------------------------------ #
    # Legacy summary (backward compatible)
    # ------------------------------------------------------------------ #
    def revenue_summary(self, db: Session) -> dict:
        dash = self.dashboard(db)
        return {
            "monthly_revenue_cents": dash["month_revenue_cents"],
            "invoice_total_cents": dash["outstanding_invoices_cents"] + dash["paid_invoices_cents"],
            "refund_count": dash["refunds_count"],
        }

    # ------------------------------------------------------------------ #
    # Dashboard
    # ------------------------------------------------------------------ #
    def dashboard(self, db: Session) -> dict[str, Any]:
        now = self._now()
        sod = self._sod()
        month_start = self._month_start()

        today_revenue = (
            db.query(func.coalesce(func.sum(Order.amount_cents), 0))
            .filter(Order.created_at >= sod, Order.state.notin_([OrderState.CANCELLED.value, OrderState.REFUNDED.value]))
            .scalar()
            or 0
        )
        month_revenue = (
            db.query(func.coalesce(func.sum(Order.amount_cents), 0))
            .filter(Order.created_at >= month_start, Order.state.notin_([OrderState.CANCELLED.value, OrderState.REFUNDED.value]))
            .scalar()
            or 0
        )

        invoices = db.query(Invoice).all()
        paid_total = 0
        outstanding_total = 0
        overdue_count = 0
        outstanding_count = 0
        paid_count = 0
        for inv in invoices:
            order = db.query(Order).filter(Order.id == inv.order_id).first()
            payment = self._payment_for_order(db, inv.order_id)
            st = self._invoice_status(inv, order, payment)
            outstanding = self._outstanding_cents(inv, st)
            if st == "paid":
                paid_total += inv.amount_cents
                paid_count += 1
            else:
                outstanding_total += outstanding
                if outstanding > 0:
                    outstanding_count += 1
            if st == "overdue":
                overdue_count += 1

        pending_payments = db.query(func.count(Payment.id)).filter(Payment.status.in_(("PENDING", "PROCESSING"))).scalar() or 0
        succeeded = db.query(func.count(Payment.id)).filter(Payment.status == "SUCCEEDED").scalar() or 0
        total_payments = db.query(func.count(Payment.id)).scalar() or 0
        refunds = db.query(func.count(Payment.id)).filter(Payment.status == "REFUNDED").scalar() or 0

        credit_notes = (
            db.query(func.count(BillingLedgerEntry.id))
            .filter(BillingLedgerEntry.kind == "credit_note")
            .scalar()
            or 0
        )

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

        merchant_balances = (
            db.query(func.coalesce(func.sum(Merchant.credit_limit_cents), 0))
            .filter(Merchant.credit_limit_cents.isnot(None))
            .scalar()
            or 0
        )

        driver_wallets = db.query(func.coalesce(func.sum(Driver.wallet_balance_cents), 0)).scalar() or 0

        profit_estimate = int(month_revenue) - int(pending_payouts) - int(paid_payouts)

        # Revenue trend — last 7 days
        trend: list[dict[str, Any]] = []
        for i in range(6, -1, -1):
            day = sod - timedelta(days=i)
            day_end = day + timedelta(days=1)
            rev = (
                db.query(func.coalesce(func.sum(Order.amount_cents), 0))
                .filter(Order.created_at >= day, Order.created_at < day_end)
                .scalar()
                or 0
            )
            trend.append({"date": day.date().isoformat(), "revenue_cents": int(rev)})

        # Top merchants
        merchants = {m.id: m.company_name for m in db.query(Merchant).all()}
        by_merchant: dict[str, int] = {}
        for o in db.query(Order).filter(Order.created_at >= month_start).all():
            if o.merchant_id:
                name = merchants.get(o.merchant_id, o.merchant_id)
                by_merchant[name] = by_merchant.get(name, 0) + o.amount_cents
        top_merchants = sorted(by_merchant.items(), key=lambda x: -x[1])[:10]

        # Cash flow from ledger (last 30 days)
        ledger_in = (
            db.query(func.coalesce(func.sum(BillingLedgerEntry.amount_cents), 0))
            .filter(
                BillingLedgerEntry.created_at >= now - timedelta(days=30),
                BillingLedgerEntry.amount_cents.isnot(None),
                BillingLedgerEntry.kind.in_(("payment_settled", "stripe_payment_succeeded")),
            )
            .scalar()
            or 0
        )

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
            "credit_notes_count": int(credit_notes),
            "merchant_balances_cents": int(merchant_balances),
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

    # ------------------------------------------------------------------ #
    # Invoices
    # ------------------------------------------------------------------ #
    def _invoice_row(self, db: Session, invoice: Invoice) -> dict[str, Any]:
        order = db.query(Order).filter(Order.id == invoice.order_id).first()
        customer = (
            db.query(Customer).filter(Customer.id == invoice.customer_id).first()
            if invoice.customer_id
            else None
        )
        booking = db.query(Booking).filter(Booking.order_id == invoice.order_id).first()
        payment = self._payment_for_order(db, invoice.order_id)
        mid = invoice.merchant_id or (order.merchant_id if order else None)
        merchant = db.query(Merchant).filter(Merchant.id == mid).first() if mid else None
        status = self._invoice_status(invoice, order, payment)
        outstanding = self._outstanding_cents(invoice, status)
        terms = (order.payment_terms if order else None) or (merchant.payment_terms if merchant else None) or "IMMEDIATE"
        if getattr(invoice, "due_at", None):
            due_date = invoice.due_at
        else:
            due_date = merchant_invoice_due_date(
                invoice.created_at.replace(tzinfo=None) if invoice.created_at and invoice.created_at.tzinfo else invoice.created_at,
                terms,
            )
        return {
            "invoice_id": invoice.id,
            "invoice_number": invoice.invoice_number,
            "receipt_number": invoice.receipt_number,
            "status": status,
            "merchant_id": mid,
            "merchant_name": merchant.company_name if merchant else None,
            "customer_id": invoice.customer_id,
            "customer_email": customer.email if customer else None,
            "order_id": invoice.order_id,
            "order_number": order.order_number if order else None,
            "tracking_number": order.tracking_number if order else None,
            "booking_number": booking.booking_number if booking else None,
            "amount_cents": invoice.amount_cents,
            "tax_cents": invoice.tax_cents,
            "fees_cents": invoice.fees_cents,
            "outstanding_cents": outstanding,
            "currency": invoice.currency,
            "payment_terms": terms,
            "due_date": due_date,
            "pdf_url": invoice.pdf_url,
            "receipt_url": invoice.stripe_receipt_url,
            "created_at": invoice.created_at,
        }

    def list_invoices(self, db: Session, *, limit: int = 100) -> list[Invoice]:
        return db.query(Invoice).order_by(Invoice.created_at.desc()).limit(limit).all()

    def list_invoices_enriched(self, db: Session, filters: FinanceFilters) -> list[dict[str, Any]]:
        q = db.query(Invoice).order_by(Invoice.created_at.desc())
        if filters.date_from:
            q = q.filter(Invoice.created_at >= filters.date_from)
        if filters.date_to:
            q = q.filter(Invoice.created_at <= filters.date_to)
        if filters.amount_min_cents is not None:
            q = q.filter(Invoice.amount_cents >= filters.amount_min_cents)
        if filters.amount_max_cents is not None:
            q = q.filter(Invoice.amount_cents <= filters.amount_max_cents)
        if filters.search:
            like = f"%{filters.search}%"
            order_ids = [
                o.id
                for o in db.query(Order)
                .filter(or_(Order.order_number.ilike(like), Order.tracking_number.ilike(like)))
                .limit(200)
                .all()
            ]
            clauses = [Invoice.invoice_number.ilike(like), Invoice.receipt_number.ilike(like)]
            if order_ids:
                clauses.append(Invoice.order_id.in_(order_ids))
            q = q.filter(or_(*clauses))

        rows: list[dict[str, Any]] = []
        for inv in q.limit(filters.limit).all():
            row = self._invoice_row(db, inv)
            if filters.status and row["status"] != filters.status:
                continue
            if filters.merchant_id and row["merchant_id"] != filters.merchant_id:
                continue
            if filters.currency and row["currency"] != filters.currency:
                continue
            if filters.outstanding_only and row["outstanding_cents"] <= 0:
                continue
            rows.append(row)
        return rows

    def get_invoice_detail(self, db: Session, invoice_id: str) -> dict[str, Any] | None:
        invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
        if not invoice:
            return None
        row = self._invoice_row(db, invoice)
        payment = self._payment_for_order(db, invoice.order_id)
        agg_ids = [invoice.order_id, invoice.id]
        if payment:
            agg_ids.append(payment.id)
        events = (
            db.query(DomainEvent)
            .filter(DomainEvent.aggregate_id.in_(agg_ids))
            .order_by(DomainEvent.occurred_at.asc())
            .limit(50)
            .all()
        )
        ledger = (
            db.query(BillingLedgerEntry)
            .filter(BillingLedgerEntry.order_id == invoice.order_id)
            .order_by(BillingLedgerEntry.created_at.asc())
            .all()
        )
        audit = (
            db.query(AdminAuditLog)
            .filter(AdminAuditLog.resource_id.in_([invoice.id, invoice.order_id]))
            .order_by(AdminAuditLog.created_at.asc())
            .all()
        )
        timeline = []
        for ev in events:
            timeline.append(
                {
                    "label": ev.event_type.replace(".", " ").title(),
                    "event_type": ev.event_type,
                    "occurred_at": ev.occurred_at,
                }
            )
        for le in ledger:
            timeline.append(
                {
                    "label": le.kind.replace("_", " ").title(),
                    "event_type": le.kind,
                    "occurred_at": le.created_at,
                    "amount_cents": le.amount_cents,
                }
            )
        timeline.sort(key=lambda x: str(x.get("occurred_at") or ""))

        return {
            **row,
            "payment": {
                "payment_id": payment.id,
                "status": payment.status,
                "amount_cents": payment.amount_cents,
                "stripe_payment_intent_id": payment.stripe_payment_intent_id,
                "payment_reference": payment.payment_reference,
                "payment_method": payment.payment_method,
                "receipt_url": payment.receipt_url,
                "created_at": payment.created_at,
            }
            if payment
            else None,
            "timeline": timeline,
            "audit_log": [
                {"action": a.action, "created_at": a.created_at, "payload": a.payload}
                for a in audit
            ],
            "duplicates": self.find_duplicate_invoices(db, invoice),
        }

    # ------------------------------------------------------------------ #
    # Payments
    # ------------------------------------------------------------------ #
    def list_payments(self, db: Session, *, limit: int = 100) -> list[Payment]:
        return db.query(Payment).order_by(Payment.created_at.desc()).limit(limit).all()

    def list_payments_enriched(self, db: Session, filters: FinanceFilters) -> list[dict[str, Any]]:
        q = db.query(Payment).order_by(Payment.created_at.desc())
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
        rows = []
        for p in q.limit(filters.limit).all():
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
        return rows

    # ------------------------------------------------------------------ #
    # Payouts & ledger
    # ------------------------------------------------------------------ #
    def list_payouts_enriched(self, db: Session, *, status: str | None = None) -> list[dict[str, Any]]:
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

    def list_ledger(self, db: Session, *, limit: int = 200) -> list[dict[str, Any]]:
        entries = (
            db.query(BillingLedgerEntry)
            .order_by(BillingLedgerEntry.created_at.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "id": e.id,
                "kind": e.kind,
                "payment_id": e.payment_id,
                "order_id": e.order_id,
                "merchant_id": e.merchant_id,
                "amount_cents": e.amount_cents,
                "currency": e.currency,
                "status": e.status,
                "created_at": e.created_at,
            }
            for e in entries
        ]

    # ------------------------------------------------------------------ #
    # Collections & smart features
    # ------------------------------------------------------------------ #
    def collections(self, db: Session) -> list[dict[str, Any]]:
        overdue = []
        for inv in db.query(Invoice).order_by(Invoice.created_at.asc()).all():
            order = db.query(Order).filter(Order.id == inv.order_id).first()
            payment = self._payment_for_order(db, inv.order_id)
            st = self._invoice_status(inv, order, payment)
            if st in ("overdue", "sent", "pending") and self._outstanding_cents(inv, st) > 0:
                row = self._invoice_row(db, inv)
                due = row.get("due_date")
                if due is not None:
                    due_n = due.replace(tzinfo=None) if getattr(due, "tzinfo", None) else due
                    row["days_overdue"] = max(0, (self._now() - due_n).days) if st == "overdue" else 0
                else:
                    row["days_overdue"] = 0
                overdue.append(row)
        return overdue

    def find_duplicate_invoices(self, db: Session, invoice: Invoice) -> list[dict[str, Any]]:
        return [
            {"invoice_id": o.id, "invoice_number": o.invoice_number, "order_id": o.order_id}
            for o in db.query(Invoice)
            .filter(Invoice.order_id == invoice.order_id, Invoice.id != invoice.id)
            .all()
        ]

    def find_duplicate_payments(self, db: Session) -> list[dict[str, Any]]:
        seen: dict[str, str] = {}
        dups: list[dict[str, Any]] = []
        for p in db.query(Payment).filter(Payment.stripe_payment_intent_id.isnot(None)).all():
            key = p.stripe_payment_intent_id or ""
            if key in seen:
                dups.append({"payment_id": p.id, "conflicts_with": seen[key], "stripe_payment_intent_id": key})
            else:
                seen[key] = p.id
        return dups

    # ------------------------------------------------------------------ #
    # Reports & export
    # ------------------------------------------------------------------ #
    def reports(self, db: Session) -> dict[str, Any]:
        month_start = self._month_start()
        dash = self.dashboard(db)
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
            "collections_count": len(self.collections(db)),
            "tax_summary_cents": dash["taxes_collected_cents"],
            "refund_analysis_cents": int(refunds_amount),
            "driver_payouts_cents": dash["driver_payouts_pending_cents"] + dash["driver_payouts_paid_cents"],
            "top_merchants": dash["top_merchants"],
            "payment_success_rate": dash["payment_success_rate"],
        }

    def export_gl(self, db: Session) -> list[dict[str, Any]]:
        """General ledger rows for CSV / accounting export."""
        rows: list[dict[str, Any]] = []
        for inv in db.query(Invoice).order_by(Invoice.created_at.asc()).all():
            row = self._invoice_row(db, inv)
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

    def record_credit_note(
        self,
        db: Session,
        ctx: AdminContext,
        *,
        order_id: str,
        amount_cents: int,
        reason: str,
    ) -> BillingLedgerEntry:
        entry = BillingLedgerEntry(
            kind="credit_note",
            order_id=order_id,
            amount_cents=amount_cents,
            status="recorded",
            metadata_json={"reason": reason, "created_by": ctx.user.id},
        )
        db.add(entry)
        db.flush()
        log_admin_audit(
            db,
            ctx,
            action="finance.credit_note",
            resource_type="order",
            resource_id=order_id,
            payload={"amount_cents": amount_cents, "reason": reason},
        )
        db.commit()
        db.refresh(entry)
        return entry
