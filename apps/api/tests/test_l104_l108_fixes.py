"""L104-L108: invoice from DELIVERED, admin return booking, Toronto dates, single invoice email."""
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from porterchain_api.admin_engine.merchant_ar_service import MerchantArService, _toronto_wall_to_utc
from porterchain_api.booking_engine import numbers
from porterchain_api.booking_engine.invoice_service import InvoiceService
from porterchain_api.notification_engine.event_router import _specs_for_event


def test_l104_delivered_order_moves_to_pod_then_invoices() -> None:
    db = MagicMock()
    order = SimpleNamespace(id="o1", state="DELIVERED")
    db.query.return_value.filter.return_value.first.return_value = order
    inv = SimpleNamespace(id="i1")
    with patch("porterchain_api.admin_engine.merchant_ar_service.is_cycle_billed", return_value=False), patch(
        "porterchain_api.booking_engine.invoice_service.transition_order_state"
    ) as tr, patch.object(InvoiceService, "finalize_after_pod", return_value=inv):
        assert InvoiceService().manual_invoice(db, "o1") is inv
    assert tr.call_args.kwargs["event_type"] == "order.pod_completed"


def test_l104_undelivered_order_gives_readable_error() -> None:
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = SimpleNamespace(id="o1", state="IN_TRANSIT")
    with pytest.raises(ValueError, match="invoice_requires_delivery: this order is in transit"):
        InvoiceService().manual_invoice(db, "o1")


def test_l105_admin_return_rejects_undelivered() -> None:
    from porterchain_api.admin_engine.orders_service import AdminOrdersService

    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = SimpleNamespace(
        id="o1", state="IN_TRANSIT", merchant_id="m1", metadata_json={}, meta={}
    )
    db.get.return_value = SimpleNamespace(id="m1")
    with patch("porterchain_api.merchant_engine.return_service.is_return", return_value=False):
        with pytest.raises(ValueError, match="return_not_delivered"):
            AdminOrdersService().create_return_committed(db, MagicMock(), "o1")


def test_l106_numbers_use_toronto_day() -> None:
    late = datetime(2026, 10, 31, 2, 30, tzinfo=UTC)  # 10:30 PM Oct 30 in Toronto

    class FakeDT(datetime):
        @classmethod
        def now(cls, tz=None):
            return late.astimezone(tz)

    with patch.object(numbers, "datetime", FakeDT):
        assert "20261030" in numbers.generate_order_number()
        assert "20261030" in numbers.generate_tracking_number()


def test_l107_period_reads_toronto_wall_time() -> None:
    assert _toronto_wall_to_utc(datetime(2026, 10, 30, 23, 30, tzinfo=UTC)) == datetime(2026, 10, 31, 3, 30)
    start, end = MerchantArService()._resolve_period(
        SimpleNamespace(billing_cycle="MONTHLY"),
        datetime(2026, 10, 1, tzinfo=UTC),
        datetime(2026, 10, 30, 23, 30, tzinfo=UTC),
    )
    # L137: a 23:30 period end means through that day -> Toronto midnight (04:00 UTC in EDT).
    assert start == datetime(2026, 10, 1, 4, 0) and end == datetime(2026, 10, 31, 4, 0)


def test_l108_cycle_order_invoiced_sends_no_merchant_email() -> None:
    specs = _specs_for_event(
        "order.invoiced",
        {"merchant_ar_cycle": True, "merchant_email": "m@example.test", "invoice_number": "INV-1"},
    )
    assert not [s for s in specs if "invoice" in str(s.get("template", ""))]

