"""Notifications worker processor tests (§2.3.4)."""

from __future__ import annotations

from unittest.mock import patch

import pytest


@pytest.fixture
def notifications_module():
    import sys
    from pathlib import Path

    worker_root = Path(__file__).resolve().parents[2] / "worker"
    if str(worker_root) not in sys.path:
        sys.path.insert(0, str(worker_root))
    from processors import notifications

    return notifications


def test_process_notification_delegates_to_delivery_service(notifications_module) -> None:
    payload = {
        "channel": "email",
        "template": "delivery_update",
        "recipient": "ops@porterchain.com",
        "notification_id": "ntf_1",
    }

    with patch(
        "porterchain_api.notification_engine.delivery_service.DeliveryService"
    ) as svc_cls:
        notifications_module.process_notification(payload)

    svc_cls.return_value.deliver.assert_called_once_with(payload)


def test_process_notification_injects_push_channel(notifications_module) -> None:
    payload = {"notification_id": "ntf_push", "template": "driver_job", "recipient_id": "drv_1"}

    with patch(
        "porterchain_api.notification_engine.delivery_service.DeliveryService"
    ) as svc_cls:
        notifications_module.process_notification({**payload, "channel": "push"})

    call_payload = svc_cls.return_value.deliver.call_args[0][0]
    assert call_payload["channel"] == "push"


def test_queue_router_injects_email_channel() -> None:
    import sys
    from pathlib import Path

    from porterchain_shared.queue.names import QueueName
    from porterchain_shared.queue.publisher import QueueMessage

    worker_root = Path(__file__).resolve().parents[2] / "worker"
    if str(worker_root) not in sys.path:
        sys.path.insert(0, str(worker_root))
    from processors import process_queue_message

    payload = {"notification_id": "ntf_email", "template": "booking_confirmed"}
    msg = QueueMessage(queue=QueueName.EMAILS, message_id="m1", payload=payload)

    with patch("processors.process_notification") as process_notification:
        process_queue_message(msg)

    process_notification.assert_called_once_with({**payload, "channel": "email"})
