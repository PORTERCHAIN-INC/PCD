"""Fleetbase adapter errors."""


class FleetbaseError(Exception):
    """Base error for Fleetbase adapter."""


class FleetbaseNotConfiguredError(FleetbaseError):
    """Bridge disabled or missing configuration."""


class FleetbaseApiError(FleetbaseError):
    def __init__(self, message: str, *, status_code: int | None = None, body: str = "") -> None:
        super().__init__(message)
        self.status_code = status_code
        self.body = body


class FleetbaseCircuitOpenError(FleetbaseApiError):
    """Circuit breaker is OPEN — fail fast; caller requeues via RetryQueue/DLQ."""

    def __init__(self, message: str = "Fleetbase circuit open") -> None:
        super().__init__(message, status_code=503)


class FleetbaseVersionError(FleetbaseError):
    """Fleetbase API version mismatch."""
