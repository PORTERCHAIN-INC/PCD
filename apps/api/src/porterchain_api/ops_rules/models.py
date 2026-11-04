"""F3 location graph (buildings, units, access notes) + driver equipment tags + safety reports."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from porterchain_api.db import Base


class Location(Base):
    __tablename__ = "locations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    #: address | building | shop | depot | partner_hub | locker
    kind: Mapped[str] = mapped_column(String(24), default="building")
    building_key: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    address: Mapped[str] = mapped_column(Text)
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    access_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    hours: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    geofence_m: Mapped[float] = mapped_column(Float, default=75)
    #: e.g. {"unsafe": {...}} set by a safety stop; drivers are warned on approach.
    flags: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class LocationUnit(Base):
    __tablename__ = "location_units"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    location_id: Mapped[str] = mapped_column(String(36), index=True)
    unit: Mapped[str] = mapped_column(String(32))
    access_notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class DriverEquipment(Base):
    __tablename__ = "driver_equipment"
    driver_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tags: Mapped[list] = mapped_column(JSON, default=list)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class SafetyReport(Base):
    __tablename__ = "safety_reports"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    code: Mapped[str] = mapped_column(String(40), index=True)
    driver_id: Mapped[str] = mapped_column(String(36), index=True)
    order_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    route_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    location_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    parcels: Mapped[list] = mapped_column(JSON, default=list)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    photo_keys: Mapped[list] = mapped_column(JSON, default=list)
    police_report_no: Mapped[str | None] = mapped_column(String(64), nullable=True)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
