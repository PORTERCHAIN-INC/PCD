"""Retry policy for event handler failures."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 5
    base_delay_seconds: float = 2.0
    max_delay_seconds: float = 900.0

    def delay_for_attempt(self, attempt: int) -> float:
        if attempt <= 0:
            return 0.0
        delay = self.base_delay_seconds * (2 ** (attempt - 1))
        return min(delay, self.max_delay_seconds)

    def should_retry(self, attempt: int) -> bool:
        return attempt < self.max_attempts
