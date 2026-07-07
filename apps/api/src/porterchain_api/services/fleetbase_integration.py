"""Factory for Fleetbase adapter."""

from porterchain_api.config import Settings
from porterchain_fleetbase_adapter import FleetbaseAdapter
from porterchain_fleetbase_adapter.config import FleetbaseSettings


def get_fleetbase_integration(settings: Settings) -> FleetbaseAdapter:
    return FleetbaseAdapter(
        FleetbaseSettings(
            api_url=settings.fleetbase_api_url,
            api_key=settings.fleetbase_api_key,
            company_uuid=settings.fleetbase_default_company_uuid,
            dispatch_bridge=settings.fleetbase_dispatch_bridge,
            webhook_secret=settings.fleetbase_webhook_secret,
        )
    )
