"""Route Center API schemas."""

from typing import Any

from pydantic import BaseModel, Field


class RouteCenterDashboard(BaseModel):
    routes_waiting: int = 0
    routes_planned: int = 0
    routes_optimized: int = 0
    routes_dispatched: int = 0
    routes_active: int = 0
    routes_completed: int = 0
    drivers_available: int = 0
    drivers_busy: int = 0
    vehicles_available: int = 0
    vehicles_busy: int = 0
    orders_waiting: int = 0
    capacity_utilization_pct: float = 0
    todays_distance_km: float = 0
    fuel_estimate_liters: float = 0
    average_eta_minutes: float = 0
    late_routes: int = 0
    on_time_pct: float = 0
    orders_in_flight: int = 0


class RoutePlanCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    order_ids: list[str] = Field(default_factory=list)
    strategy: str = "balanced"
    zone: str | None = None
    template_id: str | None = None


class RoutePlanUpdate(BaseModel):
    name: str | None = None
    order_ids: list[str] | None = None
    stops: list[dict[str, Any]] | None = None
    strategy: str | None = None
    driver_id: str | None = None
    vehicle_id: str | None = None


class RoutePlanMerge(BaseModel):
    plan_ids: list[str] = Field(min_length=2)
    name: str


class RoutePlanSplit(BaseModel):
    groups: list[list[str]] = Field(min_length=2)


class RouteOptimizeRequest(BaseModel):
    strategy: str | None = None
    engine: str = "valhalla"


class RouteDispatchRequest(BaseModel):
    driver_id: str
    vehicle_id: str | None = None
    approve: bool = False


class RouteBulkDispatchRequest(BaseModel):
    plan_ids: list[str]
    driver_id: str


class RouteTemplateSave(BaseModel):
    name: str
    template_type: str = "daily"


class RouteTemplateCreatePlan(BaseModel):
    name: str | None = None
