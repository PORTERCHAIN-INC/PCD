"""Typed health contracts for admin settings + diagnostics."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

HealthTriad = Literal["healthy", "warning", "critical"]


class IntegrationComponent(BaseModel):
    """One integration_health entry — status triad + optional raw probe token."""

    model_config = ConfigDict(extra="allow")

    status: HealthTriad
    raw: str | None = None


class IntegrationHealthResponse(BaseModel):
    """Compact health map for dashboard widget + settings."""

    model_config = ConfigDict(extra="allow")

    api: IntegrationComponent
    database: IntegrationComponent
    redis: IntegrationComponent
    queue: IntegrationComponent | None = None
    stripe: IntegrationComponent | None = None
    fleetbase: IntegrationComponent | None = None
    google_maps: IntegrationComponent | None = None
    firebase: IntegrationComponent | None = None
    clerk: IntegrationComponent | None = None
    storage: IntegrationComponent | None = None
    email: IntegrationComponent | None = None
    sms: IntegrationComponent | None = None
    push: IntegrationComponent | None = None
    nvidia_nim: IntegrationComponent | None = None
    nvidia_cuopt: IntegrationComponent | None = None
    routing: dict[str, Any] | None = None


class HealthComponent(BaseModel):
    """One diagnostics health-dashboard component (Jeff Dean phase_1 reads these)."""

    model_config = ConfigDict(extra="allow")

    id: str
    name: str
    category: str
    status: HealthTriad
    latency_ms: float | None = None
    last_sync: str | None = None
    version: str | None = None
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    recovery_status: str = "none"
    details: dict[str, Any] = Field(default_factory=dict)


class HealthGroupSummary(BaseModel):
    healthy: int = 0
    warning: int = 0
    critical: int = 0


class HealthGroup(BaseModel):
    model_config = ConfigDict(extra="allow")

    label: str
    items: list[HealthComponent] = Field(default_factory=list)
    summary: HealthGroupSummary = Field(default_factory=HealthGroupSummary)


class MasterruleCheck(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    label: str
    status: str
    note: str = ""


class HealthDashboardResponse(BaseModel):
    """Rich System Health payload — freeze shape for phase_1_system_layer."""

    model_config = ConfigDict(extra="allow")

    overall: HealthTriad
    checked_at: str
    version: str
    environment: str
    cached: bool = False
    summary: HealthGroupSummary
    components: list[HealthComponent]
    groups: dict[str, HealthGroup] = Field(default_factory=dict)
    masterrule_compliance: dict[str, Any] = Field(default_factory=dict)
    auth_sli: dict[str, Any] | None = None
    auth_posture: dict[str, Any] | None = None
    cache_age_sec: float | None = None
