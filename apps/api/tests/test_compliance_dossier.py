"""Compliance PDF dossier tests (§8.1.13)."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

from porterchain_api.reporting.compliance_dossier import (
    build_compliance_dossier_pdf,
    build_dossier_sections,
    render_compliance_pdf,
)


def _order(**kwargs):
    defaults = dict(
        order_number="PC-1001",
        tracking_number="TRK-1001",
        state="delivered",
        merchant_id="m-1",
        scheduled_at=datetime(2026, 7, 9, 12, 0, tzinfo=UTC),
        pickup={"formatted": "100 King St W, Toronto"},
        dropoff={"formatted": "200 Bay St, Toronto"},
        special_instructions=None,
        assigned_driver_id=None,
        compliance_metadata={
            "vertical": "medical",
            "chain_of_custody": {
                "custodian_name": "Dr. Lee",
                "specimen_id": "SP-42",
                "seal_number": "SEAL-9",
            },
            "cold_chain": {"required": True, "min_c": 2.0, "max_c": 8.0, "readings": []},
        },
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def test_dossier_sections_include_chain_of_custody():
    order = _order()
    sections = build_dossier_sections(order, [])
    labels = [label for label, _ in sections]
    assert "Chain of custody" in labels
    chain = next(lines for label, lines in sections if label == "Chain of custody")
    assert any("Dr. Lee" in line for line in chain)


def test_render_compliance_pdf_magic_bytes():
    pdf = render_compliance_pdf([("Summary", ["Line one"])], footer="footer")
    assert pdf.startswith(b"%PDF-1.4")
    assert pdf.rstrip().endswith(b"%%EOF")


def test_build_compliance_dossier_pdf_for_order():
    order = _order()
    pdf = build_compliance_dossier_pdf(order, [])
    assert pdf.startswith(b"%PDF-1.4")
    assert len(pdf) > 400
