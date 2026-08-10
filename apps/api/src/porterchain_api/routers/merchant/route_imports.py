"""Merchant route import — vehicle-first multi-stop import with Nominatim + GTA quote."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from porterchain_api.auth.merchant import get_merchant_context
from porterchain_api.config import Settings, get_settings
from porterchain_api.db import get_db
from porterchain_api.merchant_engine.rbac import MerchantContext, require_module
from porterchain_api.merchant_engine.route_import_service import MerchantRouteImportService
from porterchain_api.routers.merchant._deps import _handle_permission, router
from porterchain_api.schemas_merchant import (
    RouteImportCreateRequest,
    RouteImportMappingPatch,
    RouteImportProfileResponse,
    RouteImportProfileSaveRequest,
    RouteImportResponse,
    RouteImportStopPatch,
)

_route_import = MerchantRouteImportService()


def _respond(job) -> RouteImportResponse:
    return RouteImportResponse(**_route_import.job_response(job))


@router.post(
    "/route-imports",
    response_model=RouteImportResponse,
    summary="Create route import preview from JSON (agent/API SSOT)",
    response_description="Preview with stops, Nominatim status, Valhalla distance, and GTA quote",
    openapi_extra={
        "x-porterchain-agent": {
            "geocode": "nominatim",
            "distance": "valhalla_osrm",
            "pricing": "gta_rate",
            "idempotency": "body.idempotency_key",
        }
    },
)
def create_route_import_json(
    body: RouteImportCreateRequest,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> RouteImportResponse:
    try:
        require_module(ctx, "bulk")
        job = _route_import.create_from_json(db, ctx, body.model_dump(mode="json"))
        return _respond(job)
    except PermissionError as exc:
        _handle_permission(exc)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post(
    "/route-imports/upload",
    response_model=RouteImportResponse,
    summary="Create route import preview from CSV/XLSX/XLS",
)
async def create_route_import_upload(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
    file: UploadFile = File(...),
    vehicle_class: str = Form("cargoVan"),
    scheduled_at: str | None = Form(None),
    package_type: str = Form("looseParcel"),
) -> RouteImportResponse:
    try:
        require_module(ctx, "bulk")
        data = await file.read()
        job = _route_import.create_from_file(
            db,
            ctx,
            filename=file.filename or "upload.csv",
            data=data,
            vehicle_class=vehicle_class or "cargoVan",
            scheduled_at=scheduled_at,
            package_type=package_type or "looseParcel",
        )
        return _respond(job)
    except PermissionError as exc:
        _handle_permission(exc)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/route-imports/{job_id}", response_model=RouteImportResponse)
def get_route_import(
    job_id: str,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> RouteImportResponse:
    try:
        require_module(ctx, "bulk")
        return _respond(_route_import.get_job(db, ctx, job_id))
    except PermissionError as exc:
        _handle_permission(exc)
    except LookupError:
        raise HTTPException(status_code=404, detail="route_import_not_found") from None


@router.patch("/route-imports/{job_id}/mapping", response_model=RouteImportResponse)
def patch_route_import_mapping(
    job_id: str,
    body: RouteImportMappingPatch,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> RouteImportResponse:
    try:
        require_module(ctx, "bulk")
        mapping = [m.model_dump() for m in body.mapping]
        return _respond(_route_import.patch_mapping(db, ctx, job_id, mapping))
    except PermissionError as exc:
        _handle_permission(exc)
    except LookupError:
        raise HTTPException(status_code=404, detail="route_import_not_found") from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.patch("/route-imports/{job_id}/stops/{index}", response_model=RouteImportResponse)
def patch_route_import_stop(
    job_id: str,
    index: int,
    body: RouteImportStopPatch,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> RouteImportResponse:
    try:
        require_module(ctx, "bulk")
        return _respond(
            _route_import.patch_stop(db, ctx, job_id, index, body.model_dump(exclude_unset=True))
        )
    except PermissionError as exc:
        _handle_permission(exc)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None


@router.post(
    "/route-imports/{job_id}/optimize",
    response_model=RouteImportResponse,
    summary="Reorder drops (nearest-neighbor + 2-opt) and re-quote",
)
def optimize_route_import(
    job_id: str,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> RouteImportResponse:
    try:
        require_module(ctx, "bulk")
        return _respond(_route_import.optimize(db, ctx, job_id))
    except PermissionError as exc:
        _handle_permission(exc)
    except LookupError:
        raise HTTPException(status_code=404, detail="route_import_not_found") from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/route-import-profiles", response_model=list[RouteImportProfileResponse])
def list_route_import_profiles(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
) -> list[RouteImportProfileResponse]:
    try:
        require_module(ctx, "bulk")
        return [RouteImportProfileResponse(**p) for p in _route_import.list_mapping_profiles(ctx)]
    except PermissionError as exc:
        _handle_permission(exc)
        return []


@router.post(
    "/route-imports/{job_id}/mapping-profile",
    response_model=RouteImportProfileResponse,
)
def save_route_import_mapping_profile(
    job_id: str,
    body: RouteImportProfileSaveRequest,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> RouteImportProfileResponse:
    try:
        require_module(ctx, "bulk")
        return RouteImportProfileResponse(
            **_route_import.save_mapping_profile(db, ctx, job_id, body.name)
        )
    except PermissionError as exc:
        _handle_permission(exc)
    except LookupError:
        raise HTTPException(status_code=404, detail="route_import_not_found") from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/route-imports/{job_id}/confirm", response_model=RouteImportResponse)
def confirm_route_import(
    job_id: str,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> RouteImportResponse:
    try:
        require_module(ctx, "bulk")
        return _respond(_route_import.confirm(db, settings, ctx, job_id))
    except PermissionError as exc:
        _handle_permission(exc)
    except LookupError:
        raise HTTPException(status_code=404, detail="route_import_not_found") from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
