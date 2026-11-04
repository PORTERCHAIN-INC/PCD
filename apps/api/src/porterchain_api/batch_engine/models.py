"""Bulk delivery batches: CSV rows -> parcels -> routes/waves -> custody chain."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from porterchain_api.db import Base


class DeliveryBatch(Base):
    __tablename__ = "delivery_batches"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    merchant_id: Mapped[str] = mapped_column(String(36), index=True)
    bulk_job_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(24), default="planned")
    plan: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class BatchRoute(Base):
    __tablename__ = "batch_routes"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    batch_id: Mapped[str] = mapped_column(String(36), index=True)
    route_no: Mapped[int] = mapped_column(Integer)
    wave: Mapped[int] = mapped_column(Integer, default=1)
    vehicle_class: Mapped[str] = mapped_column(String(32))
    driver_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    #: locked (dependent leg) -> awaiting_handover | planned -> pickup_confirmed -> closed; pickup_failed; cancelled
    status: Mapped[str] = mapped_column(String(24), default="planned")
    #: house | shop | warehouse | storage | driver (parcels come from another of our drivers)
    pickup_source: Mapped[str] = mapped_column(String(16), default="shop")
    pickup_point: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    depends_on_route_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    notices: Mapped[list] = mapped_column(JSON, default=list)
    route_plan: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    pickup: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class BatchParcel(Base):
    __tablename__ = "batch_parcels"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    batch_id: Mapped[str] = mapped_column(String(36), index=True)
    route_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    #: Collected by this upstream route, then handed to `route_id`'s driver (dependent leg).
    via_route_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    row_no: Mapped[int] = mapped_column(Integer)
    barcode: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    #: Merchant/client labels (Shopify order no., client tracking id) — normalised, linked at import or first scan.
    client_labels: Mapped[list] = mapped_column(JSON, default=list)
    order_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    recipient: Mapped[str | None] = mapped_column(String(160), nullable=True)
    address: Mapped[str] = mapped_column(Text)
    unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    building_key: Mapped[str] = mapped_column(String(200), index=True)
    stop_seq: Mapped[int] = mapped_column(Integer, default=0)
    weight_kg: Mapped[float] = mapped_column(Float, default=0)
    handling: Mapped[list] = mapped_column(JSON, default=list)
    #: pharmacy / high_value / contract -> per-parcel scan at pickup
    scan_required: Mapped[bool] = mapped_column(Boolean, default=False)
    #: manifested, picked_up, delivered, damaged, missing, return_to_depot, reattempt
    status: Mapped[str] = mapped_column(String(24), default="manifested", index=True)
    holder_driver_id: Mapped[str | None] = mapped_column(String(36), nullable=True)


class BatchHandover(Base):
    __tablename__ = "batch_handovers"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    batch_id: Mapped[str] = mapped_column(String(36), index=True)
    from_route_id: Mapped[str] = mapped_column(String(36))
    from_driver_id: Mapped[str] = mapped_column(String(36))
    to_driver_id: Mapped[str] = mapped_column(String(36), index=True)
    to_route_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    parcel_ids: Mapped[list] = mapped_column(JSON, default=list)
    place_kind: Mapped[str] = mapped_column(String(16), default="meeting_point")  # meeting_point | depot
    status: Mapped[str] = mapped_column(String(16), default="pending")  # pending | accepted | cancelled
    give: Mapped[dict] = mapped_column(JSON, default=dict)
    receive: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CustodyEvent(Base):
    __tablename__ = "batch_custody_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    parcel_id: Mapped[str] = mapped_column(String(36), index=True)
    kind: Mapped[str] = mapped_column(String(24))  # pickup, handover_out, handover_in, delivered, return, reattempt
    driver_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    counterpart_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    photo_key: Mapped[str | None] = mapped_column(String(256), nullable=True)
    ref_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class BatchException(Base):
    __tablename__ = "batch_exceptions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    route_id: Mapped[str] = mapped_column(String(36), index=True)
    kind: Mapped[str] = mapped_column(String(24))  # short, extra, damaged, unknown_label, duplicate_scan
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
    driver_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
