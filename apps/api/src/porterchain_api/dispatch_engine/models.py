"""Dispatch-owned tables: job offers, fleet plans/routes, partners and order legs."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from porterchain_api.db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class DispatchJobOffer(Base):
    """One offer of one order to one driver. Pending offers expire, then pass on."""

    __tablename__ = "dispatch_job_offers"
    __table_args__ = (Index("ix_dispatch_job_offers_order_status", "order_id", "status"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    driver_id: Mapped[str] = mapped_column(ForeignKey("drivers.id", ondelete="CASCADE"), index=True)
    # pending | accepted | declined | expired | cancelled
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True)
    rank: Mapped[int] = mapped_column(Integer, default=1)
    offered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    offered_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    meta: Mapped[dict] = mapped_column(JSON, default=dict)


class DispatchPlan(Base):
    """One solve of the day. Draft until an admin commits it; re-plans supersede."""

    __tablename__ = "dispatch_plans"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    service_date: Mapped[date] = mapped_column(Date, index=True)
    # draft | committed | superseded | discarded
    status: Mapped[str] = mapped_column(String(16), default="draft", index=True)
    solver: Mapped[str] = mapped_column(String(16), default="ortools")
    version: Mapped[int] = mapped_column(Integer, default=1)
    parent_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    summary: Mapped[dict] = mapped_column(JSON, default=dict)
    created_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    committed_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    committed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class DispatchRoute(Base):
    """One vehicle's ordered stops inside a plan (stops JSON: key, order, kind, FSA, ETA)."""

    __tablename__ = "dispatch_routes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    plan_id: Mapped[str] = mapped_column(ForeignKey("dispatch_plans.id", ondelete="CASCADE"), index=True)
    vehicle_id: Mapped[str] = mapped_column(String(64))
    driver_id: Mapped[str | None] = mapped_column(ForeignKey("drivers.id", ondelete="SET NULL"), nullable=True, index=True)
    vehicle_class: Mapped[str] = mapped_column(String(32))
    stops: Mapped[list] = mapped_column(JSON, default=list)
    seconds: Mapped[int] = mapped_column(Integer, default=0)
    cost_cents: Mapped[int] = mapped_column(Integer, default=0)
    fill_pct: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(16), default="draft")


class LogisticsPartner(Base):
    """Warehouse, FTL/LTL linehaul or 3PL final-mile partner (business data, no personal data)."""

    __tablename__ = "logistics_partners"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(128))
    # warehouse | ftl | ltl | 3pl
    kind: Mapped[str] = mapped_column(String(16), index=True)
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    fsa_coverage: Mapped[list] = mapped_column(JSON, default=list)  # FSA prefixes, e.g. ["K", "H3"]
    rate_per_kg_cents: Mapped[int] = mapped_column(Integer, default=0)
    min_charge_cents: Mapped[int] = mapped_column(Integer, default=0)
    transit_days: Mapped[int] = mapped_column(Integer, default=1)
    cutoff_local: Mapped[str | None] = mapped_column(String(5), nullable=True)  # "15:00"
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)  # partner ops desk
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class OrderLeg(Base):
    """One leg of an order's journey: local van, warehouse hold, FTL/LTL linehaul or 3PL."""

    __tablename__ = "order_legs"
    __table_args__ = (Index("ix_order_legs_order_seq", "order_id", "seq"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    seq: Mapped[int] = mapped_column(Integer, default=0)
    # local | warehouse | ftl | ltl | 3pl
    mode: Mapped[str] = mapped_column(String(16))
    partner_id: Mapped[str | None] = mapped_column(
        ForeignKey("logistics_partners.id", ondelete="SET NULL"), nullable=True, index=True
    )
    from_label: Mapped[str] = mapped_column(String(64), default="")
    to_label: Mapped[str] = mapped_column(String(64), default="")
    # planned | requested | accepted | picked_up | delivered | cancelled
    status: Mapped[str] = mapped_column(String(16), default="planned", index=True)
    est_cost_cents: Mapped[int] = mapped_column(Integer, default=0)
    meta: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DispatchStopEvent(Base):
    """Driver check-in at one plan stop: arrived, picked_up, delivered or failed, with GPS."""

    __tablename__ = "dispatch_stop_events"
    __table_args__ = (Index("ix_dispatch_stop_events_route_key", "route_id", "stop_key"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    route_id: Mapped[str | None] = mapped_column(
        ForeignKey("dispatch_routes.id", ondelete="SET NULL"), nullable=True, index=True
    )
    stop_key: Mapped[str] = mapped_column(String(96), index=True)
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    driver_id: Mapped[str] = mapped_column(ForeignKey("drivers.id", ondelete="CASCADE"), index=True)
    # arrived | picked_up | delivered | failed
    event: Mapped[str] = mapped_column(String(16), index=True)
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    accuracy_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
