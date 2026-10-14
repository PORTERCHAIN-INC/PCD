"""DB pool pressure + idle-in-transaction kill alerts (2026-10-14 freeze follow-up).

Logs at ERROR (picked up by Sentry's logging integration) when:
- pool checkout usage crosses POOL_ALERT_RATIO of pool_size + max_overflow, or
- Postgres kills a connection with IdleInTransactionSessionTimeout.
"""

from __future__ import annotations

import asyncio
import logging
import time

from sqlalchemy import event
from sqlalchemy.engine import Engine

logger = logging.getLogger("porterchain.db_pool")

POOL_ALERT_RATIO = 0.8
_ALERT_COOLDOWN_S = 60.0
_last_alert: dict[str, float] = {}
idle_tx_kills = 0


def pool_usage(engine: Engine) -> dict[str, float]:
    pool = engine.pool
    size = getattr(pool, "size", lambda: 0)()
    overflow_max = getattr(pool, "_max_overflow", 0)
    capacity = max(size + max(overflow_max, 0), 1)
    checked_out = getattr(pool, "checkedout", lambda: 0)()
    return {"checked_out": checked_out, "capacity": capacity, "ratio": checked_out / capacity}


def _alert(kind: str, msg: str, *args) -> bool:
    now = time.monotonic()
    if now - _last_alert.get(kind, -1e9) < _ALERT_COOLDOWN_S:
        return False
    _last_alert[kind] = now
    logger.error(msg, *args)
    return True


def check_pool(engine: Engine) -> bool:
    u = pool_usage(engine)
    if u["ratio"] > POOL_ALERT_RATIO:
        return _alert(
            "pool", "db_pool_pressure checked_out=%d capacity=%d ratio=%.2f",
            u["checked_out"], u["capacity"], u["ratio"],
        )
    return False


def _on_handle_error(ctx) -> None:
    global idle_tx_kills
    orig = getattr(ctx, "original_exception", None)
    if orig is not None and type(orig).__name__ == "IdleInTransactionSessionTimeout":
        idle_tx_kills += 1
        _alert("idle_tx", "db_idle_in_transaction_killed total=%d", idle_tx_kills)


def install(engine: Engine) -> None:
    if not event.contains(engine, "handle_error", _on_handle_error):
        event.listen(engine, "handle_error", _on_handle_error)
    if not event.contains(engine, "checkout", _on_checkout):
        event.listen(engine, "checkout", _on_checkout)


def _on_checkout(dbapi_conn, record, proxy) -> None:  # noqa: ARG001
    from porterchain_api.db import engine

    check_pool(engine)


async def run_pool_watch(engine: Engine, interval_s: float = 15.0) -> None:
    while True:
        check_pool(engine)
        await asyncio.sleep(interval_s)
