"""Order print-preview / pickup-list PDFs — commercial dock sheets, not carrier labels.

Fleetbase has no merchant label API. Do not title these “shipping label”.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Sequence

from porterchain_api.domain.catalog_labels import order_state_label
from porterchain_api.merchant_engine.toronto import format_datetime_toronto
from porterchain_api.booking_models import Order
from porterchain_api.reporting.compliance_dossier import render_compliance_pdf

_PREVIEW_NOTE = "Print preview for your dock — not a carrier shipping label."


def _addr_line(addr: dict[str, Any] | None) -> str:
    if not isinstance(addr, dict):
        return "—"
    parts = [
        addr.get("name") or addr.get("contact_name"),
        addr.get("formatted") or addr.get("street") or addr.get("address") or addr.get("line1"),
        addr.get("city"),
        addr.get("postal_code") or addr.get("postal") or addr.get("zip"),
    ]
    return ", ".join(str(p) for p in parts if p) or "—"


def _ref_lines(order: Order) -> list[str]:
    lines: list[str] = []
    if getattr(order, "purchase_order_number", None):
        lines.append(f"PO: {order.purchase_order_number}")
    if getattr(order, "internal_reference", None):
        lines.append(f"Your reference: {order.internal_reference}")
    if getattr(order, "cost_centre", None):
        lines.append(f"Cost centre: {order.cost_centre}")
    return lines


def _order_sheet_lines(order: Order) -> list[str]:
    amount = f"${(order.amount_cents or 0) / 100:.2f} {(order.currency or 'cad').upper()}"
    return [
        f"Tracking: {order.tracking_number}",
        f"Order: {order.order_number}",
        f"Status: {order_state_label(order.state)}",
        f"Scheduled: {format_datetime_toronto(order.scheduled_at)}",
        f"Amount: {amount}",
        *_ref_lines(order),
    ]


def build_print_preview_pdf(order: Order) -> bytes:
    """One order per sheet — tracking, stops, references."""
    exported = datetime.now(UTC)
    sections: list[tuple[str, list[str]]] = [
        ("Print preview", [*_order_sheet_lines(order), _PREVIEW_NOTE]),
        ("Pickup", [_addr_line(order.pickup if isinstance(order.pickup, dict) else None)]),
        ("Delivery", [_addr_line(order.dropoff if isinstance(order.dropoff, dict) else None)]),
    ]
    if order.special_instructions:
        sections.append(("Instructions", [order.special_instructions[:240]]))
    footer = f"{order.tracking_number} · print preview {format_datetime_toronto(exported)}"
    return render_compliance_pdf(sections, title="Print preview", footer=footer)


def build_label_pdf(order: Order) -> bytes:
    """Retired dishonest alias — use LabelService / labels.pdf."""
    raise RuntimeError("use LabelService — GET /orders/{id}/labels.pdf")


def build_invoice_pdf(
    order: Order,
    *,
    invoice_number: str,
    amount_cents: int,
    currency: str = "cad",
    receipt_number: str | None = None,
    merchant_name: str | None = None,
    customer_email: str | None = None,
    tax_cents: int = 0,
    fees_cents: int = 0,
    outstanding_cents: int | None = None,
    lines: Sequence[dict[str, Any]] | None = None,
) -> bytes:
    """Commercial invoice sheet when Stripe PDF is absent.

    Amounts must match GET /billing/invoices/{id} (amount_cents / tax / fees / outstanding).
    """
    exported = datetime.now(UTC)
    cur = (currency or "cad").upper()
    amount = f"${(amount_cents or 0) / 100:.2f} {cur}"
    tax = f"${(tax_cents or 0) / 100:.2f} {cur}"
    fees = f"${(fees_cents or 0) / 100:.2f} {cur}"
    due = (
        f"${(outstanding_cents if outstanding_cents is not None else amount_cents) / 100:.2f} {cur}"
    )
    invoice_lines = [
        f"Invoice: {invoice_number}",
        f"Receipt: {receipt_number or '—'}",
        f"Amount: {amount}",
        f"Tax: {tax}",
        f"Fees: {fees}",
        f"Outstanding: {due}",
        f"Order: {order.order_number}",
        f"Tracking: {order.tracking_number}",
        f"Status: {order_state_label(order.state)}",
    ]
    sections: list[tuple[str, list[str]]] = [
        ("Invoice", invoice_lines),
        (
            "Bill to",
            [
                f"Merchant: {merchant_name or '—'}",
                f"Customer: {customer_email or '—'}",
            ],
        ),
        ("Pickup", [_addr_line(order.pickup if isinstance(order.pickup, dict) else None)]),
        ("Delivery", [_addr_line(order.dropoff if isinstance(order.dropoff, dict) else None)]),
    ]
    if lines:
        line_text: list[str] = []
        for ln in lines[:40]:
            desc = str(ln.get("description") or "Delivery")
            cents = int(ln.get("amount_cents") or 0)
            channel = ln.get("channel") or "—"
            model = ln.get("pricing_model") or "—"
            line_text.append(
                f"{desc} · {channel}/{model} · ${cents / 100:.2f} {cur}"
            )
        sections.append(("Lines", line_text))
    footer = f"{invoice_number} · {format_datetime_toronto(exported)}"
    return render_compliance_pdf(sections, title="PorterChain Invoice", footer=footer)


def build_pickup_list_pdf(
    orders: Sequence[Order],
    *,
    merchant_name: str | None = None,
    driver_name: str | None = None,
) -> bytes:
    """Dock list for one or more orders — not a Fleetbase vehicle manifest."""
    exported = datetime.now(UTC)
    header = [
        f"Company: {merchant_name or '—'}",
        f"Orders: {len(orders)}",
        f"Printed: {format_datetime_toronto(exported)}",
        _PREVIEW_NOTE,
    ]
    if driver_name:
        header.insert(2, f"Driver: {driver_name}")
    sections: list[tuple[str, list[str]]] = [("Pickup list", header)]
    for index, order in enumerate(orders, start=1):
        lines = [
            *_order_sheet_lines(order),
            f"Pickup: {_addr_line(order.pickup if isinstance(order.pickup, dict) else None)}",
            f"Delivery: {_addr_line(order.dropoff if isinstance(order.dropoff, dict) else None)}",
        ]
        compliance = order.compliance_metadata if isinstance(order.compliance_metadata, dict) else {}
        stops = compliance.get("stops") or compliance.get("additional_stops") or []
        if isinstance(stops, list) and stops:
            for i, stop in enumerate(stops[:8], start=1):
                if isinstance(stop, dict):
                    lines.append(f"Stop {i}: {_addr_line(stop)}")
                else:
                    lines.append(f"Stop {i}: {stop}")
        sections.append((f"{index}. {order.tracking_number}", lines))
    footer = f"Pickup list · {len(orders)} order(s) · {format_datetime_toronto(exported)}"
    return render_compliance_pdf(sections, title="Pickup list", footer=footer)


def build_manifest_pdf(order: Order, *, driver_name: str | None = None) -> bytes:
    """Admin alias — same pickup list for one order."""
    return build_pickup_list_pdf([order], driver_name=driver_name)
