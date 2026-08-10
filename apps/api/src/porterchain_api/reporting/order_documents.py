"""Order label / manifest PDFs — commercial docs, not Fleetbase execution UI."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from porterchain_api.models import Order
from porterchain_api.reporting.compliance_dossier import render_compliance_pdf


def _addr_line(addr: dict[str, Any] | None) -> str:
    if not isinstance(addr, dict):
        return "—"
    parts = [
        addr.get("name") or addr.get("contact_name"),
        addr.get("street") or addr.get("address") or addr.get("line1"),
        addr.get("city"),
        addr.get("postal_code") or addr.get("zip"),
    ]
    return ", ".join(str(p) for p in parts if p) or "—"


def build_label_pdf(order: Order) -> bytes:
    """Shipping label sheet (tracking + stops) for warehouse print."""
    exported = datetime.now(UTC)
    sections: list[tuple[str, list[str]]] = [
        (
            "Shipping label",
            [
                f"Tracking: {order.tracking_number}",
                f"Order: {order.order_number}",
                f"State: {order.state}",
                f"Type: {order.order_type or '—'}",
                f"Source: {order.order_source or '—'}",
            ],
        ),
        ("Pickup", [_addr_line(order.pickup if isinstance(order.pickup, dict) else None)]),
        ("Delivery", [_addr_line(order.dropoff if isinstance(order.dropoff, dict) else None)]),
    ]
    if order.special_instructions:
        sections.append(("Instructions", [order.special_instructions[:240]]))
    if order.fleetbase_order_id:
        sections.append(("Fleetbase", [order.fleetbase_order_id, "Execution / POD live in Fleetbase"]))
    footer = f"{order.tracking_number} · label {exported.date().isoformat()}"
    return render_compliance_pdf(sections, title="PorterChain Shipping Label", footer=footer)


def build_invoice_pdf(
    order: Order,
    *,
    invoice_number: str,
    amount_cents: int,
    currency: str = "cad",
    receipt_number: str | None = None,
    merchant_name: str | None = None,
    customer_email: str | None = None,
) -> bytes:
    """Commercial invoice sheet when Stripe PDF is absent."""
    exported = datetime.now(UTC)
    amount = f"${(amount_cents or 0) / 100:.2f} {(currency or 'cad').upper()}"
    sections: list[tuple[str, list[str]]] = [
        (
            "Invoice",
            [
                f"Invoice: {invoice_number}",
                f"Receipt: {receipt_number or '—'}",
                f"Amount: {amount}",
                f"Order: {order.order_number}",
                f"Tracking: {order.tracking_number}",
                f"State: {order.state}",
            ],
        ),
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
    footer = f"{invoice_number} · {exported.date().isoformat()} · Moving commerce on chain"
    return render_compliance_pdf(sections, title="PorterChain Invoice", footer=footer)


def build_manifest_pdf(order: Order, *, driver_name: str | None = None) -> bytes:
    """Single-order dispatch manifest for handoff / dock print."""
    exported = datetime.now(UTC)
    sections: list[tuple[str, list[str]]] = [
        (
            "Dispatch manifest",
            [
                f"Tracking: {order.tracking_number}",
                f"Order: {order.order_number}",
                f"State: {order.state}",
                f"Amount: ${(order.amount_cents or 0) / 100:.2f} {(order.currency or 'cad').upper()}",
                f"Driver: {driver_name or 'Unassigned'}",
                f"Scheduled: {order.scheduled_at.isoformat() if order.scheduled_at else '—'}",
            ],
        ),
        ("Pickup", [_addr_line(order.pickup if isinstance(order.pickup, dict) else None)]),
        ("Delivery", [_addr_line(order.dropoff if isinstance(order.dropoff, dict) else None)]),
    ]
    compliance = order.compliance_metadata if isinstance(order.compliance_metadata, dict) else {}
    stops = compliance.get("stops") or compliance.get("additional_stops") or []
    if isinstance(stops, list) and stops:
        lines = []
        for i, stop in enumerate(stops[:12], start=1):
            if isinstance(stop, dict):
                lines.append(f"{i}. {_addr_line(stop)}")
            else:
                lines.append(f"{i}. {stop}")
        sections.append(("Stops", lines))
    footer = f"{order.tracking_number} · manifest {exported.date().isoformat()}"
    return render_compliance_pdf(sections, title="PorterChain Order Manifest", footer=footer)
