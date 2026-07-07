"""Live Operations Map API schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class LiveMapFilters(BaseModel):
    driver_status: list[str] | None = None
    vehicle_type: list[str] | None = None
    merchant_id: str | None = None
    city: str | None = None
    region: str | None = None
    priority: Literal["high", "normal", "all"] | None = "all"
    delivery_status: list[str] | None = None
    date: str | None = None
    service_area: str | None = None
    vehicle_capacity_min_kg: float | None = None
    online_only: bool | None = None


class MapCoordinate(BaseModel):
    lat: float
    lng: float


class LiveMapDriver(BaseModel):
    id: str
    reference: str
    name: str
    photo_url: str | None = None
    phone: str | None = None
    email: str | None = None
    status: str
    availability: str
    online: bool
    vehicle_type: str | None = None
    vehicle_id: str | None = None
    vehicle_plate: str | None = None
    location: MapCoordinate | None = None
    heading: float | None = None
    speed_kmh: float | None = None
    battery_percent: int | None = None
    rating: float | None = None
    current_order_id: str | None = None
    updated_at: datetime | None = None


class LiveMapVehicle(BaseModel):
    id: str
    reference: str
    driver_id: str | None = None
    driver_name: str | None = None
    vehicle_class: str
    plate_number: str
    make_model: str | None = None
    capacity_kg: float | None = None
    status: str
    location: MapCoordinate | None = None
    heading: float | None = None


class LiveMapOrderStop(BaseModel):
    order_id: str
    tracking_number: str
    order_number: str
    stop_type: Literal["pickup", "delivery"]
    state: str
    priority: str
    eta: datetime | None = None
    merchant: str | None = None
    merchant_id: str | None = None
    customer_name: str | None = None
    package_count: int = 1
    vehicle_required: str | None = None
    location: MapCoordinate
    amount_cents: int = 0


class LiveMapMerchant(BaseModel):
    id: str
    reference: str
    name: str
    email: str | None = None
    phone: str | None = None
    location: MapCoordinate | None = None
    city: str | None = None
    status: str


class LiveMapCustomer(BaseModel):
    id: str
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    location: MapCoordinate | None = None


class LiveMapWarehouse(BaseModel):
    id: str
    label: str
    merchant_id: str | None = None
    merchant_name: str | None = None
    address_type: str
    location: MapCoordinate


class LiveMapGeofence(BaseModel):
    id: str
    name: str
    geofence_type: str
    bounds: dict[str, Any]
    is_active: bool = True


class LiveMapAlert(BaseModel):
    id: str
    alert_type: str
    severity: Literal["critical", "warning", "info"]
    title: str
    message: str
    entity_type: str | None = None
    entity_id: str | None = None
    location: MapCoordinate | None = None
    created_at: datetime | None = None


class LiveMapEvent(BaseModel):
    id: str
    event_type: str
    source: str
    title: str
    aggregate_type: str | None = None
    aggregate_id: str | None = None
    occurred_at: datetime | None = None


class CommandCenterStats(BaseModel):
    orders_today: int = 0
    drivers_online: int = 0
    vehicles_active: int = 0
    orders_waiting: int = 0
    late_orders: int = 0
    delayed_drivers: int = 0
    support_tickets: int = 0
    revenue_today_cents: int = 0
    open_claims: int = 0
    open_exceptions: int = 0


class HeatMapPoint(BaseModel):
    lat: float
    lng: float
    weight: float = 1.0


class SmartOpsInsight(BaseModel):
    nearest_drivers: list[LiveMapDriver] = Field(default_factory=list)
    suggested_drivers: list[LiveMapDriver] = Field(default_factory=list)
    delay_predictions: list[dict[str, Any]] = Field(default_factory=list)
    traffic_warnings: list[str] = Field(default_factory=list)
    route_risks: list[dict[str, Any]] = Field(default_factory=list)
    merchant_health: list[dict[str, Any]] = Field(default_factory=list)
    driver_health: list[dict[str, Any]] = Field(default_factory=list)


class LiveMapSnapshot(BaseModel):
    generated_at: datetime
    drivers: list[LiveMapDriver] = Field(default_factory=list)
    vehicles: list[LiveMapVehicle] = Field(default_factory=list)
    orders: list[LiveMapOrderStop] = Field(default_factory=list)
    merchants: list[LiveMapMerchant] = Field(default_factory=list)
    customers: list[LiveMapCustomer] = Field(default_factory=list)
    warehouses: list[LiveMapWarehouse] = Field(default_factory=list)
    geofences: list[LiveMapGeofence] = Field(default_factory=list)
    alerts: list[LiveMapAlert] = Field(default_factory=list)
    events: list[LiveMapEvent] = Field(default_factory=list)
    command_center: CommandCenterStats
    heat_maps: dict[str, list[HeatMapPoint]] = Field(default_factory=dict)
    smart: SmartOpsInsight
    weather: dict[str, Any] = Field(default_factory=dict)


class LiveMapSearchResult(BaseModel):
    type: Literal["driver", "vehicle", "merchant", "customer", "order"]
    id: str
    label: str
    subtitle: str | None = None
    location: MapCoordinate | None = None


class LiveMapEntityDetail(BaseModel):
    entity_type: str
    entity_id: str
    title: str
    subtitle: str | None = None
    status: str | None = None
    location: MapCoordinate | None = None
    contact: dict[str, str | None] = Field(default_factory=dict)
    current_job: dict[str, Any] | None = None
    timeline: list[dict[str, Any]] = Field(default_factory=list)
    eta: datetime | None = None
    notes: list[dict[str, Any]] = Field(default_factory=list)
    actions: list[dict[str, str]] = Field(default_factory=list)
    meta: dict[str, Any] = Field(default_factory=dict)


class PlaybackFrame(BaseModel):
    ts: datetime
    driver_id: str
    lat: float
    lng: float
    heading: float | None = None
    speed_kmh: float | None = None


class PlaybackResponse(BaseModel):
    date: str
    driver_id: str | None = None
    frames: list[PlaybackFrame] = Field(default_factory=list)
    stops: list[dict[str, Any]] = Field(default_factory=list)
    incidents: list[dict[str, Any]] = Field(default_factory=list)
