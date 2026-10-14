"""Redact credentials from uvicorn access/error log lines.

WebSocket clients pass the session token as ``?token=`` (browsers cannot set headers on
WS). uvicorn logs the full path, so without this every connect wrote a live staff/driver
session token to the container log.
"""

from __future__ import annotations

import logging
import re

_SECRET_QS = re.compile(r"(?i)\b(token|access_token|ticket|key|signature|code)=([^&\s\"']+)")
_BEARER = re.compile(r"(staff_sess_|imp_)[A-Za-z0-9_\-]+")


def redact(text: str) -> str:
    return _BEARER.sub(r"\1REDACTED", _SECRET_QS.sub(r"\1=REDACTED", text))


class RedactTokensFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            if record.args:
                args = record.args if isinstance(record.args, tuple) else (record.args,)
                record.args = tuple(redact(a) if isinstance(a, str) else a for a in args)
            if isinstance(record.msg, str):
                record.msg = redact(record.msg)
        except Exception:  # noqa: BLE001 - never drop a log line
            pass
        return True


_FILTER = RedactTokensFilter()


def install() -> None:
    """Idempotent: attach to uvicorn loggers and their handlers."""
    for name in ("uvicorn.access", "uvicorn.error", "uvicorn"):
        lg = logging.getLogger(name)
        if _FILTER not in lg.filters:
            lg.addFilter(_FILTER)
        for h in lg.handlers:
            if _FILTER not in h.filters:
                h.addFilter(_FILTER)
