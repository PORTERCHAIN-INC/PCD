"""GST/HST filing report (GST34 lines) and QuickBooks / Xero invoice CSV exports.

Basis: invoices *issued* in the period (accrual — CRA makes tax collectible when the
invoice is issued). Void invoices are excluded. Tax is grouped by the destination
province stored on each invoice line (cycle invoices) or invoice (per-order).

Line 106 (input tax credits) needs PorterChain's purchase records, which PCD does not
hold — it is returned as 0 with a note, to be filled in by the bookkeeper.
"""

from __future__ import annotations

import csv
import io
from collections import defaultdict
from datetime import datetime
from typing import Any

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from porterchain_api.billing_engine.models import InvoiceLine
from porterchain_api.booking_models import Customer, Invoice, Order


def _issued(inv: Invoice) -> datetime | None:
    return inv.issued_at or inv.created_at


def invoices_in_period(db: Session, start: datetime, end: datetime) -> list[Invoice]:
    issued = func.coalesce(Invoice.issued_at, Invoice.created_at)
    return (
        db.query(Invoice)
        .filter(issued >= start, issued < end, Invoice.voided_at.is_(None))
        .filter(or_(Invoice.status.is_(None), ~Invoice.status.in_(("void", "voided", "cancelled"))))
        .order_by(issued.asc())
        .all()
    )


def _rows_for(db: Session, inv: Invoice, default_prov: str) -> list[dict[str, Any]]:
    """One row per taxable line: pre-tax, tax, province, description."""
    from porterchain_api.platform.merchant_billing import charged_tax_split

    if (inv.billing_kind or "order") == "cycle":
        lines = db.query(InvoiceLine).filter(InvoiceLine.invoice_id == inv.id).order_by(InvoiceLine.created_at).all()
        if lines:
            return [
                {
                    "description": ln.description,
                    "pretax_cents": int(ln.amount_cents or 0),
                    "tax_cents": int(ln.tax_cents or 0),
                    "province": ln.tax_province or inv.tax_province or default_prov,
                }
                for ln in lines
            ]
    order = db.get(Order, inv.order_id) if inv.order_id else None
    province = inv.tax_province or (charged_tax_split(db, order, 0).province if order else default_prov)
    return [
        {
            "description": f"Delivery {order.order_number}" if order else "Delivery services",
            "pretax_cents": int(inv.amount_cents or 0) - int(inv.tax_cents or 0),
            "tax_cents": int(inv.tax_cents or 0),
            "province": province,
        }
    ]


def hst_report(db: Session, start: datetime, end: datetime) -> dict[str, Any]:
    from porterchain_pricing.tax.provinces import PROVINCES

    from porterchain_api.admin_engine.platform_settings import (
        collect_qst,
        default_tax_province,
        supplier_gst_hst_number,
    )

    qst = collect_qst(db)
    default_prov = default_tax_province(db)
    by_prov: dict[str, dict[str, int]] = defaultdict(lambda: {"pretax_cents": 0, "tax_cents": 0, "lines": 0})
    invoices = invoices_in_period(db, start, end)
    for inv in invoices:
        for row in _rows_for(db, inv, default_prov):
            b = by_prov[row["province"]]
            b["pretax_cents"] += row["pretax_cents"]
            b["tax_cents"] += row["tax_cents"]
            b["lines"] += 1
    provinces = []
    gst_hst = qst_total = 0
    for code, b in sorted(by_prov.items(), key=lambda kv: -kv[1]["pretax_cents"]):
        prov = PROVINCES.get(code) or PROVINCES["ON"]
        pct = prov.freight_percent(collect_qst=qst)
        qst_pct = next((c.percent for c in prov.freight_components(collect_qst=qst) if c.code == "QST"), 0.0)
        qst_part = int(round(b["tax_cents"] * qst_pct / pct)) if pct and qst_pct else 0
        gst_hst += b["tax_cents"] - qst_part
        qst_total += qst_part
        provinces.append(
            {
                "province": code,
                "name": prov.name,
                "label": prov.label(collect_qst=qst),
                "rate_pct": pct,
                "taxable_sales_cents": b["pretax_cents"],
                "tax_cents": b["tax_cents"],
                "gst_hst_cents": b["tax_cents"] - qst_part,
                "qst_cents": qst_part,
                "lines": b["lines"],
            }
        )
    sales = sum(p["taxable_sales_cents"] for p in provinces)
    return {
        "period_start": start,
        "period_end": end,
        "basis": "accrual (invoice issue date)",
        "registration_number": supplier_gst_hst_number(db),
        "invoice_count": len(invoices),
        "provinces": provinces,
        "gst34": {
            "line_101_sales_cents": sales,
            "line_103_tax_collected_cents": gst_hst,
            "line_106_itc_cents": 0,
            "line_109_net_tax_cents": gst_hst,
        },
        "qst_collected_cents": qst_total,
        "notes": [
            "Line 106 (ITCs) needs purchase receipts kept outside PCD — enter it in My Business Account.",
            "Exported from issued invoices; Stripe refunds and credit notes in the period are adjustments.",
        ],
    }


