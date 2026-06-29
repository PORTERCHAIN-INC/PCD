"""Driver platform RBAC."""

from dataclasses import dataclass

from porterchain_api.admin_models import Driver
from porterchain_api.domain.admin_states import DriverStatus


@dataclass(frozen=True)
class DriverContext:
    driver: Driver


def require_approved_driver(ctx: DriverContext) -> None:
    if ctx.driver.status != DriverStatus.APPROVED.value:
        raise PermissionError("driver_not_approved")
