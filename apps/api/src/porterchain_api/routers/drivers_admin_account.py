"""Driver profile, document decision, and vehicle routes.

Split from drivers_admin so that module stays within the router size cap.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from porterchain_api.config import Settings, get_settings
from porterchain_api.db import get_db
from porterchain_api.routers.drivers_admin import Ctx, _d360, _drivers, _invoke, _mutated, _vehicle
from porterchain_api.schemas_admin import (
    DriverDocumentDecisionRequest,
    DriverProfilePatch,
    DriverVehicleCreateInput,
    DriverVehicleUpdate,
)

router = APIRouter(prefix="/v1/admin/drivers", tags=["drivers"])


@router.patch("/{driver_id}")
def update_driver_profile(driver_id: str, body: DriverProfilePatch, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    payload = body.model_dump(exclude_unset=True)
    if "address" in payload and payload["address"] is not None:
        payload["address"] = body.address.model_dump(exclude_none=True) if body.address else None
    if "emergency_contact" in payload and body.emergency_contact is not None:
        payload["emergency_contact"] = body.emergency_contact.model_dump(exclude_none=True)
    return _mutated(ctx, db, driver_id, _drivers.update_profile, **payload)


@router.post("/{driver_id}/documents/decision")
def decide_driver_document(
    driver_id: str, body: DriverDocumentDecisionRequest, ctx: Ctx, db: Session = Depends(get_db)
) -> dict:
    return _mutated(
        ctx,
        db,
        driver_id,
        _drivers.decide_document,
        doc_type=body.doc_type,
        decision=body.decision,
        reason=body.reason,
    )


@router.get("/{driver_id}/vehicles")
def driver_vehicles(driver_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> list[dict]:
    return _invoke(ctx, "drivers_read", _d360.vehicles, db, driver_id)


@router.post("/{driver_id}/vehicles", status_code=201)
def attach_driver_vehicle(
    driver_id: str,
    body: DriverVehicleCreateInput,
    ctx: Ctx,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    """D-29: attach vehicle and sync Fleetbase when bridge enabled."""
    vehicle = _invoke(
        ctx,
        "drivers",
        _drivers.attach_vehicle,
        db,
        ctx,
        driver_id,
        vehicle_class=body.vehicle_class,
        plate_number=body.plate_number,
        make_model=body.make_model,
        capacity_kg=body.capacity_kg,
        settings=settings,
    )
    return _vehicle(vehicle)


@router.post("/{driver_id}/vehicles/{vehicle_id}/deactivate")
def deactivate_driver_vehicle(
    driver_id: str,
    vehicle_id: str,
    ctx: Ctx,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    """D-29: deactivate vehicle and push inactive state to Fleetbase."""
    return _vehicle(
        _invoke(ctx, "drivers", _drivers.deactivate_vehicle, db, ctx, driver_id, vehicle_id, settings=settings)
    )


@router.patch("/{driver_id}/vehicles/{vehicle_id}")
def update_driver_vehicle(
    driver_id: str,
    vehicle_id: str,
    body: DriverVehicleUpdate,
    ctx: Ctx,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    return _vehicle(
        _invoke(
            ctx,
            "drivers",
            _drivers.update_vehicle,
            db,
            ctx,
            driver_id,
            vehicle_id,
            settings=settings,
            **body.model_dump(exclude_unset=True),
        )
    )
