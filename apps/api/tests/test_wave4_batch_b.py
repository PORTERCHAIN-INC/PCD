"""Wave 4 Batch B: onboarding gate, invoice total, claims by customer."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from porterchain_api.billing_engine.merchant_service import invoice_total_cents
from porterchain_api.support_engine.claims_constants import ClaimFilters
from porterchain_api.support_engine.claims_query import ClaimsQueryMixin


def test_invoice_total_includes_fees() -> None:
    inv = SimpleNamespace(amount_cents=1000, tax_cents=130, fees_cents=50)
    assert invoice_total_cents(inv) == 1050  # amount already includes tax; fees additive


def test_invoice_total_zero_safe() -> None:
    inv = SimpleNamespace(amount_cents=None, tax_cents=None, fees_cents=None)
    assert invoice_total_cents(inv) == 0


class _Claims(ClaimsQueryMixin):
    def _row(self, db, claim):
        return {
            "id": claim.id,
            "priority": "normal",
            "assigned_investigator_id": None,
            "merchant_id": None,
            "driver_id": None,
            "customer_id": "cust-1",
            "has_insurance": False,
            "amount_cents": 100,
            "risk_score": 10,
        }


def test_claims_customer_filter_empty_orders() -> None:
    svc = _Claims()
    db = MagicMock()
    # Order.id query returns empty
    q = MagicMock()
    q.filter.return_value.limit.return_value.all.return_value = []
    db.query.return_value = q

    out = svc.list_enriched(db, ClaimFilters(customer_id="cust-missing"))
    assert out == []

