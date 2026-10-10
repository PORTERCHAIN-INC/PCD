"""Merchant billing — orchestrates billing_engine for net-terms merchants."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from porterchain_api.billing_engine.ar import MerchantAr, merchant_ar
from porterchain_api.billing_engine.merchant_service import (
    BILLING_CYCLES,
    billing_period_bounds,
    effective_payment_terms,
    invoice_status,
    merchant_uses_stripe,
    net_terms_days,
    outstanding_cents,
    serialize_invoice_row,
)
from porterchain_api.billing_engine.models import BillingLedgerEntry
from porterchain_api.booking_models import Invoice, Order, Payment
from porterchain_api.domain.states import OrderState
from porterchain_api.merchant_engine import reporting_metrics as report_engine
from porterchain_api.merchant_engine.rbac import MerchantContext


class MerchantBillingService:
    def _merchant_order_ids(self, db: Session, merchant_id: str):
        return db.query(Order.id).filter(Order.merchant_id == merchant_id)

    def _payment_for_order(self, db: Session, order_id: str) -> Payment | None:
        return (
            db.query(Payment)
            .filter(Payment.order_id == order_id)
            .order_by(Payment.created_at.desc())
            .first()
        )

    def overview(self, db: Session, ctx: MerchantContext) -> dict[str, Any]:
        from porterchain_api.merchant_engine.billing_pack import overview_payload

        return overview_payload(self, db, ctx, billing_cycles=BILLING_CYCLES)

    def statement_summary(self, db: Session, ctx: MerchantContext) -> dict:
        merchant = ctx.merchant
        period_start, period_end = billing_period_bounds(
            merchant.billing_cycle,
            anchor=merchant.activated_at or merchant.created_at,
        )
        monthly_orders = (
            db.query(func.count(Order.id))
            .filter(
                Order.merchant_id == merchant.id,
                Order.created_at >= period_start,
                Order.created_at < period_end,
            )
            .scalar()
            or 0
        )
        monthly_spend = (
            db.query(func.coalesce(func.sum(Order.amount_cents), 0))
            .filter(
                Order.merchant_id == merchant.id,
                Order.created_at >= period_start,
                Order.created_at < period_end,
                Order.state.notin_([OrderState.CANCELLED.value, OrderState.REFUNDED.value]),
            )
            .scalar()
            or 0
        )
        ar = self._ar(db, ctx)

        return {
            "payment_terms": merchant.payment_terms,
            "billing_cycle": merchant.billing_cycle,
            "net_terms_days": net_terms_days(merchant.payment_terms),
            "stripe_enabled": merchant_uses_stripe(merchant),
            "outstanding_balance_cents": ar.outstanding_cents,
            "outstanding_invoices_cents": ar.invoiced_cents,
            "uninvoiced_orders_cents": ar.uninvoiced_cents,
            "credit_notes_cents": ar.credits_cents,
            "monthly_orders": int(monthly_orders),
            "monthly_spend_cents": int(monthly_spend),
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
        }

    def statement_detail(self, db: Session, ctx: MerchantContext) -> dict[str, Any]:
        merchant = ctx.merchant
        period_start, period_end = billing_period_bounds(
            merchant.billing_cycle,
            anchor=merchant.activated_at or merchant.created_at,
        )
        lines: list[dict[str, Any]] = []

        orders = (
            db.query(Order)
            .filter(
                Order.merchant_id == merchant.id,
                Order.created_at >= period_start,
                Order.created_at < period_end,
                Order.state.notin_([OrderState.CANCELLED.value, OrderState.REFUNDED.value]),
            )
            .order_by(Order.created_at.asc())
            .all()
        )
        for order in orders:
            inv = db.query(Invoice).filter(Invoice.order_id == order.id).first()
            payment = self._payment_for_order(db, order.id)
            lines.append(
                {
                    "type": "order",
                    "date": order.created_at.isoformat() if order.created_at else None,
                    "reference": order.order_number,
                    "tracking_number": order.tracking_number,
                    "description": f"Delivery {order.tracking_number}",
                    "amount_cents": order.amount_cents,
                    "tax_cents": inv.tax_cents if inv else 0,
                    "invoiced": inv is not None,
                    "invoice_number": inv.invoice_number if inv else None,
                    "status": invoice_status(inv, order, payment, terms=merchant.payment_terms)
                    if inv
                    else "uninvoiced",
                }
            )

        for entry in self._merchant_ledger(db, ctx):
            if entry.kind == "credit_note":
                lines.append(
                    {
                        "type": "credit_note",
                        "date": entry.created_at.isoformat() if entry.created_at else None,
                        "reference": entry.id,
                        "description": (entry.metadata_json or {}).get("reason", "Credit note"),
                        "amount_cents": -(entry.amount_cents or 0),
                        "tax_cents": 0,
                    }
                )

        for pay, order in (
            db.query(Payment, Order)
            .join(Order, Payment.order_id == Order.id)
            .filter(
                Order.merchant_id == merchant.id,
                Payment.created_at >= period_start,
                Payment.created_at < period_end,
            )
            .order_by(Payment.created_at.asc())
            .all()
        ):
            lines.append(
                {
                    "type": "payment",
                    "date": pay.created_at.isoformat() if pay.created_at else None,
                    "reference": pay.payment_reference or pay.id,
                    "description": f"Payment ({pay.payment_method or 'net_terms'})",
                    "amount_cents": -pay.amount_cents,
                    "tax_cents": 0,
                }
            )

        lines.sort(key=lambda x: x.get("date") or "")

        merchant_id = merchant.id
        period_start_dt = period_start
        delivery = report_engine.delivery_performance(db, merchant_id, since=period_start_dt)
        invoices = report_engine.invoice_summary(db, merchant_id, since=period_start_dt)
        avg_hours = delivery.get("avg_delivery_hours")

        return {
            **self.statement_summary(db, ctx),
            "line_items": lines,
            "line_items_total_cents": sum(int(l.get("amount_cents") or 0) for l in lines if l["type"] == "order"),
            "delivery_success_percent": delivery["delivery_success_percent"],
            "average_delivery_minutes": int(avg_hours * 60) if avg_hours is not None else None,
            "top_routes": report_engine.top_routes(db, merchant_id, since=period_start_dt),
            "invoice_summary_cents": invoices["invoice_total_cents"],
        }

    def list_invoices(self, db: Session, ctx: MerchantContext) -> list[dict]:
        return self.list_invoices_enriched(db, ctx)

    def list_invoices_enriched(self, db: Session, ctx: MerchantContext) -> list[dict]:
        rows = self._merchant_invoices(db, ctx)
        result: list[dict] = []
        include_stripe = merchant_uses_stripe(ctx.merchant)
        for inv, order in rows:
            payment = self._payment_for_order(db, inv.order_id) if inv.order_id else None
            row = serialize_invoice_row(
                inv,
                order,
                payment,
                terms=effective_payment_terms(order, ctx.merchant),
                include_stripe=include_stripe,
            )
            result.append(row)
        return result

    def invoice_detail(self, db: Session, ctx: MerchantContext, invoice_id: str) -> dict[str, Any]:
        """Full merchant SOT for one invoice: lines, channel, pricing_model, quote, payability."""

        from porterchain_api.billing_engine.ar import aging_bucket
        from porterchain_api.billing_engine.merchant_service import (
            invoice_due_date,
            invoice_total_cents,
        )
        from porterchain_api.billing_engine.models import InvoiceLine

        row = (
            db.query(Invoice, Order)
            .outerjoin(Order, Invoice.order_id == Order.id)
            .filter(Invoice.id == invoice_id)
            .first()
        )
        if not row:
            raise LookupError("invoice_not_found")
        inv, order = row
        merchant_id = inv.merchant_id or (order.merchant_id if order else None)
        if merchant_id != ctx.merchant.id:
            raise LookupError("invoice_not_found")

        payment = self._payment_for_order(db, inv.order_id) if inv.order_id else None
        terms = effective_payment_terms(order, ctx.merchant)
        status = invoice_status(inv, order, payment, terms=terms)
        outstanding = outstanding_cents(inv, status)
        due = inv.due_at or invoice_due_date(inv.created_at, terms)
        due_iso = None
        aging = None
        if due:
            due_naive = due.replace(tzinfo=None) if getattr(due, "tzinfo", None) else due
            due_iso = due_naive.isoformat()
            now = datetime.now(UTC).replace(tzinfo=None)
            if status == "overdue" and now > due_naive:
                aging = aging_bucket(max(0, (now - due_naive).days))
            elif status not in ("paid", "void", "cancelled"):
                aging = "Current"

        pricing_model = getattr(ctx.merchant, "pricing_model", None) or "distance"
        line_rows = (
            db.query(InvoiceLine).filter(InvoiceLine.invoice_id == inv.id).order_by(InvoiceLine.created_at.asc()).all()
        )
        lines: list[dict[str, Any]] = []
        if line_rows:
            for ln in line_rows:
                o = (
                    db.query(Order).filter(Order.id == ln.order_id).first()
                    if ln.order_id
                    else order
                )
                lines.append(self._invoice_line_sot(db, ln, o, pricing_model))
        elif order:
            # Synthetic single line from the linked order (common for 1:1 invoices).
            lines.append(
                self._order_as_invoice_line(db, order, inv, pricing_model)
            )

        line_sum = sum(int(x.get("amount_cents") or 0) for x in lines)
        # Prefer invoice total; if lines empty keep invoice amount.
        if not lines:
            lines = [
                {
                    "line_id": None,
                    "order_id": inv.order_id,
                    "order_number": order.order_number if order else None,
                    "tracking_number": order.tracking_number if order else None,
                    "description": f"Invoice {inv.invoice_number}",
                    "amount_cents": invoice_total_cents(inv),
                    "tax_cents": int(inv.tax_cents or 0),
                    "channel": None,
                    "pricing_model": pricing_model,
                    "quote_breakdown": None,
                    "rate_quote_id": None,
                    "rate_quote_cents": None,
                }
            ]
            line_sum = invoice_total_cents(inv)

        payable = outstanding > 0 and status not in ("paid", "void", "cancelled")
        detail = {
            "invoice_id": inv.id,
            "invoice_number": inv.invoice_number,
            "status": status,
            "payment_terms": terms or "NET_30",
            "due_date": due_iso,
            "aging_bucket": aging,
            "amount_cents": int(inv.amount_cents or 0),
            "tax_cents": int(inv.tax_cents or 0),
            "fees_cents": int(inv.fees_cents or 0),
            "outstanding_cents": outstanding,
            "currency": inv.currency or "cad",
            "created_at": inv.created_at,
            "pdf_url": inv.pdf_url,
            "pay_url": f"/v1/merchant/billing/invoices/{inv.id}/pay" if payable else None,
            "payable": payable,
            "lines": lines,
            "lines_total_cents": line_sum,
            "remittance_memo": inv.invoice_number,
        }
        try:
            from porterchain_api.merchant_engine.commerce_metrics import (
                check_invoice_detail_consistency,
            )

            mismatches = check_invoice_detail_consistency(detail)
            detail["ar_consistency"] = {"ok": not mismatches, "reasons": mismatches}
        except Exception:
            detail["ar_consistency"] = {"ok": True, "reasons": []}
        return detail

    def _channel_for_order(self, order: Order | None) -> str | None:
        if not order:
            return None
        from porterchain_api.merchant_engine.reporting_metrics import (
            channel_for_order_source,
        )

        return channel_for_order_source(order.order_source)

    def _order_as_invoice_line(
        self,
        db: Session,
        order: Order,
        inv: Invoice,
        pricing_model: str,
    ) -> dict[str, Any]:
        from porterchain_api.billing_engine.models import InvoiceLine

        synthetic = InvoiceLine(
            invoice_id=inv.id,
            order_id=order.id,
            description=f"Delivery {order.order_number}",
            amount_cents=int(order.amount_cents or inv.amount_cents or 0),
            tax_cents=int(inv.tax_cents or 0),
        )
        return self._invoice_line_sot(db, synthetic, order, pricing_model)

    def _invoice_line_sot(
        self,
        db: Session,
        line: Any,
        order: Order | None,
        pricing_model: str,
    ) -> dict[str, Any]:
        from porterchain_api.merchant_models import ShopifyRateQuote

        compliance = (order.compliance_metadata or {}) if order else {}
        quote = compliance.get("quote") if isinstance(compliance.get("quote"), dict) else None
        shopify = compliance.get("shopify") if isinstance(compliance.get("shopify"), dict) else {}
        rate_quote_id = shopify.get("rate_quote_id")
        rate_quote_cents = shopify.get("rate_quote_cents")
        if rate_quote_id and rate_quote_cents is None:
            rq = db.get(ShopifyRateQuote, rate_quote_id)
            if rq:
                rate_quote_cents = rq.total_cents
        return {
            "line_id": getattr(line, "id", None),
            "order_id": getattr(line, "order_id", None) or (order.id if order else None),
            "order_number": order.order_number if order else None,
            "tracking_number": order.tracking_number if order else None,
            "description": getattr(line, "description", None) or "Delivery",
            "amount_cents": int(getattr(line, "amount_cents", 0) or 0),
            "tax_cents": int(getattr(line, "tax_cents", 0) or 0),
            "channel": self._channel_for_order(order),
            "pricing_model": pricing_model,
            "quote_breakdown": quote,
            "rate_quote_id": rate_quote_id,
            "rate_quote_cents": int(rate_quote_cents) if rate_quote_cents is not None else None,
        }

    def invoice_pdf(self, db: Session, ctx: MerchantContext, invoice_id: str) -> tuple[bytes, str]:
        from porterchain_api.reporting.order_documents import pdf_for_merchant_invoice

        detail = self.invoice_detail(db, ctx, invoice_id)
        return pdf_for_merchant_invoice(
            db,
            invoice_id,
            detail,
            merchant_name=ctx.merchant.company_name,
            merchant_email=ctx.merchant.email,
        )

    def remind_invoice(self, db: Session, ctx: MerchantContext, invoice_id: str) -> dict[str, Any]:
        from porterchain_api.merchant_engine.invoice_reminder import remind_invoice

        row = (
            db.query(Invoice, Order)
            .join(Order, Invoice.order_id == Order.id)
            .filter(Invoice.id == invoice_id, Order.merchant_id == ctx.merchant.id)
            .first()
        )
        if not row:
            raise LookupError("invoice_not_found")
        invoice, _order = row
        return remind_invoice(
            db,
            invoice,
            ctx.merchant,
            actor_type="merchant_user",
            actor_id=ctx.user.id,
        )

    def start_invoice_pay(
        self,
        db: Session,
        settings: Any,
        ctx: MerchantContext,
        invoice_id: str,
    ) -> dict[str, Any]:
        """Create Stripe Checkout for an open invoice (amount locked server-side)."""
        from porterchain_api.services.stripe_service import (
            create_invoice_checkout_session,
        )

        row = (
            db.query(Invoice, Order)
            .outerjoin(Order, Invoice.order_id == Order.id)
            .filter(Invoice.id == invoice_id)
            .first()
        )
        if not row:
            raise LookupError("invoice_not_found")
        inv, order = row
        merchant_id = inv.merchant_id or (order.merchant_id if order else None)
        if merchant_id != ctx.merchant.id:
            raise LookupError("invoice_not_found")

        payment = self._payment_for_order(db, inv.order_id) if inv.order_id else None
        terms = effective_payment_terms(order, ctx.merchant) if order else ctx.merchant.payment_terms
        status = invoice_status(inv, order, payment, terms=terms)
        due = outstanding_cents(inv, status)
        if due <= 0:
            raise ValueError("nothing_outstanding")
        if status in ("paid", "void", "cancelled"):
            raise ValueError("invoice_not_payable")

        try:
            from porterchain_api.merchant_engine.commerce_metrics import (
                note_commerce_event,
            )

            note_commerce_event("invoice_pay", "started")
            note_commerce_event("invoice_pay", "pay_started")  # ops-1 alias
        except Exception:
            pass

        pay = Payment(
            quote_id=None,
            order_id=inv.order_id,
            customer_id=inv.customer_id,
            invoice_id=inv.id,
            status="PENDING",
            amount_cents=due,
            currency=inv.currency or "cad",
            payment_method="stripe",
        )
        if not pay.id:
            from uuid import uuid4

            pay.id = str(uuid4())
        db.add(pay)
        db.flush()

        if getattr(settings, "allow_stripe_mock", False) and not getattr(
            settings, "stripe_secret", None
        ):
            self._settle_invoice_payment(
                db,
                invoice=inv,
                order=order,
                payment=pay,
                stripe_payment_intent_id=f"pi_mock_{pay.id[:8]}",
                receipt_url=None,
                session_id=f"cs_mock_{pay.id[:8]}",
            )
            db.commit()
            try:
                from porterchain_api.merchant_engine.commerce_metrics import (
                    note_commerce_event,
                )

                note_commerce_event("invoice_pay", "succeeded_mock")
            except Exception:
                pass
            return {
                "invoice_id": inv.id,
                "amount_cents": due,
                "currency": (inv.currency or "cad").upper(),
                "pay_url": None,
                "paid": True,
                "mock": True,
            }

        if not getattr(settings, "stripe_secret", None):
            raise RuntimeError("stripe_not_configured")

        url, session_id = create_invoice_checkout_session(
            settings,
            amount_cents=due,
            currency=inv.currency or "cad",
            invoice_id=inv.id,
            invoice_number=inv.invoice_number,
            merchant_id=ctx.merchant.id,
            payment_id=pay.id,
            customer_email=ctx.merchant.email,
        )
        pay.stripe_checkout_session_id = session_id
        db.commit()
        try:
            from porterchain_api.merchant_engine.commerce_metrics import (
                note_commerce_event,
            )

            note_commerce_event("invoice_pay", "checkout_created")
        except Exception:
            pass
        return {
            "invoice_id": inv.id,
            "amount_cents": due,
            "currency": (inv.currency or "cad").upper(),
            "pay_url": url,
            "session_id": session_id,
            "paid": False,
            "mock": False,
        }

    def start_pay_outstanding(
        self,
        db: Session,
        settings: Any,
        ctx: MerchantContext,
    ) -> dict[str, Any]:
        """One Checkout for all open invoices (server-locked sum)."""
        from uuid import uuid4

        from porterchain_api.services.stripe_service import (
            create_invoice_checkout_session,
        )

        open_rows = [
            r
            for r in self.list_invoices_enriched(db, ctx)
            if int(r.get("outstanding_cents") or 0) > 0
            and r.get("status") not in ("paid", "void", "cancelled")
        ]
        if not open_rows:
            raise ValueError("nothing_outstanding")
        total = sum(int(r["outstanding_cents"]) for r in open_rows)
        invoice_ids = [str(r["invoice_id"]) for r in open_rows]
        currency = (open_rows[0].get("currency") or "cad").lower()

        pay = Payment(
            quote_id=None,
            order_id=None,
            customer_id=None,
            invoice_id=None,
            status="PENDING",
            amount_cents=total,
            currency=currency,
            payment_method="stripe",
            payment_reference="pay_all",
        )
        pay.id = str(uuid4())
        db.add(pay)
        db.flush()

        # Stash invoice set on a ledger draft row for webhook reconciliation.
        batch = BillingLedgerEntry(
            kind="merchant_invoice_pay_batch",
            payment_id=pay.id,
            merchant_id=ctx.merchant.id,
            amount_cents=total,
            currency=currency,
            status="pending",
            metadata_json={"invoice_ids": invoice_ids},
        )
        db.add(batch)
        db.flush()

        if getattr(settings, "allow_stripe_mock", False) and not getattr(
            settings, "stripe_secret", None
        ):
            self._settle_invoice_batch(
                db,
                ctx.merchant.id,
                invoice_ids,
                payment=pay,
                stripe_payment_intent_id=f"pi_mock_batch_{pay.id[:8]}",
                receipt_url=None,
                session_id=f"cs_mock_batch_{pay.id[:8]}",
            )
            db.commit()
            return {
                "amount_cents": total,
                "currency": currency.upper(),
                "invoice_ids": invoice_ids,
                "pay_url": None,
                "paid": True,
                "mock": True,
            }

        if not getattr(settings, "stripe_secret", None):
            raise RuntimeError("stripe_not_configured")

        url, session_id = create_invoice_checkout_session(
            settings,
            amount_cents=total,
            currency=currency,
            invoice_id="batch",
            invoice_number=f"BATCH-{len(invoice_ids)}",
            merchant_id=ctx.merchant.id,
            payment_id=pay.id,
            customer_email=ctx.merchant.email,
        )
        # Overwrite metadata mentally: webhook uses payment_id → batch ledger.
        pay.stripe_checkout_session_id = session_id
        batch.metadata_json = {
            **dict(batch.metadata_json or {}),
            "session_id": session_id,
            "invoice_ids": invoice_ids,
        }
        db.commit()
        return {
            "amount_cents": total,
            "currency": currency.upper(),
            "invoice_ids": invoice_ids,
            "pay_url": url,
            "session_id": session_id,
            "paid": False,
            "mock": False,
        }

    def _settle_invoice_batch(
        self,
        db: Session,
        merchant_id: str,
        invoice_ids: list[str],
        *,
        payment: Payment,
        stripe_payment_intent_id: str | None,
        receipt_url: str | None,
        session_id: str | None,
    ) -> None:
        if payment.status == "SUCCEEDED":
            return
        payment.status = "SUCCEEDED"
        payment.stripe_payment_intent_id = stripe_payment_intent_id or payment.stripe_payment_intent_id
        payment.receipt_url = receipt_url or payment.receipt_url
        if session_id:
            payment.stripe_checkout_session_id = session_id
        payment.transaction_id = stripe_payment_intent_id or payment.transaction_id
        for iid in invoice_ids:
            row = (
                db.query(Invoice, Order)
                .outerjoin(Order, Invoice.order_id == Order.id)
                .filter(Invoice.id == iid)
                .first()
            )
            if not row:
                continue
            inv, order = row
            mid = inv.merchant_id or (order.merchant_id if order else None)
            if mid != merchant_id:
                continue
            child = Payment(
                quote_id=None,
                order_id=inv.order_id,
                customer_id=inv.customer_id,
                invoice_id=inv.id,
                status="SUCCEEDED",
                amount_cents=int(inv.amount_cents or 0) + int(inv.fees_cents or 0),
                currency=inv.currency or payment.currency,
                payment_method="stripe",
                stripe_payment_intent_id=stripe_payment_intent_id,
                stripe_checkout_session_id=session_id,
                receipt_url=receipt_url,
                transaction_id=stripe_payment_intent_id,
            )
            from uuid import uuid4

            child.id = str(uuid4())
            db.add(child)
            inv.status = "paid"
            db.add(
                BillingLedgerEntry(
                    kind="merchant_stripe_invoice_payment",
                    payment_id=child.id,
                    invoice_id=inv.id,
                    order_id=inv.order_id,
                    merchant_id=merchant_id,
                    amount_cents=child.amount_cents,
                    currency=child.currency,
                    status="recorded",
                    metadata_json={
                        "batch_payment_id": payment.id,
                        "invoice_id": inv.id,
                    },
                )
            )
        for entry in (
            db.query(BillingLedgerEntry)
            .filter(
                BillingLedgerEntry.payment_id == payment.id,
                BillingLedgerEntry.kind == "merchant_invoice_pay_batch",
            )
            .all()
        ):
            entry.status = "recorded"

    def _settle_invoice_payment(
        self,
        db: Session,
        *,
        invoice: Invoice,
        order: Order | None,
        payment: Payment,
        stripe_payment_intent_id: str | None,
        receipt_url: str | None,
        session_id: str | None = None,
    ) -> None:
        if payment.status == "SUCCEEDED":
            return
        payment.status = "SUCCEEDED"
        payment.stripe_payment_intent_id = stripe_payment_intent_id or payment.stripe_payment_intent_id
        payment.receipt_url = receipt_url or payment.receipt_url
        if session_id:
            payment.stripe_checkout_session_id = session_id
        payment.transaction_id = stripe_payment_intent_id or payment.transaction_id
        invoice.status = "paid"
        entry = BillingLedgerEntry(
            kind="merchant_stripe_invoice_payment",
            payment_id=payment.id,
            order_id=order.id if order else invoice.order_id,
            merchant_id=invoice.merchant_id or (order.merchant_id if order else None),
            amount_cents=payment.amount_cents,
            currency=payment.currency,
            status="recorded",
            metadata_json={
                "invoice_id": invoice.id,
                "invoice_number": invoice.invoice_number,
                "stripe_payment_intent_id": stripe_payment_intent_id,
                "session_id": session_id,
            },
        )
        db.add(entry)
        merchant_id = invoice.merchant_id or (order.merchant_id if order else None)
        if merchant_id:
            from porterchain_api.merchant_models import MerchantAuditLog

            db.add(
                MerchantAuditLog(
                    merchant_id=merchant_id,
                    actor_user_id=None,
                    action="invoice.paid_stripe",
                    resource_type="invoice",
                    resource_id=invoice.id,
                    payload={
                        "invoice_number": invoice.invoice_number,
                        "amount_cents": payment.amount_cents,
                        "session_id": session_id,
                        "stripe_payment_intent_id": stripe_payment_intent_id,
                    },
                )
            )
        # Receipt email to billing contact (Mailpit locally).
        try:
            from porterchain_api.merchant_engine.invoice_reminder import (
                primary_billing_email,
            )
            from porterchain_api.merchant_models import Merchant
            from porterchain_api.platform.receipt_notify import emit_receipt_generated

            merchant = db.get(Merchant, merchant_id) if merchant_id else None
            to_email = primary_billing_email(merchant) if merchant else None
            amount_display = f"${(payment.amount_cents or 0) / 100:.2f} {(payment.currency or 'cad').upper()}"
            payload = {
                "invoice_id": invoice.id,
                "invoice_number": invoice.invoice_number,
                "order_id": order.id if order else invoice.order_id,
                "order_number": order.order_number if order else None,
                "tracking_number": order.tracking_number if order else None,
                "merchant_id": merchant_id,
                "merchant_name": merchant.company_name if merchant else None,
                "email": to_email or (merchant.email if merchant else None),
                "merchant_email": to_email or (merchant.email if merchant else None),
                "amount_cents": payment.amount_cents,
                "amount_display": amount_display,
                "currency": payment.currency or "cad",
                "receipt_url": receipt_url or payment.receipt_url,
                "receipt_number": getattr(invoice, "receipt_number", None),
            }
            emit_receipt_generated(
                db,
                invoice_id=invoice.id,
                correlation_id=order.id if order else invoice.id,
                payload=payload,
            )
        except Exception:
            pass
        try:
            from porterchain_api.merchant_engine.commerce_metrics import (
                note_commerce_event,
            )

            note_commerce_event("invoice_pay", "settled")
            note_commerce_event("invoice_pay", "succeeded")  # ops-1 alias
        except Exception:
            pass

    def list_payments(self, db: Session, ctx: MerchantContext) -> list[dict[str, Any]]:
        from porterchain_api.merchant_engine.billing_views import (
            list_payments as _list_payments,
        )

        return _list_payments(self, db, ctx)

    def list_credit_notes(self, db: Session, ctx: MerchantContext) -> list[dict[str, Any]]:
        from porterchain_api.merchant_engine.billing_views import (
            list_credit_notes as _list_credit_notes,
        )

        return _list_credit_notes(self, db, ctx)

    def billing_history(self, db: Session, ctx: MerchantContext) -> list[dict[str, Any]]:
        from porterchain_api.merchant_engine.billing_views import (
            billing_history as _billing_history,
        )

        return _billing_history(self, db, ctx)

    def tax_summary(self, db: Session, ctx: MerchantContext) -> dict[str, Any]:
        from porterchain_api.merchant_engine.billing_views import (
            tax_summary as _tax_summary,
        )

        return _tax_summary(self, db, ctx)

    def contract_pricing(self, db: Session, ctx: MerchantContext) -> dict[str, Any]:
        from porterchain_api.merchant_engine.billing_views import (
            contract_pricing as _contract_pricing,
        )

        return _contract_pricing(self, db, ctx)

    def export_invoices_csv(self, db: Session, ctx: MerchantContext) -> str:
        from porterchain_api.merchant_engine.billing_views import (
            export_invoices_csv as _export,
        )

        return _export(self, db, ctx)

    def export_statement_csv(self, db: Session, ctx: MerchantContext) -> str:
        from porterchain_api.merchant_engine.billing_views import (
            export_statement_csv as _export,
        )

        return _export(self, db, ctx)

    def export_history_csv(self, db: Session, ctx: MerchantContext) -> str:
        from porterchain_api.merchant_engine.billing_views import (
            export_history_csv as _export,
        )

        return _export(self, db, ctx)

    def _merchant_invoices(self, db: Session, ctx: MerchantContext) -> list[tuple[Invoice, Order]]:
        from porterchain_api.merchant_engine.billing_views import merchant_invoices

        return merchant_invoices(db, ctx)

    def _merchant_ledger(self, db: Session, ctx: MerchantContext) -> list[BillingLedgerEntry]:
        from porterchain_api.merchant_engine.billing_views import merchant_ledger

        return merchant_ledger(db, ctx)

    def _ar(self, db: Session, ctx: MerchantContext) -> MerchantAr:
        return merchant_ar(db, ctx.merchant)

    def outstanding_balance(self, db: Session, ctx: MerchantContext) -> int:
        return self._ar(db, ctx).outstanding_cents
