"""Factory for Fleetbase adapter."""

from porterchain_api.config import Settings
from porterchain_fleetbase_adapter import FleetbaseAdapter
from porterchain_fleetbase_adapter.config import FleetbaseSettings


def get_fleetbase_integration(
    settings: Settings, *, max_retries: int | None = None
) -> FleetbaseAdapter:
    """Build the adapter. Pass max_retries=0 on the RetryQueue drain path only."""
    kwargs: dict = {
        "api_url": settings.fleetbase_api_url,
        "api_key": settings.fleetbase_api_key,
        "company_uuid": settings.fleetbase_default_company_uuid,
        "dispatch_bridge": settings.fleetbase_dispatch_bridge,
        "webhook_secret": settings.fleetbase_webhook_secret,
        "ops_timeout": float(getattr(settings, "fleetbase_ops_timeout", 2.0)),
        "request_timeout": float(getattr(settings, "fleetbase_request_timeout", 15.0)),
    }
    if max_retries is not None:
        kwargs["max_retries"] = max_retries
    return FleetbaseAdapter(FleetbaseSettings(**kwargs))
