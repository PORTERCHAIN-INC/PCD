"""Compliance PDF dossier for vertical audit packages (§8.1.13)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Sequence

from porterchain_api.admin_models import Driver
from porterchain_api.merchant_models import Merchant
from porterchain_api.models import Order


def _pdf_escape(text: str) -> str:
    safe = text.encode("latin-1", errors="replace").decode("latin-1")
    return safe.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _wrap_lines(prefix: str, value: Any) -> list[str]:
    if value is None or value == "":
        return []
    if isinstance(value, bool):
        return [f"{prefix}: {'yes' if value else 'no'}"]
    if isinstance(value, (dict, list)):
        import json

        compact = json.dumps(value, default=str, separators=(",", ":"))
        if len(compact) > 120:
            compact = compact[:117] + "..."
        return [f"{prefix}: {compact}"]
    return [f"{prefix}: {value}"]


def build_dossier_sections(
    order: Order,
    events: Sequence[Any],
    *,
    merchant: Merchant | None = None,
    driver: Driver | None = None,
    exported_at: datetime | None = None,
) -> list[tuple[str, list[str]]]:
    """Structured sections for compliance review — mirrors §8.1.4 audit export."""
    exported_at = exported_at or datetime.now(UTC)
    meta = order.compliance_metadata if isinstance(order.compliance_metadata, dict) else {}

    sections: list[tuple[str, list[str]]] = [
        (
            "Summary",
            [
                f"Exported at: {exported_at.isoformat()}",
                f"Order number: {order.order_number}",
                f"Tracking number: {order.tracking_number}",
                f"State: {order.state}",
                f"Vertical: {meta.get('vertical') or 'general'}",
                f"Scheduled at: {order.scheduled_at.isoformat() if order.scheduled_at else 'n/a'}",
            ],
        ),
    ]

    if merchant:
        sections.append(
            (
                "Merchant",
                [
                    f"Company: {merchant.company_name}",
                    f"Merchant ID: {merchant.id}",
                    f"Payment terms: {merchant.payment_terms}",
                ],
            )
        )

    pickup = order.pickup if isinstance(order.pickup, dict) else {}
    dropoff = order.dropoff if isinstance(order.dropoff, dict) else {}
    sections.append(
        (
            "Route",
            [
                f"Pickup: {pickup.get('formatted', 'n/a')}",
                f"Dropoff: {dropoff.get('formatted', 'n/a')}",
                f"Special instructions: {order.special_instructions or 'n/a'}",
            ],
        )
    )

    chain = meta.get("chain_of_custody") or {}
    if chain:
        sections.append(
            (
                "Chain of custody",
                [
                    *_wrap_lines("Custodian", chain.get("custodian_name")),
                    *_wrap_lines("Specimen ID", chain.get("specimen_id")),
                    *_wrap_lines("Seal number", chain.get("seal_number")),
                ],
            )
        )

    cold = meta.get("cold_chain") or {}
    if cold:
        cold_lines = [
            *_wrap_lines("Required", cold.get("required")),
            *_wrap_lines("Min °C", cold.get("min_c")),
            *_wrap_lines("Max °C", cold.get("max_c")),
        ]
        readings = cold.get("readings") or []
        for idx, reading in enumerate(readings[:20], start=1):
            cold_lines.append(
                f"Reading {idx}: {reading.get('c')}°C at {reading.get('at', 'n/a')}"
            )
        sections.append(("Cold chain", cold_lines))

    window = meta.get("delivery_window") or {}
    if window:
        sections.append(
            (
                "Delivery window",
                [
                    *_wrap_lines("Start", window.get("start")),
                    *_wrap_lines("End", window.get("end")),
                ],
            )
        )

    if driver:
        sections.append(
            (
                "Assigned driver",
                [
                    f"Name: {driver.first_name} {driver.last_name}".strip(),
                    f"Driver ID: {driver.id}",
                    f"Medical transport certified: {'yes' if driver.medical_transport_certified else 'no'}",
                ],
            )
        )

    timeline_lines: list[str] = []
    for event in events[:50]:
        occurred = getattr(event, "occurred_at", None)
        stamp = occurred.isoformat() if occurred else "n/a"
        event_type = getattr(event, "event_type", "event")
        from_state = getattr(event, "from_state", None)
        to_state = getattr(event, "to_state", None)
        transition = f" ({from_state} → {to_state})" if from_state or to_state else ""
        timeline_lines.append(f"{stamp} — {event_type}{transition}")
    if timeline_lines:
        sections.append(("Audit timeline", timeline_lines))

    return sections


def render_compliance_pdf(
    sections: list[tuple[str, list[str]]],
    *,
    title: str = "Porterchain Compliance Dossier",
    footer: str | None = None,
) -> bytes:
    """Minimal PDF 1.4 (stdlib only) — single-page text dossier."""
    content_ops: list[str] = []
    y = 800

    content_ops.append(f"BT /F1 16 Tf 50 {y} Td ({_pdf_escape(title)}) Tj ET")
    y -= 26

    for heading, lines in sections:
        if y < 70:
            break
        content_ops.append(f"BT /F1 12 Tf 50 {y} Td ({_pdf_escape(heading)}) Tj ET")
        y -= 18
        for line in lines:
            if y < 55:
                break
            content_ops.append(f"BT /F1 10 Tf 60 {y} Td ({_pdf_escape(line)}) Tj ET")
            y -= 13

    if footer:
        content_ops.append(f"BT /F1 8 Tf 50 36 Td ({_pdf_escape(footer)}) Tj ET")

    stream = "\n".join(content_ops)
    stream_bytes = stream.encode("latin-1")

    objects: list[bytes] = []
    objects.append(b"1 0 obj<< /Type /Catalog /Pages 2 0 R >>endobj\n")
    objects.append(b"2 0 obj<< /Type /Pages /Kids [3 0 R] /Count 1 >>endobj\n")
    objects.append(
        b"3 0 obj<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 842] "
        b"/Contents 4 0 R /Resources<< /Font<< /F1 5 0 R >> >> >>endobj\n"
    )
    objects.append(
        f"4 0 obj<< /Length {len(stream_bytes)} >>stream\n".encode("ascii")
        + stream_bytes
        + b"\nendstream\nendobj\n"
    )
    objects.append(b"5 0 obj<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>endobj\n")

    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for obj in objects:
        offsets.append(len(pdf))
        pdf.extend(obj)

    xref_start = len(pdf)
    pdf.extend(f"xref\n0 {len(offsets)}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    pdf.extend(
        f"trailer<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref_start}\n%%EOF\n".encode(
            "ascii"
        )
    )
    return bytes(pdf)


def build_compliance_dossier_pdf(
    order: Order,
    events: Sequence[Any],
    *,
    merchant: Merchant | None = None,
    driver: Driver | None = None,
) -> bytes:
    exported_at = datetime.now(UTC)
    sections = build_dossier_sections(
        order,
        events,
        merchant=merchant,
        driver=driver,
        exported_at=exported_at,
    )
    footer = f"Order {order.order_number} · exported {exported_at.date().isoformat()}"
    return render_compliance_pdf(sections, footer=footer)
