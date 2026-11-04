"""L145: a payout hold does not show as negative earnings or as withheld tax."""
from datetime import UTC, datetime
from types import SimpleNamespace

from porterchain_api.billing_engine.driver_finance_service import DriverFinanceService


def _tx(kind, cents):
    return SimpleNamespace(tx_type=kind, amount_cents=cents, created_at=datetime.now(UTC), id=kind, description=kind,
                           reference_id=None, balance_after_cents=0)


def test_payout_excluded_from_net_and_deductions(db):
    s = DriverFinanceService()
    txs = [_tx("delivery", 850), _tx("payout", -850)]
    start = datetime(2000, 1, 1, tzinfo=UTC)
    assert s._net_earnings(txs, start, datetime.now(UTC)) == 850
    assert s._filter_deductions(txs, limit=10) == []
