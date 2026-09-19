import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from porterchain_api.db import Base
from porterchain_api.domain.admin_states import DriverStatus, TicketStatus


def _uuid() -> str:
    return str(uuid.uuid4())


class AdminUser(Base):
    __tablename__ = "admin_users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    clerk_user_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    # Phase 8 — internal UUID FK (nullable until backfill); clerk_user_id retained
    porterchain_user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("porterchain_users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    email: Mapped[str] = mapped_column(String(320))
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(String(32), default="read_only")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    fleetbase_user_uuid: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    webauthn_credentials: Mapped[list["StaffWebAuthnCredential"]] = relationship(
        "StaffWebAuthnCredential", back_populates="admin_user", cascade="all, delete-orphan"
    )


class StaffWebAuthnCredential(Base):
    """Passkey credentials for staff IdP (WebAuthn)."""

    __tablename__ = "staff_webauthn_credentials"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    admin_user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("admin_users.id", ondelete="CASCADE"), index=True
    )
    credential_id: Mapped[str] = mapped_column(String(512), unique=True, index=True)
    public_key: Mapped[str] = mapped_column(Text)
    sign_count: Mapped[int] = mapped_column(Integer, default=0)
    device_label: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    admin_user: Mapped[AdminUser] = relationship("AdminUser", back_populates="webauthn_credentials")


class Driver(Base):
    __tablename__ = "drivers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    status: Mapped[str] = mapped_column(String(32), default=DriverStatus.PENDING.value, index=True)
    clerk_user_id: Mapped[str | None] = mapped_column(String(128), nullable=True, unique=True, index=True)
    # Phase 8 — internal UUID FK (nullable until backfill); clerk_user_id retained
    porterchain_user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("porterchain_users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    email: Mapped[str] = mapped_column(String(320), index=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    full_name: Mapped[str] = mapped_column(String(255))
    license_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    medical_transport_certified: Mapped[bool] = mapped_column(Boolean, default=False)
    insurance_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    vehicle_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    background_check_status: Mapped[str] = mapped_column(String(32), default="pending")
    rating: Mapped[float | None] = mapped_column(nullable=True)
    # MIRROR of Fleetbase presence only — live online SoT is Fleetbase (via adapter).
    # Do not treat this column as dispatch authority.
    is_online: Mapped[bool] = mapped_column(Boolean, default=False)
    availability: Mapped[str] = mapped_column(String(32), default="offline")
    wallet_balance_cents: Mapped[int] = mapped_column(Integer, default=0)
    fleetbase_driver_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    documents: Mapped[dict] = mapped_column(JSON, default=dict)
    performance: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    vehicles: Mapped[list["Vehicle"]] = relationship(back_populates="driver")
    payouts: Mapped[list["DriverPayout"]] = relationship(back_populates="driver")


class Vehicle(Base):
    __tablename__ = "vehicles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    driver_id: Mapped[str | None] = mapped_column(ForeignKey("drivers.id"), nullable=True, index=True)
    vehicle_class: Mapped[str] = mapped_column(String(32))
    plate_number: Mapped[str] = mapped_column(String(32), index=True)
    make_model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    capacity_kg: Mapped[float | None] = mapped_column(nullable=True)
    compliance_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    fleetbase_vehicle_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    driver: Mapped[Driver | None] = relationship(back_populates="vehicles")


class DriverPayout(Base):
    __tablename__ = "driver_payouts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    driver_id: Mapped[str] = mapped_column(ForeignKey("drivers.id"), index=True)
    amount_cents: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(8), default="cad")
    status: Mapped[str] = mapped_column(String(32), default="pending")
    reference: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    driver: Mapped[Driver] = relationship(back_populates="payouts")


