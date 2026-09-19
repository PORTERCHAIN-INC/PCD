"""Centralized error handling and logging for Fleetbase adapter."""

from __future__ import annotations

import logging
from typing import Any

from porterchain_fleetbase_adapter.exceptions import FleetbaseApiError, FleetbaseError, FleetbaseNotConfiguredError

logger = logging.getLogger(__name__)


class ErrorHandler:
    """Translate Fleetbase errors into structured outcomes for Porterchain callers."""

    def __init__(self, *, logger_name: str | None = None) -> None:
        self._logger = logging.getLogger(logger_name) if logger_name else logger

    def log_and_suppress(self, exc: Exception, context: str, *, level: int = logging.WARNING) -> None:
        if isinstance(exc, FleetbaseApiError):
            body = (exc.body or "")[:200]
            self._logger.log(
                level,
                "%s: %s status=%s body=%s",
                context,
                exc,
                exc.status_code,
                body,
            )
            return
        self._logger.log(level, "%s: %s", context, exc)

    def to_result(self, exc: Exception, context: str) -> dict[str, Any]:
        self.log_and_suppress(exc, context)
        return {
            "ok": False,
            "error": str(exc),
            "error_type": type(exc).__name__,
            "status_code": getattr(exc, "status_code", None),
        }

    @staticmethod
    def is_configuration_error(exc: Exception) -> bool:
        return isinstance(exc, FleetbaseNotConfiguredError)

    @staticmethod
    def is_api_error(exc: Exception) -> bool:
        return isinstance(exc, FleetbaseApiError)

    @staticmethod
    def is_retryable(exc: Exception) -> bool:
        if isinstance(exc, FleetbaseApiError):
            body = (exc.body or "").lower()
            if "too many requests" in body or "rate limit" in body:
                return True
            if exc.status_code is not None:
                return exc.status_code in {408, 429, 500, 502, 503, 504}
        return False
