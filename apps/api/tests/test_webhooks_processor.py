"""Webhooks worker processor tests (§2.3.5)."""

from __future__ import annotations

from unittest.mock import patch

import pytest


@pytest.fixture
def webhooks_module():
    import sys
    from pathlib import Path

    worker_root = Path(__file__).resolve().parents[2] / "worker"
    if str(worker_root) not in sys.path:
        sys.path.insert(0, str(worker_root))
    from processors import webhooks

    return webhooks


def test_process_webhook_merchant_fanout(webhooks_module) -> None:
    payload = {
        "action": "merchant_fanout",
        "event_type": "order.delivered",
        "envelope": {"aggregate_type": "order", "aggregate_id": "ord_1"},
    }

    with patch(
        "porterchain_api.merchant_engine.webhook_delivery_service.deliver_merchant_fanout"
    ) as fanout:
        webhooks_module.process_webhook(payload)

    fanout.assert_called_once_with(payload)


def test_process_webhook_fleetbase_ingress_ack(webhooks_module, caplog) -> None:
    with patch(
        "porterchain_api.merchant_engine.webhook_delivery_service.deliver_merchant_fanout"
    ) as fanout:
        webhooks_module.process_webhook(
            {"source": "fleetbase", "update": {"porterchain_order_id": "ord_99"}}
        )

    fanout.assert_not_called()


def test_process_webhook_generic_payload(webhooks_module, caplog) -> None:
    with caplog.at_level("INFO"):
        webhooks_module.process_webhook({"source": "stripe", "type": "checkout.session.completed"})

    assert any("webhook processed" in record.message for record in caplog.records)
