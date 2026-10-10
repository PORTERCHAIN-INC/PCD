"""Pydantic schemas for driver platform API."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class DriverLoginRequest(BaseModel):
    email: str
    phone: str | None = None


class DriverRefreshRequest(BaseModel):
    refresh_token: str


class DriverTokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int
    driver_id: str


class DriverProfileResponse(BaseModel):
    id: str
    full_name: str
    email: str
    phone: str | None
    status: str
    rating: float | None
    is_online: bool
    availability: str
    wallet_balance_cents: int
    license_verified: bool
    insurance_verified: bool
    vehicle_verified: bool


class DriverDashboardResponse(BaseModel):
    todays_earnings_cents: int
    todays_stops_total: int
    todays_stops_completed: int
    wallet_balance_cents: int
    is_online: bool
    availability: str
    rating: float | None
    active_route_id: str | None
    bonuses_available: int
    performance_score: float
    pending_documents: int


class DriverOnboardingStep(BaseModel):
    id: str
    label: str
    description: str
    complete: bool
    status: str
    missing: list[str] = Field(default_factory=list)


class DriverOnboardingResponse(BaseModel):
    ready: bool
    blockers: list[str]
    status: str
    clerk_linked: bool
    steps: list[DriverOnboardingStep]
    pending_documents: int
    can_access_portal: bool


class StopResponse(BaseModel):
    stop_id: str
    order_id: str
    sequence: int
    stop_type: str
    status: str
    address: dict
    scheduled_at: datetime | None
    tracking_number: str
    order_number: str
    special_instructions: str | None = None
    otp_required: bool = False
    pod_required: bool = True


class RouteResponse(BaseModel):
    route_id: str
    driver_id: str
    status: str
    stops: list[StopResponse]
    route_polyline: str | None = None
    earnings_cents: int = 0
    started_at: datetime | None = None


class AvailabilityRequest(BaseModel):
    online: bool | None = None
    mode: str | None = None


class ShiftStartRequest(BaseModel):
    route_id: str | None = None
    pretrip: dict[str, bool] | None = None


class LocationPingRequest(BaseModel):
    lat: float
    lng: float
    accuracy_m: float | None = None
    heading: float | None = None
    speed_mps: float | None = None
    recorded_at: str | None = None


class ExceptionRequest(BaseModel):
    exception_type: str
    notes: str | None = None
    photo_url: str | None = None


class PackageMissingRequest(BaseModel):
    """A box missing at pickup — photo (URL or camera data URL) and a reason code."""

    photo_url: str
    reason: Literal["not_ready", "not_found", "damaged", "wrong_item", "other"]
    notes: str | None = Field(default=None, max_length=500)


class DocumentUploadRequest(BaseModel):
    doc_type: str
    file_url: str
    metadata: dict | None = None


class PodPhotoRequest(BaseModel):
    file_url: str


class PodSignatureRequest(BaseModel):
    signature_data: str


class PodIdCheckRequest(BaseModel):
    """Receiver ID check — document type + yes/no checks only (no ID number / DOB stored)."""

    id_type: str
    name_matches: bool
    age_verified: bool | None = None


class PodBarcodeRequest(BaseModel):
    barcode: str


class PodOtpRequest(BaseModel):
    otp: str | None = None


class IncidentRequest(BaseModel):
    incident_type: str
    description: str
    order_id: str | None = None
    location: dict | None = None


class EmergencyRequest(BaseModel):
    message: str | None = None
    location: dict | None = None


class SupportTicketRequest(BaseModel):
    subject: str
    description: str | None = None
    order_id: str | None = None
    priority: str = "normal"
    category: str = "driver_support"


class DriverClaimOpenRequest(BaseModel):
    order_id: str
    claim_type: str
    description: str | None = None


class EmergencyContactUpdateRequest(BaseModel):
    name: str
    phone: str
    relationship: str | None = None


class PushRegisterRequest(BaseModel):
    device_token: str
    platform: str = "expo"


class PushUnregisterRequest(BaseModel):
    device_token: str | None = None


class OfflineActionRequest(BaseModel):
    action_type: str
    payload: dict = Field(default_factory=dict)
    client_id: str | None = None


class AcceptRejectRequest(BaseModel):
    reason: str | None = None


class DriverNextStop(BaseModel):
    stop_id: str
    stop_type: str
    order_id: str
    order_number: str | None = None
    tracking_number: str | None = None
    sequence: int | None = 0
    address: dict = Field(default_factory=dict)
    formatted_address: str = "—"
    distance_m: int | None = None
    eta_minutes: int | None = None
    status: str | None = None
    source: str | None = None
    special_instructions: str | None = None
    access_unit: str | None = None
    access_buzzer: str | None = None
    access_dock: str | None = None
    call_on_arrival: bool = False
    contact_phone_masked: str | None = None
    delivery_attempts: int = 0
    max_delivery_attempts: int = 2


class DriverScanProgress(BaseModel):
    scanned: int = 0
    required: int = 0
    complete: bool = False
    missing_suffixes: list[str] = Field(default_factory=list)


class DriverJobSummary(BaseModel):
    order_id: str
    order_number: str
    tracking_number: str
    state: str
    status: str
    bucket: str
    pickup_address: str
    delivery_address: str
    pickup_stop_id: str
    delivery_stop_id: str
    scheduled_at: str | None = None
    special_instructions: str | None = None
    urgency: str = "normal"
    high_priority: bool = False
    priority_rank: int | None = None
    current_leg: str = "pickup"
    pickup_completed: bool = False
    delivery_completed: bool = False
    is_current_job: bool = False
    route_id: str | None = None
    scan_pickup: DriverScanProgress = Field(default_factory=DriverScanProgress)
    scan_delivery: DriverScanProgress = Field(default_factory=DriverScanProgress)
    shopify_order_label: str | None = None


class DriverRouteMetrics(BaseModel):
    stop_count: int | None = None
    order_count: int | None = None
    distance_km: float | None = None
    duration_minutes: float | None = None
    estimated_fuel_cents: int | None = None
    estimated_fuel_liters: float | None = None
    source: str | None = None


class DriverJobsListResponse(BaseModel):
    route_id: str | None = None
    route_status: str | None = None
    plan_id: str | None = None
    route_metrics: DriverRouteMetrics | None = None
    optimize_available: bool = False
    next_stop: DriverNextStop | None = None
    current: DriverJobSummary | None = None
    upcoming: list[DriverJobSummary] = Field(default_factory=list)
    completed: list[DriverJobSummary] = Field(default_factory=list)
    jobs: list[DriverJobSummary] = Field(default_factory=list)


class DriverJobsOptimizeResponse(BaseModel):
    plan_id: str
    run_id: str | None = None
    status: str = "pending"
    optimized_stops: list[dict] = Field(default_factory=list)
    metrics: dict = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    order_ids: list[str] = Field(default_factory=list)
    message: str | None = None
    jobs: DriverJobsListResponse
    #: CAS token for admin/driver reopt race (Phase 5). Pass as expected_version.
    sequence_version: int | None = None
    preview: bool | None = None
    applied: bool | None = None
    apply_on_ready: bool | None = None
    ok: bool | None = None
    error: str | None = None


class DriverJobDetailResponse(DriverJobSummary):
    pickup_detail: dict = Field(default_factory=dict)
    delivery_detail: dict = Field(default_factory=dict)
    pickup_stop: dict = Field(default_factory=dict)
    delivery_stop: dict = Field(default_factory=dict)
    allowed_actions: list[str] = Field(default_factory=list)
    next_stop: DriverNextStop | None = None
    pickup_completed_at: str | None = None
    delivery_completed_at: str | None = None
    merchant: dict | None = None
    customer: dict = Field(default_factory=dict)
    packages: list[dict] = Field(default_factory=list)
    packages_error: str | None = None
    scan_pickup: DriverScanProgress = Field(default_factory=DriverScanProgress)
    scan_delivery: DriverScanProgress = Field(default_factory=DriverScanProgress)
    timeline: list[dict] = Field(default_factory=list)
    photos: list[dict] = Field(default_factory=list)
    signatures: list[dict] = Field(default_factory=list)
    documents: list[dict] = Field(default_factory=list)
    proof_of_delivery: dict = Field(default_factory=dict)
    otp_required: bool = False
    pod_requirements: dict = Field(default_factory=dict)
    pod_missing: list[str] = Field(default_factory=list)
    on_duty: bool = True
    incidents: list[dict] = Field(default_factory=list)
    amount_cents: int = 0
    currency: str = "cad"
    cod_amount_cents: int | None = None
    cod_status: str | None = None
    updated_at: str | None = None
    pickup_stop_id: str | None = None
    delivery_stop_id: str | None = None
    delivery_attempts: int = 0
    max_delivery_attempts: int = 2
    declared_value_cents: int | None = None
    booking_mode: str | None = None
    vehicle_class: str | None = None


class DriverDevLoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)


class DriverDevLoginResponse(BaseModel):
    driver_id: str
    email: str
    full_name: str
    status: str


class DriverDevListItem(BaseModel):
    driver_id: str
    email: str
    full_name: str