class SupportTicket(Base):
    __tablename__ = "support_tickets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    status: Mapped[str] = mapped_column(String(32), default=TicketStatus.OPEN.value, index=True)
    priority: Mapped[str] = mapped_column(String(16), default="normal")
    subject: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    customer_id: Mapped[str | None] = mapped_column(
        ForeignKey("customers.id", ondelete="SET NULL"), nullable=True, index=True
    )
    merchant_id: Mapped[str | None] = mapped_column(
        ForeignKey("merchants.id", ondelete="SET NULL"), nullable=True, index=True
    )
    driver_id: Mapped[str | None] = mapped_column(
        ForeignKey("drivers.id", ondelete="SET NULL"), nullable=True, index=True
    )
    order_id: Mapped[str | None] = mapped_column(
        ForeignKey("orders.id", ondelete="SET NULL"), nullable=True, index=True
    )
    category: Mapped[str] = mapped_column(String(64), default="general_inquiry", index=True)
    ticket_data: Mapped[dict] = mapped_column(JSON, default=dict)
    assigned_to: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Claim(Base):
    __tablename__ = "claims"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    order_id: Mapped[str | None] = mapped_column(
        ForeignKey("orders.id", ondelete="SET NULL"), nullable=True, index=True
    )
    merchant_id: Mapped[str | None] = mapped_column(
        ForeignKey("merchants.id", ondelete="SET NULL"), nullable=True, index=True
    )
    claim_type: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(32), default="open", index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence: Mapped[dict] = mapped_column(JSON, default=dict)
    resolution: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    assigned_to: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PricingTariff(Base):
    __tablename__ = "pricing_tariffs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(128))
    tariff_type: Mapped[str] = mapped_column(String(32), index=True)
    vehicle_class: Mapped[str | None] = mapped_column(String(32), nullable=True)
    zone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    merchant_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    base_cents: Mapped[int] = mapped_column(Integer, default=0)
    per_km_cents: Mapped[int] = mapped_column(Integer, default=0)
    fuel_surcharge_percent: Mapped[float] = mapped_column(default=0.0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Promotion(Base):
    __tablename__ = "promotions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    promotion_type: Mapped[str] = mapped_column(String(32), default="coupon")
    merchant_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    discount_percent: Mapped[float | None] = mapped_column(nullable=True)
    discount_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PricingFsaRate(Base):
    """
    Flat price for delivering into one forward sortation area.

    `merchant_id`, `origin_fsa` and `vehicle_class` are optional filters — NULL
    means "any", so a single-warehouse Shopify store needs only `dest_fsa` and
    `flat_cents`. The most specific matching row wins at quote time.
    """

    __tablename__ = "pricing_fsa_rates"
    __table_args__ = (
        Index(
            "uq_pricing_fsa_rates_scope",
            "merchant_id",
            "origin_fsa",
            "dest_fsa",
            "vehicle_class",
            unique=True,
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    merchant_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    origin_fsa: Mapped[str | None] = mapped_column(String(3), nullable=True)
    dest_fsa: Mapped[str] = mapped_column(String(3), index=True)
    vehicle_class: Mapped[str | None] = mapped_column(String(32), nullable=True)
    flat_cents: Mapped[int] = mapped_column(Integer)
    # When true the flat price already covers downtown / upper-zone fees, so a
    # quote cannot be followed by a surprise geographic surcharge.
    includes_location_fees: Mapped[bool] = mapped_column(Boolean, default=True)
    label: Mapped[str | None] = mapped_column(String(128), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class PricingZone(Base):
    __tablename__ = "pricing_zones"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(128))
    bounds: Mapped[dict] = mapped_column(JSON, default=dict)
    multiplier: Mapped[float] = mapped_column(default=1.0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MerchantContract(Base):
    __tablename__ = "merchant_contracts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    merchant_id: Mapped[str] = mapped_column(ForeignKey("merchants.id"), index=True)
    name: Mapped[str] = mapped_column(String(128))
    rules: Mapped[dict] = mapped_column(JSON, default=dict)
    crm_contract_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    minimum_monthly_commitment_cents: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    effective_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AdminAuditLog(Base):
    __tablename__ = "admin_audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    actor_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    action: Mapped[str] = mapped_column(String(64), index=True)
    resource_type: Mapped[str] = mapped_column(String(32))
    resource_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RouteCenterTemplate(Base):
    """Wholesale / recurring route templates (§8.1.10) — alias: RouteTemplate."""

    __tablename__ = "route_center_templates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(128))
    template_type: Mapped[str] = mapped_column(String(32), default="daily", index=True)
    merchant_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    zone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    schedule: Mapped[dict] = mapped_column(JSON, default=dict)
    stops: Mapped[list] = mapped_column(JSON, default=list)
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# Checklist §8.1.10 wholesale route templates
RouteTemplate = RouteCenterTemplate


class SystemConfig(Base):
    __tablename__ = "system_config"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[dict] = mapped_column(JSON, default=dict)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
