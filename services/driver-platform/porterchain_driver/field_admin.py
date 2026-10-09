"""Field steps a super admin runs for an assigned driver."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.booking_models import Order, Package
from porterchain_api.config import Settings
from porterchain_api.merchant_engine.scan_gate_service import (
    STATUS_DELIVERED,
    STATUS_LOADED,
    STATUS_MANIFESTED,
    STATUS_OUT_FOR_DELIVERY,
    STATUS_PICKED_UP,
    PackagesIncomplete,
    ScanGateService)
from porterchain_driver.availability import AvailabilityService
from porterchain_driver.stops import StopsService

PARCEL_STATUSES = (
    STATUS_MANIFESTED,
    STATUS_PICKED_UP,
    STATUS_LOADED,
    STATUS_OUT_FOR_DELIVERY,
    STATUS_DELIVERED)


def parcel_rows(db: Session, order: Order) -> list[dict[str, Any]]:
    return ScanGateService().package_rows(db, order)


def perform(db: Session, settings: Settings, driver: Any, order: Order, action: str) -> None:
    stops = StopsService()
    availability = AvailabilityService()
    try:
        _perform(stops, availability, db, driver, order, action)
    except PackagesIncomplete as exc:
        missing = exc.payload.get("missing_suffixes") if isinstance(exc.payload, dict) else None
        suffix = f" Still open: {', '.join(missing)}." if missing else ""
        raise ValueError(f"Set each parcel status before completing this stop.{suffix}") from exc
    except PermissionError as exc:
        from porterchain_driver.pod_policy import DriverOffDuty, PodMissing, human_missing

        if isinstance(exc, PodMissing):
            raise ValueError(
                f"{human_missing(exc.missing)} Use “Finish without proof” (with a reason) to override."
            ) from exc
        if isinstance(exc, DriverOffDuty):
            raise ValueError(
                "This driver is not on shift. Use “Finish without proof” (with a reason) to override."
            ) from exc
        if str(exc) in {"pod_required", "pod_complete_required"}:
            raise ValueError(
                "Proof of delivery is still required before this stop can be completed."
            ) from exc
        raise


def record_proof_url(db: Session, settings: Settings, driver: Any, order: Order, file_url: str) -> None:
    """Super admin attaches a delivery photo on the driver's behalf (counts as photo proof)."""
    url = (file_url or "").strip()
    if not url.startswith(("https://", "http://", "data:image/")):
        raise ValueError("Give a photo URL (https://…).")
    from porterchain_driver.pod import ProofOfDeliveryService

    ProofOfDeliveryService()._record_pod(db, order.id, driver.id, "photo", url)


def set_parcel_status(
    db: Session,
    order: Order,
    parcel_id: str,
    status: str,
    tracking_suffix: str | None = None,  # accepted for the admin API; lookup is by id
) -> tuple[Package, str]:
    if status not in PARCEL_STATUSES:
        raise ValueError(
            "Choose a parcel status: manifested, picked up, loaded, out for delivery, or delivered."
        )
    parcel = (
        db.query(Package).filter(Package.id == parcel_id, Package.order_id == order.id).first()
    )
    if parcel is None:
        parcel_rows(db, order)
        parcel = (
            db.query(Package).filter(Package.id == parcel_id, Package.order_id == order.id).first()
        )
    if parcel is None:
        raise LookupError("parcel_not_found")
    previous = parcel.status
    parcel.status = status
    return parcel, previous




def _perform(
    stops: StopsService,
    availability: AvailabilityService,
    db: Session,
    driver: Any,
    order: Order,
    action: str,
) -> None:
    if action == "accept":
        availability.accept_assignment(db, driver, order.id)
    elif action == "decline":
        availability.reject_assignment(
            db, driver, order.id, reason="super_admin"
        )
    elif action == "start_route":
        route = stops.assigned_route(db, driver)
        if route is None:
            raise ValueError("This driver has no route to start.")
        stops.start_route(db, driver, route.route_id)
    elif action == "arrive_pickup":
        stops.arrive_stop(
            db,
            driver,
            f"{order.id}-pickup",
            enforce_sequence=False,
            skip_presence=True)
    elif action == "complete_pickup":
        stops.deliver_stop(
            db, driver, f"{order.id}-pickup", enforce_sequence=False
        )
    elif action == "arrive_delivery":
        stops.arrive_stop(
            db,
            driver,
            f"{order.id}-dropoff",
            enforce_sequence=False,
            skip_presence=True)
    elif action == "complete_delivery":
        stops.deliver_stop(
            db, driver, f"{order.id}-dropoff", enforce_sequence=False
        )
    elif action == "complete_delivery_without_proof":
        # Audited super-admin override: skips the POD and on-shift gates (scan gate still applies).
        stops.deliver_stop(
            db,
            driver,
            f"{order.id}-dropoff",
            enforce_sequence=False,
            pod_override=True,
            duty_override=True,
        )
    else:
        raise ValueError("That step is not available for this order.")
