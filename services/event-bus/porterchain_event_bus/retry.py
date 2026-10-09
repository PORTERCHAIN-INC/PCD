"""Retry policy for event handler failures."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 5
    base_delay_seconds: float = 2.0
    max_delay_seconds: float = 900.0

    def should_retry(self, attempt: int) -> bool:
        return attempt < self.max_attempts
