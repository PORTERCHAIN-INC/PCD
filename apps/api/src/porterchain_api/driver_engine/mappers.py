"""Driver API response mappers — UI layer helpers (masterrule §3)."""

from __future__ import annotations

from porterchain_api.admin_models import Driver
from porterchain_api.config import Settings
from porterchain_api.driver_engine.rbac import DriverContext, require_fully_onboarded_driver
from porterchain_api.schemas_driver import DriverProfileResponse, RouteResponse, StopResponse


def driver_profile(driver: Driver) -> DriverProfileResponse:
    return DriverProfileResponse(
        id=driver.id,
        full_name=driver.full_name,
        email=driver.email,
        phone=driver.phone,
        status=driver.status,
        rating=driver.rating,
        is_online=bool(driver.is_online),
        availability=driver.availability or "offline",
        wallet_balance_cents=driver.wallet_balance_cents or 0,
        license_verified=driver.license_verified,
        insurance_verified=driver.insurance_verified,
        vehicle_verified=driver.vehicle_verified,
        fleetbase_driver_id=driver.fleetbase_driver_id,
    )


def stop_response(s) -> StopResponse:
    return StopResponse(
        stop_id=s.stop_id,
        order_id=s.order_id,
        sequence=s.sequence,
        stop_type=s.stop_type,
        status=s.status,
        address=s.address,
        scheduled_at=s.scheduled_at,
        tracking_number=s.tracking_number,
        order_number=s.order_number,
        special_instructions=s.special_instructions,
        otp_required=s.otp_required,
        pod_required=s.pod_required,
    )


def route_response(r) -> RouteResponse:
    return RouteResponse(
        route_id=r.route_id,
        driver_id=r.driver_id,
        status=r.status,
        stops=[stop_response(s) for s in r.stops],
        route_polyline=r.route_polyline,
        earnings_cents=r.earnings_cents,
        started_at=r.started_at,
    )


def guard_portal_ready(ctx: DriverContext, settings: Settings) -> None:
    require_fully_onboarded_driver(ctx.driver, settings=settings)
