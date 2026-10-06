"""Shared types for driver platform services."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class StopView:
    stop_id: str
    order_id: str
    sequence: int
    stop_type: str  # pickup | dropoff
    status: str
    address: dict[str, Any]
    scheduled_at: datetime | None
    tracking_number: str
    order_number: str
    special_instructions: str | None = None
    otp_required: bool = False
    pod_required: bool = True


@dataclass
class RouteView:
    route_id: str
    driver_id: str
    status: str
    stops: list[StopView] = field(default_factory=list)
    route_polyline: str | None = None
    earnings_cents: int = 0
    started_at: datetime | None = None


@dataclass
class DashboardSnapshot:
    driver_id: str
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


@dataclass
class WalletTransactionView:
    id: str
    type: str
    amount_cents: int
    balance_after_cents: int
    description: str
    reference_id: str | None
    created_at: datetime


@dataclass
class PodCaptureResult:
    success: bool
    proof_type: str
    proof_id: str | None
    message: str = ""
