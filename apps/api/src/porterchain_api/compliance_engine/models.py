"""Doc 80 vehicle compliance tables (Ontario, Phase 0: Civic + rentals, no owned fleet)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from porterchain_api.db import Base


class VehicleTrip(Base):
    """Vehicle record per trip (70 §2.3 dispatch.trips columns). A trip cannot start without it."""

    __tablename__ = "compliance_vehicle_trips"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    driver_id: Mapped[str] = mapped_column(String(36), index=True)
    plate: Mapped[str] = mapped_column(String(16))
    jurisdiction: Mapped[str] = mapped_column(String(4), default="ON")
    vin: Mapped[str | None] = mapped_column(String(17), nullable=True)
    is_rental: Mapped[bool] = mapped_column(Boolean, default=False)
    rental_agreement_ref: Mapped[str | None] = mapped_column(String(64), nullable=True)
    rental_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rgw_kg: Mapped[int] = mapped_column(Integer)
    gvwr_kg: Mapped[int | None] = mapped_column(Integer, nullable=True)
    curb_kg: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cvor_required: Mapped[bool] = mapped_column(Boolean, default=False)
    insurance_evidence_ref: Mapped[str | None] = mapped_column(String(128), nullable=True)
    maintenance_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    inspection_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    declared_kg: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(16), default="draft")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DvirReport(Base):
    """Daily inspection report (O. Reg. 199/07 s. 7(1)); valid 24 h; kept 6 months."""

    __tablename__ = "compliance_dvir_reports"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    client_id: Mapped[str | None] = mapped_column(String(36), unique=True, nullable=True)
    driver_id: Mapped[str] = mapped_column(String(36), index=True)
    trip_id: Mapped[str | None] = mapped_column(String(36), index=True, nullable=True)
    plate: Mapped[str] = mapped_column(String(16))
    jurisdiction: Mapped[str] = mapped_column(String(4), default="ON")
    operator_name: Mapped[str] = mapped_column(String(128))
    inspected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    location: Mapped[str] = mapped_column(String(255))
    inspector_name: Mapped[str] = mapped_column(String(128))
    odometer_km: Mapped[int] = mapped_column(Integer)
    kind: Mapped[str] = mapped_column(String(16), default="schedule1")  # schedule1 | walkaround
    items: Mapped[dict] = mapped_column(JSON, default=dict)
    defects: Mapped[list] = mapped_column(JSON, default=list)
    major_defect: Mapped[bool] = mapped_column(Boolean, default=False)
    signed_statement: Mapped[bool] = mapped_column(Boolean, default=False)
    photos: Mapped[list | None] = mapped_column(JSON, nullable=True)
    retain_until: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class HosEvent(Base):
    """Phone HOS log event; ``at`` is the phone clock at the event and is never rewritten on sync."""

    __tablename__ = "compliance_hos_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    client_id: Mapped[str | None] = mapped_column(String(36), unique=True, nullable=True)
    driver_id: Mapped[str] = mapped_column(String(36), index=True)
    status: Mapped[str] = mapped_column(String(12))  # on_duty | driving | off_duty
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    other_operator_today: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    start_location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
