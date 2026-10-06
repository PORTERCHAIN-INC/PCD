"""Merchant cycle AR — admin preview/generate invoices + offline payment recording."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.admin_engine.audit import log_admin_audit
from porterchain_api.admin_engine.rbac import AdminContext
from porterchain_api.billing_engine.merchant_service import (
    billing_period_bounds,
    invoice_due_date,
    invoice_status,
    outstanding_cents,
)
from porterchain_api.billing_engine.models import BillingLedgerEntry
from porterchain_api.booking_engine import events as BookingEvents
from porterchain_api.booking_engine._core import emit_event
from porterchain_api.booking_engine.numbers import generate_invoice_number
from porterchain_api.booking_engine.order_transitions import transition_order_state
from porterchain_api.domain.states import OrderState
from porterchain_api.merchant_engine import events as MerchantEvents
from porterchain_api.merchant_engine.lookups import get_merchant
from porterchain_api.booking_models import Invoice, Order, Payment

ELIGIBLE_STATES = frozenset(
    {
        OrderState.DELIVERED.value,
        OrderState.POD_COMPLETED.value,
        # Allow recovering state-only "INVOICED" orders that never got an Invoice row.
        OrderState.INVOICED.value,
    }
)

OFFLINE_METHODS = frozenset({"wire", "ach", "cheque", "other"})


def previous_billing_period_bounds(
    cycle: str,
    reference: datetime | None = None,
) -> tuple[datetime, datetime]:
    """Return the fully closed period immediately before the current cycle window."""
    cur_start, cur_end = billing_period_bounds(cycle, reference)
    duration = cur_end - cur_start
    return cur_start - duration, cur_start


def _aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


def _naive(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt.replace(tzinfo=None) if dt.tzinfo else dt


class MerchantArService:
    def _resolve_period(
        self,
        merchant: Any,
        period_start: datetime | None,
        period_end: datetime | None,
    ) -> tuple[datetime, datetime]:
        if period_start and period_end:
            start, end = _naive(period_start), _naive(period_end)
            if start >= end:
                raise ValueError("invalid_period")
            return start, end
        return previous_billing_period_bounds(merchant.billing_cycle or "MONTHLY")

    def _eligible_orders(
        self,
        db: Session,
        merchant_id: str,
        period_start: datetime,
        period_end: datetime,
    ) -> list[Order]:
        invoiced_ids = {
            row[0]
            for row in db.query(Invoice.order_id).filter(Invoice.order_id.isnot(None)).all()
        }
        start, end = _aware(period_start), _aware(period_end)
        rows = (
            db.query(Order)
            .filter(
                Order.merchant_id == merchant_id,
                Order.state.in_(list(ELIGIBLE_STATES)),
            )
            .order_by(Order.updated_at.asc())
            .all()
        )
        out: list[Order] = []
        for order in rows:
            if order.id in invoiced_ids:
                continue
            # Activity rule: updated_at within [start, end).
            stamp = order.updated_at or order.created_at
            if stamp is None:
                continue
            stamp_a = _aware(stamp)
            if start <= stamp_a < end:
                out.append(order)
        return out

    def preview(
        self,
        db: Session,
        *,
        merchant_id: str,
        period_start: datetime | None = None,
        period_end: datetime | None = None,
    ) -> dict[str, Any]:
        merchant = get_merchant(db, merchant_id)
        if not merchant:
            raise LookupError("merchant_not_found")
        start, end = self._resolve_period(merchant, period_start, period_end)
        orders = self._eligible_orders(db, merchant_id, start, end)
        cents = sum(int(o.amount_cents or 0) for o in orders)
        return {
            "merchant_id": merchant_id,
            "merchant_name": merchant.legal_name or merchant.company_name,
            "payment_terms": merchant.payment_terms,
            "billing_cycle": merchant.billing_cycle,
            "period_start": _aware(start),
            "period_end": _aware(end),
            "order_count": len(orders),
            "uninvoiced_cents": cents,
            "order_ids": [o.id for o in orders],
            "orders": [
                {
                    "order_id": o.id,
                    "order_number": o.order_number,
                    "tracking_number": o.tracking_number,
                    "state": o.state,
                    "amount_cents": o.amount_cents,
                    "updated_at": o.updated_at,
                }
                for o in orders
            ],
        }

    def generate(
        self,
        db: Session,
        ctx: AdminContext,
        *,
        merchant_id: str,
        period_start: datetime | None = None,
        period_end: datetime | None = None,
    ) -> dict[str, Any]:
        merchant = get_merchant(db, merchant_id)
        if not merchant:
            raise LookupError("merchant_not_found")
        start, end = self._resolve_period(merchant, period_start, period_end)
        orders = self._eligible_orders(db, merchant_id, start, end)
        created: list[dict[str, Any]] = []
        skipped = 0

        for order in orders:
            existing = db.query(Invoice).filter(Invoice.order_id == order.id).first()
            if existing:
                skipped += 1
                continue

            terms = order.payment_terms or merchant.payment_terms
            due = invoice_due_date(datetime.now(UTC), terms)
            from porterchain_api.admin_engine.platform_settings import (
                invoice_number_prefix,
                tax_cents_for_amount,
            )

            amount_cents = int(order.amount_cents or 0)
            invoice = Invoice(
                invoice_number=generate_invoice_number(prefix=invoice_number_prefix(db)),
                order_id=order.id,
                customer_id=None,
                merchant_id=merchant_id,
                amount_cents=amount_cents,
                tax_cents=tax_cents_for_amount(db, amount_cents),
                fees_cents=0,
                currency=order.currency or "cad",
                due_at=_aware(due),
                billing_period_start=_aware(start),
                billing_period_end=_aware(end),
            )
            db.add(invoice)
            db.flush()

            from porterchain_api.billing_engine.models import InvoiceLine
            from porterchain_api.merchant_engine.reporting_metrics import channel_for_order_source

            channel = channel_for_order_source(order.order_source)
            pricing_model = getattr(merchant, "pricing_model", None) or "distance"
            db.add(
                InvoiceLine(
                    invoice_id=invoice.id,
                    order_id=order.id,
                    description=(
                        f"Delivery {order.order_number}"
                        f" · {channel or 'portal'}/{pricing_model}"
                    )[:255],
                    amount_cents=amount_cents,
                    tax_cents=int(invoice.tax_cents or 0),
                )
            )

            if OrderState(order.state) == OrderState.DELIVERED:
                transition_order_state(
                    db,
                    order,
                    OrderState.POD_COMPLETED,
                    event_type="order.pod_completed",
                    actor_type="admin",
                    actor_id=ctx.user.id,
                    payload={"merchant_ar": True},
                )
                db.refresh(order)

            # POD → INVOICED may already have run via InvoiceService on order.pod_completed.
            if OrderState(order.state) != OrderState.INVOICED:
                transition_order_state(
                    db,
                    order,
                    OrderState.INVOICED,
                    event_type=BookingEvents.ORDER_INVOICED,
                    actor_type="admin",
                    actor_id=ctx.user.id,
                    payload={
                        "invoice_id": invoice.id,
                        "invoice_number": invoice.invoice_number,
                        "merchant_id": merchant_id,
                        "merchant_email": merchant.email,
                        "merchant_name": merchant.company_name,
                        "email": merchant.email,
                        "order_id": order.id,
                        "order_number": order.order_number,
                        "amount_cents": invoice.amount_cents,
                        "amount_display": f"${(invoice.amount_cents or 0) / 100:.2f} {(invoice.currency or 'cad').upper()}",
                        "merchant_ar": True,
                    },
                )

            emit_event(
                db,
                event_type=MerchantEvents.MERCHANT_INVOICE_GENERATED,
                aggregate_type="merchant",
                aggregate_id=merchant_id,
                correlation_id=invoice.id,
                actor_type="admin",
                actor_id=ctx.user.id,
                payload={
                    "invoice_id": invoice.id,
                    "invoice_number": invoice.invoice_number,
                    "order_id": order.id,
                    "amount_cents": invoice.amount_cents,
                },
            )
            created.append(
                {
                    "invoice_id": invoice.id,
                    "invoice_number": invoice.invoice_number,
                    "order_id": order.id,
                    "order_number": order.order_number,
                    "amount_cents": invoice.amount_cents,
                    "due_at": invoice.due_at,
                }
            )

        db.flush()

        log_admin_audit(
            db,
            ctx,
            action="finance.merchant_ar.generate",
            resource_type="merchant",
            resource_id=merchant_id,
            payload={
                "period_start": start.isoformat(),
                "period_end": end.isoformat(),
                "created": len(created),
                "skipped": skipped,
            },
        )
        db.commit()
        return {
            "merchant_id": merchant_id,
            "period_start": _aware(start),
            "period_end": _aware(end),
            "created_count": len(created),
            "skipped_count": skipped,
            "invoices": created,
        }

    def record_payment(
        self,
        db: Session,
        ctx: AdminContext,
        invoice_id: str,
        *,
        method: str,
        amount_cents: int | None = None,
        reference: str | None = None,
        paid_at: datetime | None = None,
    ) -> dict[str, Any]:
        method_n = (method or "").strip().lower()
        if method_n not in OFFLINE_METHODS:
            raise ValueError("invalid_payment_method")

        invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
        if not invoice:
            raise LookupError("invoice_not_found")
        order = db.query(Order).filter(Order.id == invoice.order_id).first()
        if not order:
            raise LookupError("order_not_found")

        existing = (
            db.query(Payment)
            .filter(Payment.order_id == order.id, Payment.status == "SUCCEEDED")
            .first()
        )
        if existing:
            raise ValueError("already_paid")

        status = invoice_status(invoice, order, None, terms=order.payment_terms)
        outstanding = outstanding_cents(invoice, status)
        settle_cents = int(amount_cents) if amount_cents is not None else outstanding
        if settle_cents != outstanding:
            raise ValueError("partial_payments_unsupported")
        if settle_cents <= 0:
            raise ValueError("nothing_outstanding")

        pay = Payment(
            quote_id=None,
            order_id=order.id,
            customer_id=order.customer_id,
            status="SUCCEEDED",
            amount_cents=settle_cents,
            currency=invoice.currency or order.currency or "cad",
            payment_method=method_n,
            payment_reference=(reference or "")[:32] or None,
            transaction_id=f"offline:{invoice.id}",
        )
        db.add(pay)
        db.flush()

        entry = BillingLedgerEntry(
            kind="merchant_offline_payment",
            payment_id=pay.id,
            order_id=order.id,
            merchant_id=invoice.merchant_id or order.merchant_id,
            amount_cents=settle_cents,
            currency=pay.currency,
            status="recorded",
            metadata_json={
                "invoice_id": invoice.id,
                "invoice_number": invoice.invoice_number,
                "method": method_n,
                "reference": reference,
                "paid_at": (_aware(paid_at) or datetime.now(UTC)).isoformat(),
            },
        )
        db.add(entry)

        from porterchain_api.merchant_engine.invoice_reminder import primary_billing_email
        from porterchain_api.merchant_engine.lookups import get_merchant

        billed = get_merchant(db, invoice.merchant_id or order.merchant_id)
        emit_event(
            db,
            event_type=MerchantEvents.MERCHANT_PAYMENT_RECEIVED,
            aggregate_type="merchant",
            aggregate_id=invoice.merchant_id or order.merchant_id or "",
            correlation_id=invoice.id,
            actor_type="admin",
            actor_id=ctx.user.id,
            payload={
                "invoice_id": invoice.id,
                "payment_id": pay.id,
                "amount_cents": settle_cents,
                "method": method_n,
                "merchant_id": invoice.merchant_id or order.merchant_id,
                "merchant_email": primary_billing_email(billed) if billed else None,
            },
        )
        log_admin_audit(
            db,
            ctx,
            action="finance.merchant_ar.record_payment",
            resource_type="invoice",
            resource_id=invoice.id,
            payload={"payment_id": pay.id, "amount_cents": settle_cents, "method": method_n},
        )
        db.commit()
        return {
            "invoice_id": invoice.id,
            "payment_id": pay.id,
            "amount_cents": settle_cents,
            "status": "paid",
            "method": method_n,
            "ledger_id": entry.id,
        }
