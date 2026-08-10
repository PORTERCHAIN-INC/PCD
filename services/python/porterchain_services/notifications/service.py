"""DEPRECATED — use apps/api notification_engine.

This legacy queue-only helper bypassed preferences, audit records, and
idempotency. New code must emit domain events or call
``porterchain_api.notification_engine``.
"""

from __future__ import annotations

import logging
import warnings
from enum import StrEnum
from typing import Any

from porterchain_services.base import BaseService
from porterchain_shared.queue.names import QueueName

logger = logging.getLogger(__name__)

_DEPRECATION = (
    "porterchain_services.notifications is retired; use "
    "porterchain_api.notification_engine (domain events → event_router)."
)


class NotificationChannel(StrEnum):
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    WHATSAPP = "whatsapp"


class NotificationTemplate(StrEnum):
    BOOKING_CONFIRMED = "booking_confirmed"
    PAYMENT_RECEIPT = "payment_receipt"
    DRIVER_ASSIGNED = "driver_assigned"
    DELIVERY_UPDATE = "delivery_update"
    CHECKOUT_RECOVERY = "checkout_recovery"
    MERCHANT_WELCOME = "merchant_welcome"
    INVOICE_READY = "invoice_ready"


class NotificationService(BaseService):
    service_name = "notifications"

    def send(
        self,
        channel: NotificationChannel,
        template: NotificationTemplate,
        recipient: str,
        context: dict[str, Any],
    ) -> None:
        warnings.warn(_DEPRECATION, DeprecationWarning, stacklevel=2)
        logger.warning(_DEPRECATION)
        queue_map = {
            NotificationChannel.EMAIL: QueueName.EMAILS,
            NotificationChannel.SMS: QueueName.SMS,
            NotificationChannel.PUSH: QueueName.PUSH,
            NotificationChannel.WHATSAPP: QueueName.SMS,
        }
        queue = queue_map[channel]
        self.ctx.queues.enqueue(
            queue,
            {
                "channel": channel.value,
                "template": template.value,
                "recipient": recipient,
                "context": context,
            },
        )
        logger.info("legacy notification enqueued: %s/%s -> %s", channel.value, template.value, recipient)

    def send_booking_confirmed(self, email: str, phone: str, tracking_number: str) -> None:
        warnings.warn(_DEPRECATION, DeprecationWarning, stacklevel=2)
        ctx = {"tracking_number": tracking_number}
        self.send(NotificationChannel.EMAIL, NotificationTemplate.BOOKING_CONFIRMED, email, ctx)
        if phone:
            self.send(NotificationChannel.SMS, NotificationTemplate.BOOKING_CONFIRMED, phone, ctx)

    def send_checkout_recovery(self, email: str, quote_id: str, recovery_url: str) -> None:
        warnings.warn(_DEPRECATION, DeprecationWarning, stacklevel=2)
        self.send(
            NotificationChannel.EMAIL,
            NotificationTemplate.CHECKOUT_RECOVERY,
            email,
            {"quote_id": quote_id, "recovery_url": recovery_url},
        )
