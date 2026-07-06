"""Driver platform API — /driver-api/v1/* extends Fleetbase capabilities."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from porterchain_api.auth.driver import get_driver_context
from porterchain_api.config import Settings, get_settings
from porterchain_api.db import get_db
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
    EmergencyRequest,
    EmergencyContactUpdateRequest,
    ExceptionRequest,
    IncidentRequest,
    LocationPingRequest,
    OfflineActionRequest,
    PodBarcodeRequest,
    PodOtpRequest,
    PodPhotoRequest,
    PodSignatureRequest,
    PushRegisterRequest,
    RouteResponse,
    ShiftStartRequest,
    StopResponse,
    SupportTicketRequest,
)
from porterchain_api.driver_engine.api_service import DriverApiService
from porterchain_api.driver_engine.mappers import driver_profile, guard_portal_ready, route_response, stop_response

router = APIRouter(prefix="/driver-api/v1", tags=["driver"])
svc = DriverApiService()


def guard_portal_ready(ctx: DriverContext, settings: Settings) -> None:
    try:
        guard_portal_ready(ctx, settings)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


