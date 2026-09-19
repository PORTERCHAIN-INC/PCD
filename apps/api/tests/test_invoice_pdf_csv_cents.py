"""PDF / CSV / GET invoice detail must report the same cents."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from porterchain_api.merchant_engine.billing_service import MerchantBillingService
from porterchain_api.reporting.order_documents import build_invoice_pdf
from porterchain_api.booking_models import Order


def test_build_invoice_pdf_embeds_detail_cents():
    order = Order(
        order_number="PC-1",
        tracking_number="TRK1",
        state="INVOICED",
        amount_cents=6100,
        currency="cad",
        pickup={"formatted": "A"},
        dropoff={"formatted": "B"},
    )
    pdf = build_invoice_pdf(
        order,
        invoice_number="INV-1",
        amount_cents=6100,
        tax_cents=300,
        fees_cents=100,
        outstanding_cents=6200,
        currency="cad",
        lines=[
            {
                "description": "Delivery PC-1",
                "amount_cents": 6100,
                "channel": "shopify",
                "pricing_model": "fsa",
            }
        ],
    )
    # reportlab PDFs are binary but embed plain strings for these labels
    text = pdf.decode("latin-1", errors="ignore")
    assert "Amount: $61.00 CAD" in text
    assert "Tax: $3.00 CAD" in text
    assert "Fees: $1.00 CAD" in text
    assert "Outstanding: $62.00 CAD" in text
    assert "shopify/fsa" in text


def test_csv_and_detail_same_amount_cents():
    db = MagicMock()
    merchant = SimpleNamespace(id="m1", pricing_model="fsa", payment_terms="NET_30", email="a@b.c", company_name="Co")
    ctx = SimpleNamespace(merchant=merchant, user=SimpleNamespace(id="u1"))
    order = SimpleNamespace(
        id="o1",
        merchant_id="m1",
        order_number="PC-1",
        tracking_number="TRK1",
        order_source="SHOPIFY",
        amount_cents=6100,
        payment_terms="NET_30",
        compliance_metadata={},
        pickup={},
        dropoff={},
        state="INVOICED",
    )
    inv = SimpleNamespace(
        id="inv1",
        invoice_number="INV-1",
        merchant_id="m1",
        order_id="o1",
        customer_id=None,
        amount_cents=6100,
        tax_cents=300,
        fees_cents=0,
        currency="cad",
        status="open",
        due_at=None,
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        pdf_url=None,
        last_reminded_at=None,
        receipt_number=None,
    )

    line_q = MagicMock()
    line_q.filter.return_value.order_by.return_value.all.return_value = []

    def query_side(*models):
        name = " ".join(getattr(m, "__name__", str(m)) for m in models)
        if "InvoiceLine" in name:
            return line_q
        m = MagicMock()
        m.outerjoin.return_value.filter.return_value.first.return_value = (inv, order)
        m.filter.return_value.first.return_value = (inv, order)
        m.join.return_value.filter.return_value.first.return_value = (inv, order)
        m.filter.return_value.order_by.return_value.all.return_value = []
        return m

    db.query.side_effect = query_side
    db.get.side_effect = lambda model, key: order if key == "o1" else inv if key == "inv1" else None

    svc = MerchantBillingService()
    with (
        patch.object(svc, "_payment_for_order", return_value=None),
        patch(
            "porterchain_api.merchant_engine.billing_service.invoice_status",
            return_value="sent",
        ),
        patch(
            "porterchain_api.merchant_engine.billing_service.outstanding_cents",
            return_value=6100,
        ),
        patch(
            "porterchain_api.merchant_engine.billing_service.effective_payment_terms",
            return_value="NET_30",
        ),
        patch.object(
            svc,
            "list_invoices_enriched",
            return_value=[
                {
                    "invoice_id": "inv1",
                    "invoice_number": "INV-1",
                    "order_number": "PC-1",
                    "tracking_number": "TRK1",
                    "status": "sent",
                    "amount_cents": 6100,
                    "tax_cents": 300,
                    "outstanding_cents": 6100,
                    "currency": "cad",
                    "payment_terms": "NET_30",
                    "due_date": None,
                    "created_at": "2026-01-01T00:00:00",
                }
            ],
        ),
    ):
        detail = svc.invoice_detail(db, ctx, "inv1")
        csv_text = svc.export_invoices_csv(db, ctx)
        pdf, filename = svc.invoice_pdf(db, ctx, "inv1")

    assert detail["amount_cents"] == 6100
    assert detail["tax_cents"] == 300
    assert "6100" in csv_text
    assert "INV-1" in csv_text
    assert filename == "invoice-INV-1.pdf"
    text = pdf.decode("latin-1", errors="ignore")
    assert "Amount: $61.00 CAD" in text
    assert "Tax: $3.00 CAD" in text
