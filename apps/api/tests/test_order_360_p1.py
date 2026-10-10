"""Order 360 P1 helpers — document URL hygiene, POD normalize, label PDF."""

from porterchain_api.booking_engine.invoice_service import public_document_url
from porterchain_api.reporting.order_documents import (
    build_label_pdf,
    build_manifest_pdf,
)
from porterchain_api.reporting.pod_normalize import normalize_pod


def test_public_document_url_blocks_placeholders():
    assert public_document_url(None) is None
    assert public_document_url("https://example.local/receipt/x") is None
    assert public_document_url("https://example.com/invoice.pdf") is None
    assert public_document_url("not-a-url") is None
    assert (
        public_document_url("https://pay.stripe.com/receipts/abc")
        == "https://pay.stripe.com/receipts/abc"
    )


def test_normalize_pod_gallery_shape():
    pod = normalize_pod(
        [
            {"type": "photo", "url": "https://cdn.example.org/a.jpg", "id": "1"},
            {"type": "signature", "url": "https://cdn.example.org/s.png", "id": "2"},
            {"type": "otp", "otp": "1234"},
        ]
    )
    assert pod["complete"] is True
    assert len(pod["photos"]) == 1
    assert len(pod["signatures"]) == 1
    assert pod["otp"][0]["otp"] == "1234"
    assert pod["source"] == "porterchain"


def test_label_and_manifest_pdf_bytes():
    """Legacy build_label_pdf is retired — LabelService owns 4×6 labels."""
    import pytest

    from porterchain_api.reporting.label_service import LabelService

    class _O:
        id = "ord-1"
        tracking_number = "PC-TEST-1"
        order_number = "ORD-1"
        state = "DRIVER_ASSIGNED"
        order_type = "instant"
        order_source = "admin"
        pickup = {"street": "1 King St", "city": "Toronto"}
        dropoff = {"street": "2 Queen St", "city": "Toronto"}
        special_instructions = "Ring bell"
        fleetbase_order_id = "order_abc"
        amount_cents = 2500
        currency = "cad"
        scheduled_at = None
        assigned_driver_id = None
        compliance_metadata = None

    with pytest.raises(RuntimeError, match="LabelService"):
        build_label_pdf(_O())  # type: ignore[arg-type]
    manifest = build_manifest_pdf(_O(), driver_name="Ada")  # type: ignore[arg-type]
    assert manifest.startswith(b"%PDF")
    assert b"Pickup list" in manifest
    # LabelService requires packages — empty package list is an explicit contract.
    with pytest.raises(Exception):
        LabelService().build_order_labels_pdf(_O(), packages=[])  # type: ignore[arg-type]
