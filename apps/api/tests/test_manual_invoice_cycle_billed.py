"""Admin Generate invoice on a net-terms (cycle-billed) order must be a clear 400, not a 500."""
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from porterchain_api.booking_engine.invoice_service import InvoiceService


def test_cycle_billed_order_raises_value_error() -> None:
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = SimpleNamespace(id="o1", state="POD_COMPLETED")
    with patch("porterchain_api.admin_engine.merchant_ar_service.is_cycle_billed", return_value=True):
        with pytest.raises(ValueError, match="invoice_cycle_billed"):
            InvoiceService().manual_invoice(db, "o1")