def hst_report_csv(report: dict[str, Any]) -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Province", "Tax", "Rate %", "Taxable sales", "GST/HST", "QST", "Lines"])
    for p in report["provinces"]:
        w.writerow(
            [p["province"], p["label"], p["rate_pct"], f"{p['taxable_sales_cents'] / 100:.2f}",
             f"{p['gst_hst_cents'] / 100:.2f}", f"{p['qst_cents'] / 100:.2f}", p["lines"]]
        )
    g = report["gst34"]
    w.writerow([])
    w.writerow(["GST34 line 101 (sales)", f"{g['line_101_sales_cents'] / 100:.2f}"])
    w.writerow(["GST34 line 103 (GST/HST collected)", f"{g['line_103_tax_collected_cents'] / 100:.2f}"])
    w.writerow(["GST34 line 106 (ITCs)", "enter from purchases"])
    w.writerow(["GST34 line 109 (net tax before ITCs)", f"{g['line_109_net_tax_cents'] / 100:.2f}"])
    return buf.getvalue()


def _customer_name(db: Session, inv: Invoice, cache: dict[str, str]) -> str:
    key = inv.merchant_id or inv.customer_id or ""
    if key in cache:
        return cache[key]
    name = "Customer"
    if inv.merchant_id and not inv.customer_id:
        from porterchain_api.platform.merchant_billing import merchant_display_name

        name = merchant_display_name(db, inv.merchant_id) or "Merchant"
    elif inv.customer_id:
        c = db.get(Customer, inv.customer_id)
        name = (getattr(c, "full_name", None) or getattr(c, "name", None) or getattr(c, "email", None) or "Customer") if c else "Customer"
    cache[key] = name
    return name


def _qbo_tax_code(prov: str, label: str) -> str:
    return f"{label.split(' ')[0]} {prov}"  # e.g. "HST ON", "GST AB" — map once in QuickBooks


def accounting_csv(db: Session, start: datetime, end: datetime, *, fmt: str) -> str:
    """Invoice lines in QuickBooks Online or Xero import format (one row per line)."""
    from porterchain_pricing.tax.provinces import PROVINCES

    from porterchain_api.admin_engine.platform_settings import collect_qst, default_tax_province

    qst = collect_qst(db)
    default_prov = default_tax_province(db)
    buf = io.StringIO()
    w = csv.writer(buf)
    if fmt == "xero":
        w.writerow(["*ContactName", "*InvoiceNumber", "Reference", "*InvoiceDate", "*DueDate", "*Description",
                    "*Quantity", "*UnitAmount", "*AccountCode", "*TaxType", "TaxAmount", "Currency"])
    else:
        w.writerow(["InvoiceNo", "Customer", "InvoiceDate", "DueDate", "Item(Product/Service)",
                    "ItemDescription", "ItemQuantity", "ItemRate", "ItemAmount", "ItemTaxCode", "ItemTaxAmount", "Currency"])
    cache: dict[str, str] = {}
    for inv in invoices_in_period(db, start, end):
        name = _customer_name(db, inv, cache)
        issued = (_issued(inv) or start).date().isoformat()
        due = (inv.due_at or _issued(inv) or start).date().isoformat()
        cur = (inv.currency or "cad").upper()
        for row in _rows_for(db, inv, default_prov):
            prov = PROVINCES.get(row["province"]) or PROVINCES["ON"]
            label = prov.label(collect_qst=qst)
            amt = f"{row['pretax_cents'] / 100:.2f}"
            tax = f"{row['tax_cents'] / 100:.2f}"
            if fmt == "xero":
                w.writerow([name, inv.invoice_number, inv.payment_reference or "", issued, due, row["description"],
                            "1", amt, "200", f"{label} ({row['province']})", tax, cur])
            else:
                w.writerow([inv.invoice_number, name, issued, due, "Delivery", row["description"], "1", amt, amt,
                            _qbo_tax_code(row["province"], label), tax, cur])
    return buf.getvalue()
