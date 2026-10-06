"""Enqueue routing jobs onto QueueName.ROUTING (not emails/dispatch)."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def enqueue_routing_job(payload: dict[str, Any]) -> None:
    from porterchain_shared.queue.names import QueueName
    from porterchain_shared.queue.publisher import get_queue_publisher

    get_queue_publisher().enqueue(QueueName.ROUTING, payload)
