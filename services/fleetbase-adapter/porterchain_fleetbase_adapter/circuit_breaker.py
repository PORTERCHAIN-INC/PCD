"""Process-local circuit breaker for Fleetbase HTTP (OPEN / HALF-OPEN / CLOSED).

Shared across FleetbaseClient instances so ephemeral adapters still trip together.
Failures go to RetryQueue / event DLQ via normal exception paths — no second worker.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field

from porterchain_fleetbase_adapter.exceptions import FleetbaseCircuitOpenError

logger = logging.getLogger(__name__)


@dataclass
class CircuitBreaker:
    failure_threshold: int = 5
    open_seconds: float = 30.0
    _state: str = "closed"
    _failures: int = 0
    _opened_at: float | None = None
    _lock: threading.Lock = field(default_factory=threading.Lock)

    @property
    def state(self) -> str:
        with self._lock:
            self._maybe_half_open_unlocked()
            return self._state

    def before_call(self) -> None:
        with self._lock:
            self._maybe_half_open_unlocked()
            if self._state == "open":
                raise FleetbaseCircuitOpenError(
                    f"Fleetbase circuit open (failures={self._failures})"
                )

    def record_success(self) -> None:
        with self._lock:
            prev = self._state
            self._failures = 0
            self._state = "closed"
            self._opened_at = None
            if prev != "closed":
                logger.info("fleetbase_circuit_closed previous=%s", prev)

    def record_failure(self) -> None:
        with self._lock:
            self._failures += 1
            if self._state == "half_open" or self._failures >= self.failure_threshold:
                self._state = "open"
                self._opened_at = time.monotonic()
                logger.warning(
                    "fleetbase_circuit_open failures=%s threshold=%s",
                    self._failures,
                    self.failure_threshold,
                )

    def reset(self) -> None:
        with self._lock:
            self._state = "closed"
            self._failures = 0
            self._opened_at = None

    def _maybe_half_open_unlocked(self) -> None:
        if self._state != "open" or self._opened_at is None:
            return
        if time.monotonic() - self._opened_at >= self.open_seconds:
            self._state = "half_open"
            logger.info("fleetbase_circuit_half_open after_seconds=%s", self.open_seconds)


_shared: CircuitBreaker | None = None
_shared_lock = threading.Lock()


def get_shared_breaker(
    *,
    failure_threshold: int = 5,
    open_seconds: float = 30.0,
) -> CircuitBreaker:
    global _shared
    with _shared_lock:
        if _shared is None:
            _shared = CircuitBreaker(
                failure_threshold=failure_threshold,
                open_seconds=open_seconds,
            )
        else:
            # Keep thresholds from first init; tests call reset_shared_breaker().
            pass
        return _shared


def reset_shared_breaker(
    *,
    failure_threshold: int = 5,
    open_seconds: float = 30.0,
) -> CircuitBreaker:
    global _shared
    with _shared_lock:
        _shared = CircuitBreaker(
            failure_threshold=failure_threshold,
            open_seconds=open_seconds,
        )
        return _shared
