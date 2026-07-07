"""Retry policy for transient Fleetbase API failures."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import TypeVar

from porterchain_fleetbase_adapter.exceptions import FleetbaseApiError

T = TypeVar("T")

RETRYABLE_STATUS_CODES = {408, 429, 500, 502, 503, 504}


class RetryPolicy:
    """Exponential backoff retry for idempotent-safe Fleetbase calls."""

    def __init__(self, *, max_retries: int = 3, backoff_seconds: float = 0.5) -> None:
        self.max_retries = max(0, max_retries)
        self.backoff_seconds = max(0.0, backoff_seconds)

    def run(self, operation: Callable[[], T], *, is_retryable: Callable[[Exception], bool] | None = None) -> T:
        attempt = 0
        while True:
            try:
                return operation()
            except Exception as exc:
                attempt += 1
                retryable = is_retryable(exc) if is_retryable else _default_retryable(exc)
                if not retryable or attempt > self.max_retries:
                    raise
                time.sleep(self.backoff_seconds * (2 ** (attempt - 1)))


def _default_retryable(exc: Exception) -> bool:
    if isinstance(exc, FleetbaseApiError) and exc.status_code is not None:
        return exc.status_code in RETRYABLE_STATUS_CODES
    return False
