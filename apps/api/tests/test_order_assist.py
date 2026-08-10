"""Order 360 assist + playbook contract tests (propose-confirm)."""

from porterchain_api.admin_engine.order_assist_service import OrderAssistService, _pid
from porterchain_api.reporting.order_documents import build_invoice_pdf


def test_proposal_id_stable():
    assert _pid("assign", "o1", "d1") == _pid("assign", "o1", "d1")
    assert _pid("a", "1") != _pid("a", "2")


def test_invoice_pdf_bytes():
    class _O:
        tracking_number = "PC-TEST"
        order_number = "ORD-1"
        state = "INVOICED"
        pickup = {"city": "Toronto"}
        dropoff = {"city": "Mississauga"}

    pdf = build_invoice_pdf(
        _O(),  # type: ignore[arg-type]
        invoice_number="INV-1",
        amount_cents=4200,
        currency="cad",
        receipt_number="RCPT-1",
    )
    assert pdf.startswith(b"%PDF")


def test_assist_missing_order():
    from porterchain_api.config import get_settings
    from porterchain_api.db import SessionLocal
    from porterchain_api.merchant_models import Merchant  # noqa: F401
    from porterchain_api.user_models import PorterchainUser  # noqa: F401

    db = SessionLocal()
    try:
        try:
            OrderAssistService().assist(db, get_settings(), "missing-order-id")
            raise AssertionError("expected LookupError")
        except LookupError as exc:
            assert "order_not_found" in str(exc)
    finally:
        db.close()
