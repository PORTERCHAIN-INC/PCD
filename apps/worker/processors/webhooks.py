"""Webhook fan-out queue — merchant callbacks and ingress retries."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def process_webhook(payload: dict[str, Any]) -> None:
    source = payload.get("source")
    action = payload.get("action")
    if action == "merchant_fanout":
        from porterchain_api.merchant_engine.webhook_delivery_service import deliver_merchant_fanout

        deliver_merchant_fanout(payload)
        return
    if source == "fleetbase":
        logger.info("webhook ingress ack: fleetbase order=%s", payload.get("update", {}).get("porterchain_order_id"))
        return
    logger.info("webhook processed: keys=%s", list(payload.keys()))
