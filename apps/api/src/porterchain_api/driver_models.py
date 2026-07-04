"""Driver platform persistence models."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from porterchain_api.db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class DriverWalletTransaction(Base):
    __tablename__ = "driver_wallet_transactions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    driver_id: Mapped[str] = mapped_column(ForeignKey("drivers.id"), index=True)
    tx_type: Mapped[str] = mapped_column(String(32), index=True)
    amount_cents: Mapped[int] = mapped_column(Integer)
    balance_after_cents: Mapped[int] = mapped_column(Integer)
    reference_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DriverBonus(Base):
    __tablename__ = "driver_bonuses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    driver_id: Mapped[str] = mapped_column(ForeignKey("drivers.id"), index=True)
    title: Mapped[str] = mapped_column(String(128))
    amount_cents: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(32), default="available", index=True)
    criteria: Mapped[dict] = mapped_column(JSON, default=dict)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DriverLocationPing(Base):
    __tablename__ = "driver_location_pings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    driver_id: Mapped[str] = mapped_column(ForeignKey("drivers.id"), index=True)
    lat: Mapped[float] = mapped_column(Float)
    lng: Mapped[float] = mapped_column(Float)
    accuracy_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    heading: Mapped[float | None] = mapped_column(Float, nullable=True)
    speed_mps: Mapped[float | None] = mapped_column(Float, nullable=True)
    source: Mapped[str] = mapped_column(String(32), default="app")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DriverIncident(Base):
    __tablename__ = "driver_incidents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    driver_id: Mapped[str] = mapped_column(ForeignKey("drivers.id"), index=True)
    order_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    incident_type: Mapped[str] = mapped_column(String(64), index=True)
    description: Mapped[str] = mapped_column(Text)
    location: Mapped[dict] = mapped_column(JSON, default=dict)
    evidence: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(32), default="open", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DriverOfflineAction(Base):
    __tablename__ = "driver_offline_actions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    driver_id: Mapped[str] = mapped_column(ForeignKey("drivers.id"), index=True)
    action_type: Mapped[str] = mapped_column(String(64), index=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DriverStopMeta(Base):
    __tablename__ = "driver_stop_meta"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    order_id: Mapped[str] = mapped_column(String(36), unique=True, index=True)
    driver_id: Mapped[str] = mapped_column(String(36), index=True)
    meta: Mapped[dict] = mapped_column(JSON, default=dict)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class DriverShift(Base):
    __tablename__ = "driver_shifts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    driver_id: Mapped[str] = mapped_column(ForeignKey("drivers.id"), index=True)
    status: Mapped[str] = mapped_column(String(32), default="active", index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    break_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    vehicle_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    route_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    mileage_km: Mapped[float] = mapped_column(Float, default=0.0)
    break_minutes: Mapped[int] = mapped_column(Integer, default=0)
    meta: Mapped[dict] = mapped_column(JSON, default=dict)


class DriverShiftActivity(Base):
    __tablename__ = "driver_shift_activities"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    shift_id: Mapped[str | None] = mapped_column(ForeignKey("driver_shifts.id"), nullable=True, index=True)
    driver_id: Mapped[str] = mapped_column(ForeignKey("drivers.id"), index=True)
    activity_type: Mapped[str] = mapped_column(String(64), index=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
