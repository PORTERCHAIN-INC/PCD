"""Pydantic schemas for driver platform API."""

from datetime import datetime

from pydantic import BaseModel, Field


class DriverLoginRequest(BaseModel):
    email: str
    phone: str | None = None


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
    fleetbase_driver_id: str | None


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
    online: bool


class LocationPingRequest(BaseModel):
    lat: float
    lng: float
    accuracy_m: float | None = None
    heading: float | None = None
    speed_mps: float | None = None


class ExceptionRequest(BaseModel):
    exception_type: str
    notes: str | None = None


class DocumentUploadRequest(BaseModel):
    doc_type: str
    file_url: str
    metadata: dict | None = None


class PodPhotoRequest(BaseModel):
    file_url: str


class PodSignatureRequest(BaseModel):
    signature_data: str


class PodBarcodeRequest(BaseModel):
    barcode: str


class PodOtpRequest(BaseModel):
    otp: str


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


class PushRegisterRequest(BaseModel):
    device_token: str
    platform: str = "expo"


class OfflineActionRequest(BaseModel):
    action_type: str
    payload: dict = Field(default_factory=dict)


class AcceptRejectRequest(BaseModel):
    reason: str | None = None
