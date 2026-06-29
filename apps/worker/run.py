#!/usr/bin/env python3
"""Porterchain async worker — consumes event bus + task queues."""

import logging
import signal
import sys
import time

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("porterchain.worker")

_running = True


def _shutdown(_signum, _frame) -> None:
    global _running
    _running = False
    logger.info("shutdown signal received")


def main() -> None:
    from porterchain_event_bus import get_event_bus
    from porterchain_event_bus.handlers import register_default_handlers
    from porterchain_shared.queue.names import QueueName
    from porterchain_shared.queue.publisher import InMemoryQueuePublisher, get_queue_publisher

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    register_default_handlers()
    bus = get_event_bus()
    publisher = get_queue_publisher()
    logger.info("worker started — event bus + queues: %s", ", ".join(q.value for q in QueueName))

    while _running:
        processed = bus.consume_once(consumer_name="porterchain-worker", block_ms=1000)
        if isinstance(publisher, InMemoryQueuePublisher):
            for queue in QueueName:
                msg = publisher.dequeue(queue)
                if msg:
                    logger.info("processed %s message %s", queue.value, msg.message_id)
                    processed += 1
        if processed == 0:
            time.sleep(0.5)

    logger.info("worker stopped")
    sys.exit(0)


if __name__ == "__main__":
    main()
