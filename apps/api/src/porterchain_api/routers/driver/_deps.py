"""Driver platform API — /driver-api/v1/* (PorterChain duty, GPS, jobs, proof)."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from porterchain_api.auth.driver import get_driver_context
from porterchain_api.config import Settings, get_settings
from porterchain_api.db import get_db
from porterchain_api.driver_engine.api_service import DriverApiService
from porterchain_api.driver_engine.mappers import (
    driver_profile,
    route_response,
    stop_response,
)
from porterchain_api.driver_engine.mappers import (
    guard_portal_ready as _guard_portal_ready,
)
from porterchain_api.driver_engine.rbac import (
    DriverContext,
    evaluate_driver_onboarding,
    require_approved_driver,
)
from porterchain_api.schemas_driver import (
    AcceptRejectRequest,
    AvailabilityRequest,
    DocumentUploadRequest,
    DriverClaimOpenRequest,
    DriverDashboardResponse,
    DriverJobDetailResponse,
    DriverJobsListResponse,
    DriverJobsOptimizeResponse,
    DriverLoginRequest,
    DriverOnboardingResponse,
    DriverProfileResponse,
    DriverRefreshRequest,
    DriverTokenResponse,
    EmergencyContactUpdateRequest,
    EmergencyRequest,
    ExceptionRequest,
    IncidentRequest,
    LocationPingRequest,
    OfflineActionRequest,
    PackageMissingRequest,
    PodBarcodeRequest,
    PodIdCheckRequest,
    PodOtpRequest,
    PodPhotoRequest,
    PodSignatureRequest,
    PushRegisterRequest,
    PushUnregisterRequest,
    RouteResponse,
    ShiftStartRequest,
    StopResponse,
    SupportTicketRequest,
)

router = APIRouter(prefix="/driver-api/v1", tags=["driver"])
svc = DriverApiService()


def guard_portal_ready(ctx: DriverContext, settings: Settings) -> None:
    try:
        _guard_portal_ready(ctx, settings)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


__all__ = [
    "APIRouter",
    "AcceptRejectRequest",
    "Annotated",
    "Any",
    "AvailabilityRequest",
    "Depends",
    "DocumentUploadRequest",
    "DriverClaimOpenRequest",
    "DriverContext",
    "DriverDashboardResponse",
    "DriverJobDetailResponse",
    "DriverJobsListResponse",
    "DriverJobsOptimizeResponse",
    "DriverLoginRequest",
    "DriverOnboardingResponse",
    "DriverProfileResponse",
    "DriverRefreshRequest",
    "DriverTokenResponse",
    "EmergencyContactUpdateRequest",
    "EmergencyRequest",
    "ExceptionRequest",
    "HTTPException",
    "Header",
    "IncidentRequest",
    "LocationPingRequest",
    "OfflineActionRequest",
    "PackageMissingRequest",
    "PodBarcodeRequest",
    "PodIdCheckRequest",
    "PodOtpRequest",
    "PodPhotoRequest",
    "PodSignatureRequest",
    "PushRegisterRequest",
    "PushUnregisterRequest",
    "Query",
    "Response",
    "RouteResponse",
    "Session",
    "Settings",
    "ShiftStartRequest",
    "StopResponse",
    "SupportTicketRequest",
    "_guard_portal_ready",
    "driver_profile",
    "evaluate_driver_onboarding",
    "get_db",
    "get_driver_context",
    "get_settings",
    "guard_portal_ready",
    "require_approved_driver",
    "route_response",
    "router",
    "stop_response",
    "svc",
]

