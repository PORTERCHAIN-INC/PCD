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
    invoice_total_cents,
    outstanding_cents,
)
from porterchain_api.billing_engine.models import BillingLedgerEntry, InvoiceLine
from porterchain_api.booking_engine import events as BookingEvents
from porterchain_api.booking_engine._core import emit_event
from porterchain_api.billing_engine.invoice_numbering import allocate_invoice_number, ensure_payment_reference
from porterchain_api.billing_engine.merchant_credit import add_merchant_credit
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

# Merchants pay by Interac e-Transfer. Cheque/wire/other stay for edge cases; "ach" is
# a US rail and is no longer offered (still readable on historical payments).
OFFLINE_METHODS = frozenset({"interac", "cheque", "wire", "other"})
LEGACY_METHODS = frozenset({"ach"})
NET_TERMS_CYCLES = frozenset({"WEEKLY", "BIWEEKLY", "MONTHLY"})


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
    def run_due_cycles(self, db: Session, *, now: datetime | None = None) -> dict[str, int]:
        from porterchain_api.admin_engine.merchant_ar_cycles import run_due_cycles

        return run_due_cycles(self, db, now=now)

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
        invoiced_ids |= {
            row[0]
            for row in db.query(InvoiceLine.order_id).filter(InvoiceLine.order_id.isnot(None)).all()
        }
        end = _aware(period_end)  # period_start is informational: older uninvoiced work carries forward
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
            # Anything delivered before the period closes and never invoiced is billed now
            # (carried forward), so a late POD never falls through the cracks.
            if stamp_a < end:
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
        ctx: AdminContext | None,
        *,
        merchant_id: str,
        period_start: datetime | None = None,
        period_end: datetime | None = None,
    ) -> dict[str, Any]:
        """One consolidated invoice per merchant per billing period (weekly/biweekly/monthly).

        Each delivered order becomes a line. Orders that already have a legacy per-order
        invoice are skipped, so existing invoices stay valid and nothing is billed twice.
        ``ctx=None`` means the scheduled worker run (audited as system).
        """
        merchant = get_merchant(db, merchant_id)
        if not merchant:
            raise LookupError("merchant_not_found")
        start, end = self._resolve_period(merchant, period_start, period_end)
        orders = self._eligible_orders(db, merchant_id, start, end)
        actor_type = "admin" if ctx else "system"
        actor_id = ctx.user.id if ctx else None
        created: list[dict[str, Any]] = []

        if orders:
            from porterchain_api.admin_engine.platform_settings import invoice_number_prefix
            from porterchain_api.platform.merchant_billing import order_tax_split
            from porterchain_api.merchant_engine.invoice_reminder import primary_billing_email
            from porterchain_api.merchant_engine.reporting_metrics import channel_for_order_source

            terms = merchant.payment_terms or orders[0].payment_terms
            now = datetime.now(UTC)
            # (order, split): pre-tax + destination-province tax; gross is what the merchant owes.
            line_specs = [(order, order_tax_split(db, order)) for order in orders]
            from porterchain_api.billing_engine.accessorials import add_fee_lines, fee_specs
            extras = fee_specs(db, merchant, orders)  # waiting / failed-delivery fees with evidence
            provinces = {s.province for _, s in line_specs}
            invoice = Invoice(
                invoice_number=allocate_invoice_number(db, prefix=invoice_number_prefix(db)),
                order_id=None,
                customer_id=None,
                merchant_id=merchant_id,
                amount_cents=sum(s.gross_cents for _, s in [*line_specs, *extras]),
                tax_cents=sum(s.tax_cents for _, s in [*line_specs, *extras]),
                tax_province=next(iter(provinces)) if len(provinces) == 1 else None,
                fees_cents=0,
                currency=orders[0].currency or "cad",
                due_at=_aware(invoice_due_date(now, terms)),
                issued_at=now,
                billing_period_start=_aware(start),
                billing_period_end=_aware(end),
                billing_kind="cycle",
            )
            db.add(invoice)
            db.flush()
            ensure_payment_reference(db, invoice)

            pricing_model = getattr(merchant, "pricing_model", None) or "distance"
            for order, split in line_specs:
                channel = channel_for_order_source(order.order_source)
                db.add(
                    InvoiceLine(
                        invoice_id=invoice.id,
                        order_id=order.id,
                        description=(
                            f"Delivery {order.order_number}"
                            f" · {channel or 'portal'}/{pricing_model}"
                        )[:255],
                        amount_cents=split.pretax_cents,
                        tax_cents=split.tax_cents,
                        tax_province=split.province,
                    )
                )
                if OrderState(order.state) == OrderState.DELIVERED:
                    transition_order_state(
                        db,
                        order,
                        OrderState.POD_COMPLETED,
                        event_type="order.pod_completed",
                        actor_type=actor_type,
                        actor_id=actor_id,
                        payload={"merchant_ar": True},
                    )
                    db.refresh(order)
                if OrderState(order.state) != OrderState.INVOICED:
                    # No email keys here: the merchant gets ONE email for the cycle invoice
                    # (merchant.invoice_generated below), not one per delivery.
                    transition_order_state(
                        db,
                        order,
                        OrderState.INVOICED,
                        event_type=BookingEvents.ORDER_INVOICED,
                        actor_type=actor_type,
                        actor_id=actor_id,
                        payload={
                            "invoice_id": invoice.id,
                            "invoice_number": invoice.invoice_number,
                            "merchant_id": merchant_id,
                            "order_id": order.id,
                            "order_number": order.order_number,
                            "amount_cents": split.gross_cents,
                            "merchant_ar": True,
                            "merchant_ar_cycle": True,
                        },
                    )
            add_fee_lines(db, invoice.id, extras)
            db.flush()
            from porterchain_api.admin_engine.merchant_ar_cycles import apply_available_credit

            credit_applied = apply_available_credit(db, invoice, actor=actor_id)

            emit_event(
                db,
                event_type=MerchantEvents.MERCHANT_INVOICE_GENERATED,
                aggregate_type="merchant",
                aggregate_id=merchant_id,
                correlation_id=invoice.id,
                actor_type=actor_type,
                actor_id=actor_id,
                payload={
                    "invoice_id": invoice.id,
                    "invoice_number": invoice.invoice_number,
                    "payment_reference": invoice.payment_reference,
                    "merchant_id": merchant_id,
                    "merchant_name": merchant.company_name,
                    "merchant_email": primary_billing_email(merchant),
                    "order_count": len(line_specs),
                    "amount_cents": invoice.amount_cents,
                    "amount_display": f"${(invoice.amount_cents or 0) / 100:.2f} {(invoice.currency or 'cad').upper()}",
                    "billing_kind": "cycle",
                },
            )
            created.append(
                {
                    "invoice_id": invoice.id,
                    "invoice_number": invoice.invoice_number,
                    "payment_reference": invoice.payment_reference,
                    "order_count": len(line_specs),
                    "order_ids": [o.id for o, _ in line_specs],
                    "amount_cents": invoice.amount_cents,
                    "credit_applied_cents": credit_applied,
                    "due_at": invoice.due_at,
                }
            )

        db.flush()
        log_admin_audit(
            db,
            ctx,
            action="finance.merchant_ar.generate" if ctx else "finance.merchant_ar.generate_scheduled",
            resource_type="merchant",
            resource_id=merchant_id,
            payload={
                "period_start": start.isoformat(),
                "period_end": end.isoformat(),
                "created": len(created),
                "order_count": len(orders),
                "invoice_ids": [c["invoice_id"] for c in created],
            },
        )
        db.commit()
        return {
            "merchant_id": merchant_id,
            "period_start": _aware(start),
            "period_end": _aware(end),
            "created_count": len(created),
            "skipped_count": 0,
            "order_count": len(orders),
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
        source: dict[str, Any] | None = None,
        commit: bool = True,
    ) -> dict[str, Any]:
        """Record an offline payment. Partial payments leave a balance; any excess over
        the outstanding amount becomes merchant credit (applied to the next cycle invoice)."""
        method_n = (method or "").strip().lower()
        if method_n not in OFFLINE_METHODS:
            raise ValueError("invalid_payment_method")

        invoice = db.query(Invoice).filter(Invoice.id == invoice_id).with_for_update().first()
        if not invoice:
            raise LookupError("invoice_not_found")
        order = db.query(Order).filter(Order.id == invoice.order_id).first() if invoice.order_id else None
        if invoice.order_id and not order:
            raise LookupError("order_not_found")

        if order is not None and not int(invoice.amount_paid_cents or 0):
            existing = (
                db.query(Payment)
                .filter(Payment.order_id == order.id, Payment.status == "SUCCEEDED")
                .first()
            )
            if existing:
                raise ValueError("already_paid")

        merchant_id = invoice.merchant_id or (order.merchant_id if order else None)
        terms = (order.payment_terms if order else None)
        status = invoice_status(invoice, order, None, terms=terms)
        outstanding = outstanding_cents(invoice, status)
        if outstanding <= 0:
            raise ValueError("already_paid" if status == "paid" else "nothing_outstanding")
        received = int(amount_cents) if amount_cents is not None else outstanding
        if received <= 0:
            raise ValueError("invalid_amount")
        settle_cents = min(received, outstanding)
        excess_cents = received - settle_cents
        if excess_cents and not merchant_id:
            raise ValueError("overpayment_requires_merchant")

        invoice.amount_paid_cents = int(invoice.amount_paid_cents or 0) + settle_cents
        fully_paid = invoice.amount_paid_cents >= invoice_total_cents(invoice)
        when = _aware(paid_at) or datetime.now(UTC)
        if fully_paid:
            invoice.paid_at = when

        pay = Payment(
            quote_id=None,
            # Only the settling payment links to the order: order screens treat a
            # SUCCEEDED order payment as "paid in full".
            order_id=order.id if (order is not None and fully_paid) else None,
            invoice_id=invoice.id,
            customer_id=order.customer_id if order else None,
            status="SUCCEEDED",
            amount_cents=received,
            currency=invoice.currency or (order.currency if order else None) or "cad",
            payment_method=method_n,
            payment_reference=(reference or "")[:32] or None,
            transaction_id=f"offline:{invoice.id}",
        )
        db.add(pay)
        db.flush()

        entry = BillingLedgerEntry(
            kind="merchant_offline_payment",
            payment_id=pay.id,
            invoice_id=invoice.id,
            order_id=order.id if order else None,
            merchant_id=merchant_id,
            amount_cents=settle_cents,
            currency=pay.currency,
            status="recorded",
            metadata_json={
                "invoice_id": invoice.id,
                "invoice_number": invoice.invoice_number,
                "method": method_n,
                "reference": reference,
                "received_cents": received,
                "excess_cents": excess_cents,
                "paid_at": when.isoformat(),
                **({"source": source} if source else {}),
            },
        )
        db.add(entry)
        credit_entry = None
        if excess_cents:
            credit_entry = add_merchant_credit(
                db,
                merchant_id=merchant_id,
                amount_cents=excess_cents,
                source={"invoice_id": invoice.id, "payment_id": pay.id, "method": method_n},
            )

        from porterchain_api.merchant_engine.invoice_reminder import primary_billing_email

        billed = get_merchant(db, merchant_id) if merchant_id else None
        emit_event(
            db,
            event_type=MerchantEvents.MERCHANT_PAYMENT_RECEIVED,
            aggregate_type="merchant",
            aggregate_id=merchant_id or "",
            correlation_id=invoice.id,
            actor_type="admin",
            actor_id=ctx.user.id if ctx else None,
            payload={
                "invoice_id": invoice.id,
                "payment_id": pay.id,
                "amount_cents": received,
                "method": method_n,
                "merchant_id": merchant_id,
                "merchant_email": primary_billing_email(billed) if billed else None,
            },
        )
        log_admin_audit(
            db,
            ctx,
            action="finance.merchant_ar.record_payment",
            resource_type="invoice",
            resource_id=invoice.id,
            payload={
                "payment_id": pay.id,
                "amount_cents": received,
                "applied_cents": settle_cents,
                "excess_cents": excess_cents,
                "method": method_n,
                "reference": reference,
            },
        )
        if commit:
            db.commit()
        else:
            db.flush()
        balance = max(0, invoice_total_cents(invoice) - int(invoice.amount_paid_cents or 0))
        return {
            "invoice_id": invoice.id,
            "payment_id": pay.id,
            "amount_cents": received,
            "applied_cents": settle_cents,
            "excess_cents": excess_cents,
            "credit_ledger_id": credit_entry.id if credit_entry else None,
            "balance_cents": balance,
            "status": "paid" if fully_paid else "partial",
            "method": method_n,
            "ledger_id": entry.id,
        }



def is_cycle_billed(db: Session, order: Order) -> bool:
    from porterchain_api.admin_engine.merchant_ar_cycles import is_cycle_billed as _impl

    return _impl(db, order)

# Re-exports kept for existing importers (integration).
from porterchain_api.booking_engine.numbers import generate_invoice_number  # noqa: E402, F401
