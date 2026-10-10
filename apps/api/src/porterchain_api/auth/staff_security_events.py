"""Per-staff security event feed + new-device detection (Redis)."""

from __future__ import annotations

import json
import logging
import time
from typing import Any

logger = logging.getLogger("porterchain.security")

EVENTS_PREFIX = "pc:staff:sec_events:v1:"
EVENTS_MAX = 40


def _client():
    try:
        from porterchain_shared.redis_client import get_redis_client

        client = get_redis_client()
        client.ping()
        return client
    except Exception:  # noqa: BLE001
        return None


def _key(admin_user_id: str) -> str:
    return f"{EVENTS_PREFIX}{admin_user_id}"


def device_fingerprint(client_meta: dict[str, str] | None) -> str:
    meta = client_meta or {}
    ip = (meta.get("client_ip") or "").strip()
    label = (meta.get("device_label") or "").strip()
    if not ip and not label:
        return ""
    return f"{ip}|{label}"


def is_new_device(admin_user_id: str, client_meta: dict[str, str] | None) -> bool:
    """True when fingerprint is absent from current sessions (and user has ≥1 other session)."""
    fp = device_fingerprint(client_meta)
    if not fp or not admin_user_id:
        return False
    from porterchain_api.auth.staff_session import list_sessions_for_user

    sessions = list_sessions_for_user(admin_user_id)
    if not sessions:
        return False
    for row in sessions:
        row_fp = device_fingerprint(
            {
                "client_ip": str(row.get("client_ip") or ""),
                "device_label": str(row.get("device_label") or ""),
            }
        )
        if row_fp and row_fp == fp:
            return False
    return True


def record_security_event(
    admin_user_id: str,
    *,
    kind: str,
    detail: dict[str, Any] | None = None,
) -> None:
    if not admin_user_id:
        return
    client = _client()
    if client is None:
        return
    payload = {
        "ts": time.time(),
        "kind": (kind or "unknown")[:64],
        "detail": detail or {},
    }
    try:
        key = _key(admin_user_id)
        client.lpush(key, json.dumps(payload))
        client.ltrim(key, 0, EVENTS_MAX - 1)
        client.expire(key, 60 * 60 * 24 * 90)
    except Exception:
        logger.debug("staff_security_event_record_failed", exc_info=True)


def list_security_events(admin_user_id: str, *, limit: int = 20) -> list[dict[str, Any]]:
    if not admin_user_id:
        return []
    client = _client()
    if client is None:
        return []
    try:
        raw = client.lrange(_key(admin_user_id), 0, max(0, min(limit, EVENTS_MAX) - 1)) or []
    except Exception:  # noqa: BLE001
        return []
    out: list[dict[str, Any]] = []
    for item in raw:
        try:
            text = item.decode() if isinstance(item, bytes) else str(item)
            data = json.loads(text)
            if isinstance(data, dict):
                out.append(data)
        except Exception:  # noqa: BLE001
            continue
    return out

