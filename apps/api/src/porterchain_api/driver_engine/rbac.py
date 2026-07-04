"""Driver platform RBAC."""

from dataclasses import dataclass

from porterchain_api.admin_models import Driver
from porterchain_api.domain.admin_states import DriverStatus
from porterchain_api.driver_engine.onboarding_service import (
    evaluate_driver_onboarding,
    require_fully_onboarded_driver,
)

__all__ = [
    "DriverContext",
    "evaluate_driver_onboarding",
    "require_approved_driver",
    "require_fully_onboarded_driver",
]


@dataclass(frozen=True)
class DriverContext:
    driver: Driver


def require_approved_driver(ctx: DriverContext) -> None:
    if ctx.driver.status != DriverStatus.APPROVED.value:
        raise PermissionError("driver_not_approved")
