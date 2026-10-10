"""Merchant account ops sweep: auto credit holds + churn / hold emails to staff.

Orchestration only: merchant_engine decides (holds, dedupe, content) and
notification_engine delivers by email. Off with MERCHANT_OPS_SWEEP_ENABLED=false.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any

logger = logging.getLogger(__name__)

SWEEP_INTERVAL_SECONDS = 900
_last_sweep_at = 0.0


def send_email(template: str, recipient: str, context: dict[str, Any]) -> bool:
    from porterchain_api.notification_engine.delivery_service import DeliveryService

    try:
        log = DeliveryService().deliver(
            {"channel": "email", "template": template, "recipient": recipient, "context": context}
        )
        return getattr(log, "status", None) == "sent"
    except Exception:  # noqa: BLE001 — a mail blip must not stop the sweep
        logger.exception("merchant_ops_alert_failed template=%s", template)
        return False


def drain_if_due() -> int:
    global _last_sweep_at
    if os.environ.get("MERCHANT_OPS_SWEEP_ENABLED", "true").strip().lower() in ("0", "false", "no", "off"):
        return 0
    now = time.monotonic()
    if now - _last_sweep_at < SWEEP_INTERVAL_SECONDS:
        return 0
    _last_sweep_at = now

    from porterchain_api.config import get_settings
    from porterchain_api.db import SessionLocal
    from porterchain_api.merchant_engine.account_ops.alerts import sweep

    with SessionLocal() as db:
        out = sweep(db, get_settings(), sender=send_email)
    if any(out.values()):
        logger.info("merchant ops sweep: %s", out)
    return int(out["churn_emails"] + out["hold_emails"])
