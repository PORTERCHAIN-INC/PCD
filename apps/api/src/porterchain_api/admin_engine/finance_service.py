"""Finance Center — Application Service (masterrule §11).

Financial truth lives in Porterchain (invoices, payments, ledger, payouts).
Settlement writes go through billing_engine.SettlementService.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, time
from typing import Any

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from porterchain_api.admin_engine.audit import log_admin_audit
from porterchain_api.admin_engine.rbac import AdminContext
from porterchain_api.admin_models import AdminAuditLog
from porterchain_api.billing_engine.ar import aging_bucket
from porterchain_api.billing_engine.merchant_service import effective_payment_terms
from porterchain_api.billing_engine.merchant_service import (
    invoice_due_date as merchant_invoice_due_date,
)
from porterchain_api.billing_engine.merchant_service import (
    invoice_status as merchant_invoice_status,
)
from porterchain_api.billing_engine.merchant_service import (
    outstanding_cents as merchant_outstanding_cents,
)
from porterchain_api.billing_engine.models import BillingLedgerEntry
from porterchain_api.booking_models import (
    Booking,
    Customer,
    DomainEvent,
    Invoice,
    Order,
    Payment,
    Quote,
)
from porterchain_api.merchant_engine.invoice_reminder import primary_ap_contact
from porterchain_api.billing_engine.invoice_extras import invoice_detail_extras, invoice_ledger_filter, invoice_payment_fields
from porterchain_api.merchant_engine.lookups import (
    company_names,
    credit_limit_cents_sum,
    get_merchant,
)

INVOICE_STATUSES = frozenset({
    "draft",
    "pending",
    "sent",
    "paid",
    "partially_paid", "partial",
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
    limit: int = 50
    offset: int = 0


class AdminFinanceService:
    def _now(self) -> datetime:
        return datetime.now(UTC).replace(tzinfo=None)

    def _sod(self) -> datetime:
        n = self._now()
        return datetime.combine(n.date(), time.min)

    def _month_start(self) -> datetime:
        n = self._now()
        return datetime(n.year, n.month, 1)

    def _payment_for_order(self, db: Session, order_id: str | None) -> Payment | None:
        if not order_id:  # cycle invoices: never match NULL-order (offline) payments
            return None
        return db.query(Payment).filter(Payment.order_id == order_id).order_by(Payment.created_at.desc()).first()

    def _invoice_status(
        self,
        invoice: Invoice,
        order: Order | None,
        payment: Payment | None,
        *,
        terms: str | None = None,
    ) -> str:
        """Shared status so collections, 360, and merchant Billing agree (BD)."""
        return merchant_invoice_status(
            invoice,
            order,
            payment,
            terms=terms or (order.payment_terms if order else None),
            now=self._now(),
        )

    def _outstanding_cents(self, invoice: Invoice, status: str) -> int:
        return merchant_outstanding_cents(invoice, status)

    def _company_names(self, db: Session) -> dict[str, str]:
        return company_names(db)

    def _credit_notes_count(self, db: Session) -> int:
        return int(
            db.query(func.count(BillingLedgerEntry.id))
            .filter(BillingLedgerEntry.kind == "credit_note")
            .scalar()
            or 0
        )

    def _ledger_inflow_since(self, db: Session, since: datetime) -> int:
        return int(
            db.query(func.coalesce(func.sum(BillingLedgerEntry.amount_cents), 0))
            .filter(
                BillingLedgerEntry.created_at >= since,
                BillingLedgerEntry.amount_cents.isnot(None),
                BillingLedgerEntry.kind.in_(("payment_settled", "stripe_payment_succeeded")),
            )
            .scalar()
            or 0
        )

    def _aging_bucket(self, days: int) -> str:
        return aging_bucket(days)

    def revenue_summary(self, db: Session) -> dict:
        from porterchain_api.admin_engine.finance_board import revenue_summary_payload

        return revenue_summary_payload(self, db)

    def dashboard(self, db: Session) -> dict[str, Any]:
        from porterchain_api.admin_engine.finance_board import dashboard_payload

        return dashboard_payload(self, db)

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
        booking = db.query(Booking).filter(Booking.order_id == invoice.order_id).first() if invoice.order_id else None
        payment = self._payment_for_order(db, invoice.order_id)
        mid = invoice.merchant_id or (order.merchant_id if order else None)
        merchant = get_merchant(db, mid)
        terms = effective_payment_terms(order, merchant) or "IMMEDIATE"
        status = self._invoice_status(invoice, order, payment, terms=terms)
        outstanding = self._outstanding_cents(invoice, status)
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
            **invoice_payment_fields(db, invoice),
            "currency": invoice.currency,
            "payment_terms": terms,
            "due_date": due_date,
            "pdf_url": invoice.pdf_url,
            "receipt_url": invoice.stripe_receipt_url,
            "last_reminded_at": invoice.last_reminded_at.isoformat()
            if getattr(invoice, "last_reminded_at", None)
            else None,
            "created_at": invoice.created_at,
        }

    def list_invoices(self, db: Session, *, limit: int = 100) -> list[Invoice]:
        return db.query(Invoice).order_by(Invoice.created_at.desc()).limit(limit).all()

    def _invoice_query(self, db: Session, filters: FinanceFilters):
        q = db.query(Invoice).order_by(Invoice.created_at.desc(), Invoice.id.desc())
        if filters.date_from:
            q = q.filter(Invoice.created_at >= filters.date_from)
        if filters.date_to:
            q = q.filter(Invoice.created_at <= filters.date_to)
        if filters.amount_min_cents is not None:
            q = q.filter(Invoice.amount_cents >= filters.amount_min_cents)
        if filters.amount_max_cents is not None:
            q = q.filter(Invoice.amount_cents <= filters.amount_max_cents)
        if filters.currency:
            q = q.filter(Invoice.currency == filters.currency)
        if filters.merchant_id:
            q = q.filter(
                or_(
                    Invoice.merchant_id == filters.merchant_id,
                    Invoice.order_id.in_(
                        db.query(Order.id).filter(
                            Order.merchant_id == filters.merchant_id,
                            Order.is_sandbox.is_(False),
                        )
                    ),
                )
            )
        # Live finance lists exclude sandbox-linked invoices by default.
        q = q.filter(
            or_(
                Invoice.order_id.is_(None),
                Invoice.order_id.in_(db.query(Order.id).filter(Order.is_sandbox.is_(False))),
            )
        )
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
        return q

    def list_invoices_page(self, db: Session, filters: FinanceFilters) -> dict[str, Any]:
        from porterchain_api.platform.pagination import (
            MAX_LIST_LIMIT,
            as_page,
            clamp_page,
        )

        limit, offset = clamp_page(filters.limit, filters.offset)
        q = self._invoice_query(db, filters)
        needs_row_filter = bool(filters.status or filters.outstanding_only)
        if needs_row_filter:
            scanned: list[dict[str, Any]] = []
            for inv in q.limit(MAX_LIST_LIMIT).all():
                row = self._invoice_row(db, inv)
                if filters.status and row["status"] != filters.status:
                    continue
                if filters.outstanding_only and row["outstanding_cents"] <= 0:
                    continue
                scanned.append(row)
            return as_page(scanned[offset : offset + limit], len(scanned), limit, offset)
        total = q.count()
        items = [self._invoice_row(db, inv) for inv in q.offset(offset).limit(limit).all()]
        return as_page(items, total, limit, offset)

    def list_invoices_enriched(self, db: Session, filters: FinanceFilters) -> list[dict[str, Any]]:
        return self.list_invoices_page(db, filters)["items"]

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
            .filter(invoice_ledger_filter(invoice))
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

        order = (
            db.query(Order).filter(Order.id == invoice.order_id).first() if invoice.order_id else None
        )
        quote_id = order.quote_id if order else None
        quote = db.query(Quote).filter(Quote.id == quote_id).first() if quote_id else None
        pricing_breakdown = dict(quote.pricing_breakdown or {}) if quote else None
        summary = (pricing_breakdown or {}).get("summary") if isinstance(pricing_breakdown, dict) else None
        meta = {}
        if isinstance(summary, dict):
            meta = dict(summary.get("metadata") or {})
            meta.update({k: v for k, v in summary.items() if k != "metadata" and k in (
                "pricing_model", "final_cents", "subtotal_cents", "tax_cents"
            )})
        if isinstance(pricing_breakdown, dict) and isinstance(pricing_breakdown.get("metadata"), dict):
            meta = {**meta, **pricing_breakdown["metadata"]}

        return {
            **row,
            **invoice_detail_extras(db, invoice),
            "quote_id": quote_id,
            "quote_amount_cents": quote.amount_cents if quote else None,
            "pricing_breakdown": pricing_breakdown,
            "pricing_model": meta.get("pricing_model") or meta.get("pricing_model_requested"),
            "pricing_metadata": {
                k: meta[k]
                for k in (
                    "pricing_model",
                    "pricing_model_requested",
                    "fsa_fallback",
                    "downtown_waived",
                    "upper_zone_waived",
                    "gta_vehicle_type",
                    "dest_fsa",
                    "origin_fsa",
                    "fsa",
                )
                if k in meta
            },
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

    def list_payments_page(self, db: Session, filters: FinanceFilters) -> dict[str, Any]:
        from porterchain_api.admin_engine.finance_board import payments_page_payload

        return payments_page_payload(self, db, filters)

    def list_payments_enriched(self, db: Session, filters: FinanceFilters) -> list[dict[str, Any]]:
        return self.list_payments_page(db, filters)["items"]

    # ------------------------------------------------------------------ #
    # Payouts & ledger
    # ------------------------------------------------------------------ #
    def list_payouts_enriched(self, db: Session, *, status: str | None = None) -> list[dict[str, Any]]:
        from porterchain_api.admin_engine.finance_board import list_payouts_payload

        return list_payouts_payload(self, db, status=status)

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
        from porterchain_api.admin_engine.finance_board import collections_payload

        return collections_payload(self, db)

    def _days_overdue(self, due: Any, status: str) -> int:
        if due is None or status != "overdue":
            return 0
        due_n = due.replace(tzinfo=None) if getattr(due, "tzinfo", None) else due
        return max(0, (self._now() - due_n).days)

    def _ap_contact(
        self, db: Session, merchant_id: str | None, cache: dict[str, dict[str, Any]]
    ) -> dict[str, Any] | None:
        """Who to phone. Cached — one merchant usually owns several open invoices."""
        if not merchant_id:
            return None
        if merchant_id not in cache:
            merchant = get_merchant(db, merchant_id)
            cache[merchant_id] = primary_ap_contact(merchant).as_dict()
        return cache[merchant_id]

    def remind_invoice(self, db: Session, ctx: AdminContext, invoice_id: str) -> dict[str, Any]:
        from porterchain_api.merchant_engine.invoice_reminder import remind_invoice

        invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
        if not invoice:
            raise LookupError("invoice_not_found")
        order = db.query(Order).filter(Order.id == invoice.order_id).first() if invoice.order_id else None
        mid = invoice.merchant_id or (order.merchant_id if order else None)
        if not mid:
            raise ValueError("invoice_not_merchant")
        merchant = get_merchant(db, mid)
        if not merchant:
            raise LookupError("merchant_not_found")
        result = remind_invoice(
            db,
            invoice,
            merchant,
            actor_type="admin",
            actor_id=ctx.user.id,
        )
        log_admin_audit(
            db,
            ctx,
            action="finance.invoice_reminded",
            resource_type="invoice",
            resource_id=invoice.id,
            payload={"email": result.get("email"), "merchant_id": merchant.id},
        )
        db.commit()
        return result

    def find_duplicate_invoices(self, db: Session, invoice: Invoice) -> list[dict[str, Any]]:
        if not invoice.order_id:  # cycle invoices: NULL would match every other cycle invoice
            return []
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
        from porterchain_api.admin_engine.finance_board import reports_payload

        return reports_payload(self, db)

    def export_gl(self, db: Session) -> list[dict[str, Any]]:
        from porterchain_api.admin_engine.finance_board import export_gl_payload

        return export_gl_payload(self, db)

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

    def refund_invoice(
        self,
        db: Session,
        ctx: AdminContext,
        settings: Any,
        invoice_id: str,
        *,
        amount_cents: int | None = None,
    ) -> dict[str, Any]:
        from porterchain_api.admin_engine.finance_refund import refund_invoice

        return refund_invoice(
            self, db, ctx, settings, invoice_id, amount_cents=amount_cents
        )
