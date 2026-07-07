"""Notification service — email, SMS, Firebase push (WhatsApp future)."""

import logging
from enum import StrEnum
from typing import Any

from porterchain_services.base import BaseService
from porterchain_shared.queue.names import QueueName

logger = logging.getLogger(__name__)


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
        """Enqueue notification — workers deliver asynchronously."""
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
        logger.info("notification enqueued: %s/%s -> %s", channel.value, template.value, recipient)

    def send_booking_confirmed(self, email: str, phone: str, tracking_number: str) -> None:
        ctx = {"tracking_number": tracking_number}
        self.send(NotificationChannel.EMAIL, NotificationTemplate.BOOKING_CONFIRMED, email, ctx)
        if phone:
            self.send(NotificationChannel.SMS, NotificationTemplate.BOOKING_CONFIRMED, phone, ctx)

    def send_checkout_recovery(self, email: str, quote_id: str, recovery_url: str) -> None:
        self.send(
            NotificationChannel.EMAIL,
            NotificationTemplate.CHECKOUT_RECOVERY,
            email,
            {"quote_id": quote_id, "recovery_url": recovery_url},
        )
