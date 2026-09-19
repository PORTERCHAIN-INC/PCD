"""Fleetbase adapter connection settings."""

from dataclasses import dataclass


@dataclass(frozen=True)
class FleetbaseSettings:
    api_url: str = "http://localhost:8000"
    api_key: str = ""
    company_uuid: str = ""
    dispatch_bridge: bool = True
    webhook_secret: str = ""
    # Mutating / drain HTTP budget (RetryQueue owns retries).
    request_timeout: float = 15.0
    # User-path GET leftover ops — fail fast so uvicorn workers do not cascade.
    # Orchestrator run is mutate-class and uses request_timeout (worker only).
    ops_timeout: float = 2.0
    api_version: str = "v1"
    max_retries: int = 3
    retry_backoff_seconds: float = 0.5
    breaker_failure_threshold: int = 5
    breaker_open_seconds: float = 30.0

    @property
    def is_enabled(self) -> bool:
        return self.dispatch_bridge and bool(self.api_url)

    @property
    def is_authenticated(self) -> bool:
        return bool(self.api_key)
