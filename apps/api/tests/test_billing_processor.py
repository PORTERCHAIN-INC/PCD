"""Billing worker processor tests (§2.3.3)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def billing_module():
    import sys
    from pathlib import Path

    worker_root = Path(__file__).resolve().parents[2] / "worker"
    if str(worker_root) not in sys.path:
        sys.path.insert(0, str(worker_root))
    from processors import billing

    return billing


def test_process_billing_delegates_to_settlement_service(billing_module) -> None:
    payload = {"action": "payment_succeeded", "data": {"id": "cs_test"}}

    with patch(
        "porterchain_api.billing_engine.settlement_service.SettlementService"
    ) as svc_cls:
        billing_module.process_billing(payload)

    svc_cls.return_value.process_queue_job.assert_called_once_with(payload)


def test_process_billing_payment_settled_records_ledger(billing_module) -> None:
    mock_payment = MagicMock(
        id="pay_1",
        order_id="ord_1",
        amount_cents=4200,
        currency="cad",
    )
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = mock_payment

    with patch("porterchain_api.billing_engine.settlement_service.SessionLocal", return_value=mock_db):
        billing_module.process_billing(
            {"action": "payment_settled", "aggregate_id": "pay_1", "payload": {"source": "test"}}
        )

    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()
    entry = mock_db.add.call_args[0][0]
    assert entry.kind == "payment_settled"
    assert entry.payment_id == "pay_1"
    assert entry.order_id == "ord_1"


def test_process_billing_unknown_action_still_records_ledger(billing_module) -> None:
    mock_db = MagicMock()

    with patch("porterchain_api.billing_engine.settlement_service.SessionLocal", return_value=mock_db):
        billing_module.process_billing({"action": "noop"})

    mock_db.add.assert_called_once()
    entry = mock_db.add.call_args[0][0]
    assert entry.kind == "noop"
    assert entry.status == "ignored"
    mock_db.close.assert_called_once()
