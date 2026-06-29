"""Driver service — execution API boundary."""

from porterchain_services.base import BaseService
from porterchain_shared.auth.session import SessionTokens


class DriverService(BaseService):
    service_name = "driver"

    def issue_session(self, driver_id: str, *, secret: str, email: str | None = None) -> SessionTokens:
        from porterchain_driver.auth_tokens import issue_driver_session

        return issue_driver_session(driver_id, secret=secret, email=email)

    def sync_to_fleetbase(self, driver_id: str, payload: dict) -> str | None:
        from porterchain_services.gateway.registry import get_service_registry

        return get_service_registry().fleetbase.sync_driver(
            {"porterchain_driver_id": driver_id, **payload}
        )

    def get_platform(self):
        from porterchain_driver import DriverPlatform

        return DriverPlatform()
