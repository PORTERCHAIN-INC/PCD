"""Ops Today live stream — tiny messages on one Redis channel, fanned out by the API WS hub.

Producers stay sync and cheap (one PUBLISH, errors swallowed). The wire format matches
``RealtimeHub`` so any API instance subscribed to ``CHANNEL`` delivers it to its sockets.

Message kinds (``payload["type"]``):
  driver     {id, lat, lng, heading, at}          — accepted GPS fix (consent is enforced client-side:
                                                   only drivers already on the board snapshot move)
  order      {id, event, state}                   — order lifecycle / dispatch change
  exception  {id, event}                          — exception opened / resolved / dispatch fix
"""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

CHANNEL = "porterchain:ops:live"
ROLE, TOPIC = "ops", "live"

_EXCEPTION_PREFIXES = ("exception.", "order.exception", "dispatch.exception")
_ORDER_PREFIXES = ("order.", "dispatch.", "booking.confirmed")


def encode(payload: dict[str, Any]) -> str:
    return json.dumps(
        {"origin": "sync", "local_delivered": False, "user_role": ROLE, "user_id": TOPIC, "payload": payload},
        separators=(",", ":"),
        default=str,
    )


def publish_ops_live(payload: dict[str, Any], *, client: Any | None = None) -> None:
    try:
        if client is None:
            from porterchain_shared.redis_client import get_redis_client

            client = get_redis_client()
        client.publish(CHANNEL, encode(payload))
    except Exception:  # noqa: BLE001 — live view is best-effort; polling covers gaps
        logger.debug("ops live publish failed", exc_info=True)


def message_for_event(
    event_type: str, aggregate_type: str, aggregate_id: str, payload: dict[str, Any] | None
) -> dict[str, Any] | None:
    """Domain event → ops live message, or None when Today does not care."""
    et = str(event_type or "")
    p = payload or {}
    if et.startswith(_EXCEPTION_PREFIXES) or aggregate_type in ("exception", "order_exception"):
        return {"type": "exception", "id": aggregate_id, "event": et, "order_id": p.get("order_id")}
    if aggregate_type == "order" and et.startswith(_ORDER_PREFIXES):
        return {"type": "order", "id": aggregate_id, "event": et, "state": p.get("to_state") or p.get("state")}
    return None


def driver_message(*, driver_id: str, lat: float, lng: float, heading: float | None, at: str) -> dict[str, Any]:
    return {"type": "driver", "id": driver_id, "lat": lat, "lng": lng, "heading": heading, "at": at}
