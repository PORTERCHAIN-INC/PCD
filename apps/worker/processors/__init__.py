"""Queue consumer — routes worker jobs to processors."""

from __future__ import annotations

import logging

from porterchain_shared.queue.names import QueueName
from porterchain_shared.queue.publisher import QueueMessage

from processors.billing import process_billing
from processors.dispatch import process_dispatch
from processors.notifications import process_notification
from processors.webhooks import process_webhook

logger = logging.getLogger(__name__)


def process_queue_message(msg: QueueMessage) -> None:
    queue = msg.queue
    payload = msg.payload
    logger.debug("processing %s message %s", queue.value, msg.message_id)

    if queue == QueueName.EMAILS:
        process_notification({**payload, "channel": "email"})
    elif queue == QueueName.SMS:
        process_notification({**payload, "channel": "sms"})
    elif queue == QueueName.PUSH:
        process_notification({**payload, "channel": "push"})
    elif queue == QueueName.BILLING:
        process_billing(payload)
    elif queue == QueueName.WEBHOOKS:
        process_webhook(payload)
    elif queue == QueueName.DISPATCH:
        process_dispatch(payload)
    elif queue == QueueName.REPORTS:
        logger.info("reports job received: %s", msg.message_id)
    else:
        logger.warning("no processor for queue %s", queue.value)
