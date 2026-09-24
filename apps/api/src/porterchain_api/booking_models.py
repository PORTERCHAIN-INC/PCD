"""Booking bounded-context ORM models (quotes, orders, payments, customers).

§3.2.1 — canonical home for core shipment/booking tables. Do not re-export via
`porterchain_api.models` (strangler deleted).
"""

import uuid
from datetime import datetime

from decimal import Decimal

from sqlalchemy import event
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from porterchain_api.db import Base
from porterchain_api.domain.states import OrderSource, OrderState, OrderType, PaymentTerms, QuoteState


def _uuid() -> str:
    return str(uuid.uuid4())


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    clerk_user_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    # Phase 8 — internal UUID FK (nullable until backfill); clerk_user_id retained
    porterchain_user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("porterchain_users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    email: Mapped[str] = mapped_column(String(320), index=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    visitor_session_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    customer_reference: Mapped[str | None] = mapped_column(String(32), nullable=True, unique=True, index=True)
    # C-18: durable Stripe Customer id for saved PM / Admin 360.
    stripe_customer_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    # GDPR / DSAR — deletion_hold blocks Admin wipe during SLA window (C-19).
    privacy_status: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    privacy_hold_reference: Mapped[str | None] = mapped_column(String(64), nullable=True)
    privacy_hold_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    quotes: Mapped[list["Quote"]] = relationship(back_populates="customer")
    orders: Mapped[list["Order"]] = relationship(back_populates="customer")
    bookings: Mapped[list["Booking"]] = relationship(back_populates="customer")
    payments: Mapped[list["Payment"]] = relationship(back_populates="customer")
    invoices: Mapped[list["Invoice"]] = relationship(back_populates="customer")


class VisitorSession(Base):
    __tablename__ = "visitor_sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    ip_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    browser: Mapped[str | None] = mapped_column(String(128), nullable=True)
    utm_source: Mapped[str | None] = mapped_column(String(128), nullable=True)
    utm_medium: Mapped[str | None] = mapped_column(String(128), nullable=True)
    utm_campaign: Mapped[str | None] = mapped_column(String(128), nullable=True)
    referrer: Mapped[str | None] = mapped_column(String(512), nullable=True)
    device: Mapped[str | None] = mapped_column(String(64), nullable=True)
    location: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # First-party journey / intent bag (paths, landing, guide stage, etc.)
    signals: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    touch_count: Mapped[int] = mapped_column(Integer, default=0)
    intent_score: Mapped[int] = mapped_column(Integer, default=0)
    quote_generated: Mapped[bool] = mapped_column(default=False)
    last_quote_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    customer_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Quote(Base):
    __tablename__ = "quotes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    state: Mapped[str] = mapped_column(String(32), default=QuoteState.QUOTE.value, index=True)
    anonymous_session_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    customer_id: Mapped[str | None] = mapped_column(ForeignKey("customers.id"), nullable=True)
    pickup: Mapped[dict] = mapped_column(JSON)
    dropoff: Mapped[dict] = mapped_column(JSON)
    vehicle_class: Mapped[str] = mapped_column(String(32))
    package_type: Mapped[str] = mapped_column(String(64))
    weight_kg: Mapped[float | None] = mapped_column(nullable=True)
    dimensions: Mapped[str | None] = mapped_column(String(128), nullable=True)
    declared_value_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    additional_stops: Mapped[list | None] = mapped_column(JSON, nullable=True)
    special_instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    visitor_session_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    schedule_mode: Mapped[str] = mapped_column(String(16), default="now")
    amount_cents: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(8), default="cad")
    pricing_breakdown: Mapped[dict] = mapped_column(JSON)
    distance_meters: Mapped[int | None] = mapped_column(Integer, nullable=True)
    parcels: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    consent: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    stripe_checkout_session_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    customer: Mapped[Customer | None] = relationship(back_populates="quotes")
    order: Mapped["Order | None"] = relationship(back_populates="quote", uselist=False)
    booking: Mapped["Booking | None"] = relationship(back_populates="quote", uselist=False)


class Booking(Base):
    __tablename__ = "bookings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    booking_number: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    state: Mapped[str] = mapped_column(String(32), default="BOOKED", index=True)
    quote_id: Mapped[str] = mapped_column(ForeignKey("quotes.id"), unique=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id"), index=True)
    order_id: Mapped[str | None] = mapped_column(ForeignKey("orders.id"), nullable=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    quote: Mapped[Quote] = relationship(back_populates="booking")
    customer: Mapped[Customer] = relationship(back_populates="bookings")
    order: Mapped["Order | None"] = relationship(back_populates="booking", uselist=False)


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (
        # One order per (merchant, idempotency key, sandbox flag) so a retried API
        # create cannot become a second job — and sandbox/live keys never collide.
        Index(
            "uq_orders_merchant_idempotency_sandbox",
            "merchant_id",
            "idempotency_key",
            "is_sandbox",
            unique=True,
            postgresql_where=text("idempotency_key IS NOT NULL"),
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    order_number: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    tracking_number: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    state: Mapped[str] = mapped_column(String(32), default=OrderState.BOOKED.value, index=True)
    quote_id: Mapped[str | None] = mapped_column(ForeignKey("quotes.id"), nullable=True, unique=True)
    customer_id: Mapped[str | None] = mapped_column(ForeignKey("customers.id"), nullable=True)
    merchant_id: Mapped[str | None] = mapped_column(ForeignKey("merchants.id", ondelete="RESTRICT"), nullable=True, index=True)
    order_source: Mapped[str] = mapped_column(String(16), default=OrderSource.WEBSITE.value, index=True)
    order_type: Mapped[str] = mapped_column(String(16), default=OrderType.INSTANT.value, index=True)
    payment_terms: Mapped[str] = mapped_column(String(16), default=PaymentTerms.IMMEDIATE.value)
    amount_cents: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(8), default="cad")
    stripe_payment_intent_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    cod_amount_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cod_status: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    cod_stripe_session_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    fleetbase_order_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    assigned_driver_id: Mapped[str | None] = mapped_column(
        ForeignKey("drivers.id", ondelete="SET NULL"), nullable=True, index=True
    )
    pickup: Mapped[dict] = mapped_column(JSON)
    dropoff: Mapped[dict] = mapped_column(JSON)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    internal_reference: Mapped[str | None] = mapped_column(String(128), nullable=True)
    # Caller-supplied dedupe key for programmatic creates (Idempotency-Key header).
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    # Test bookings: no Fleetbase dispatch, no credit/COD, sandbox webhook fanout only.
    is_sandbox: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    purchase_order_number: Mapped[str | None] = mapped_column(String(128), nullable=True)
    cost_centre: Mapped[str | None] = mapped_column(String(64), nullable=True)
    special_instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    compliance_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    sla_deadline_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    quote: Mapped[Quote | None] = relationship(back_populates="order")
    customer: Mapped[Customer | None] = relationship(back_populates="orders")
    booking: Mapped["Booking | None"] = relationship(back_populates="order", uselist=False)
    events: Mapped[list["OrderEvent"]] = relationship(back_populates="order")
    exceptions: Mapped[list["OrderException"]] = relationship(back_populates="order")
    payments: Mapped[list["Payment"]] = relationship(back_populates="order")
    invoices: Mapped[list["Invoice"]] = relationship(back_populates="order")
    stops: Mapped[list["Stop"]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
        order_by="Stop.sequence",
    )
    packages: Mapped[list["Package"]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
        order_by="Package.parcel_index",
    )


class Package(Base):
    """Physical parcel on an order — N packages = N labels / scans (spine 1)."""

    __tablename__ = "packages"
    __table_args__ = (
        UniqueConstraint("order_id", "parcel_index", name="uq_packages_order_parcel_index"),
        CheckConstraint("parcel_index >= 1", name="ck_packages_parcel_index_positive"),
        CheckConstraint("parcel_index <= total_parcels", name="ck_packages_parcel_index_le_total"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    order_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("orders.id", ondelete="CASCADE"), index=True
    )
    stop_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    parcel_index: Mapped[int] = mapped_column(Integer)
    total_parcels: Mapped[int] = mapped_column(Integer)
    tracking_suffix: Mapped[str] = mapped_column(Text, unique=True, index=True)
    weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(10, 3), nullable=True)
    dimensions: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="manifested", index=True)
    stop_sequence: Mapped[int | None] = mapped_column(Integer, nullable=True)
    barcode: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True, index=True)
    label_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    signature_required: Mapped[bool] = mapped_column(default=False)
    fleetbase_entity_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    fleetbase_proof_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    order: Mapped[Order] = relationship(back_populates="packages")


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    # Nullable for merchant offline AR settlements (no retail quote).
    quote_id: Mapped[str | None] = mapped_column(ForeignKey("quotes.id"), nullable=True, index=True)
    order_id: Mapped[str | None] = mapped_column(ForeignKey("orders.id"), nullable=True, index=True)
    customer_id: Mapped[str | None] = mapped_column(ForeignKey("customers.id"), nullable=True, index=True)
    invoice_id: Mapped[str | None] = mapped_column(ForeignKey("invoices.id"), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(32), default="PENDING", index=True)
    amount_cents: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(8), default="cad")
    stripe_payment_intent_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    stripe_checkout_session_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    payment_reference: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    payment_method: Mapped[str | None] = mapped_column(String(32), nullable=True)
    transaction_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    receipt_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(String(512), nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    quote: Mapped[Quote | None] = relationship()
    order: Mapped[Order | None] = relationship(back_populates="payments")
    customer: Mapped[Customer | None] = relationship(back_populates="payments")
    invoice: Mapped["Invoice | None"] = relationship(back_populates="payments")


class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    invoice_number: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    receipt_number: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    order_id: Mapped[str | None] = mapped_column(ForeignKey("orders.id"), nullable=True, index=True)
    # Nullable for merchant net-terms invoices (no retail customer).
    customer_id: Mapped[str | None] = mapped_column(ForeignKey("customers.id"), nullable=True, index=True)
    merchant_id: Mapped[str | None] = mapped_column(ForeignKey("merchants.id"), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(32), default="open", index=True)
    amount_cents: Mapped[int] = mapped_column(Integer)
    tax_cents: Mapped[int] = mapped_column(Integer, default=0)
    fees_cents: Mapped[int] = mapped_column(Integer, default=0)
    currency: Mapped[str] = mapped_column(String(8), default="cad")
    stripe_receipt_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    pdf_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    issued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    voided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_reminded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    billing_period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    billing_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    order: Mapped[Order | None] = relationship(back_populates="invoices")
    customer: Mapped[Customer | None] = relationship(back_populates="invoices")
    merchant: Mapped["Merchant | None"] = relationship()
    payments: Mapped[list["Payment"]] = relationship(back_populates="invoice")


class OrderEvent(Base):
    __tablename__ = "order_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    from_state: Mapped[str | None] = mapped_column(String(32), nullable=True)
    to_state: Mapped[str | None] = mapped_column(String(32), nullable=True)
    actor_type: Mapped[str] = mapped_column(String(32), default="system")
    actor_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    order: Mapped[Order] = relationship(back_populates="events")


class DomainEvent(Base):
    """Immutable domain event log per EVENT_FLOW.md."""

    __tablename__ = "domain_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    aggregate_type: Mapped[str] = mapped_column(String(32))
    # Stripe evt_… and other external webhook ids exceed UUID length.
    aggregate_id: Mapped[str] = mapped_column(String(255), index=True)
    correlation_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    actor_type: Mapped[str] = mapped_column(String(32), default="system")
    actor_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    source: Mapped[str] = mapped_column(String(64), default="website_booking")
    email: Mapped[str] = mapped_column(String(320), index=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    quote_id: Mapped[str | None] = mapped_column(ForeignKey("quotes.id"), nullable=True)
    customer_id: Mapped[str | None] = mapped_column(ForeignKey("customers.id"), nullable=True)
    crm_lead_id: Mapped[str | None] = mapped_column(
        ForeignKey("crm_leads.id", ondelete="SET NULL"), nullable=True, index=True
    )
    stage: Mapped[str] = mapped_column(String(32), default="new")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AbandonedCheckout(Base):
    __tablename__ = "abandoned_checkouts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    quote_id: Mapped[str] = mapped_column(String(36), index=True)
    customer_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    email: Mapped[str] = mapped_column(String(320))
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    stripe_checkout_session_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reason: Mapped[str] = mapped_column(String(64), default="session_expired")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class OrderException(Base):
    __tablename__ = "order_exceptions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id"), index=True)
    type: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(32), default="open")
    reported_by_type: Mapped[str] = mapped_column(String(32))
    reported_by_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    evidence: Mapped[dict] = mapped_column(JSON, default=dict)
    resolution: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    order: Mapped[Order] = relationship(back_populates="exceptions")


class StripeWebhookEvent(Base):
    """Processed Stripe webhook events — durable idempotency (DD-23, §2.5.3)."""

    __tablename__ = "stripe_webhook_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    stripe_event_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    event_type: Mapped[str] = mapped_column(String(128), index=True)
    status: Mapped[str] = mapped_column(String(32), default="processing")
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Address(Base):
    """Shared stop/consignee address — commercial geography, not Fleetbase."""

    __tablename__ = "addresses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    formatted: Mapped[str] = mapped_column(String(512))
    line1: Mapped[str | None] = mapped_column(String(255), nullable=True)
    city: Mapped[str | None] = mapped_column(String(128), nullable=True)
    region: Mapped[str | None] = mapped_column(String(64), nullable=True)
    postal: Mapped[str | None] = mapped_column(String(16), nullable=True, index=True)
    country: Mapped[str] = mapped_column(String(8), default="CA")
    lat: Mapped[float | None] = mapped_column(nullable=True)
    lng: Mapped[float | None] = mapped_column(nullable=True)
    place_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Stop(Base):
    """Pickup / drop / extra stop on an order. Execution pointer lives on fleetbase_stop_id."""

    __tablename__ = "stops"
    __table_args__ = (Index("ix_stops_order_sequence", "order_id", "sequence"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    sequence: Mapped[int] = mapped_column(Integer, default=0)
    kind: Mapped[str] = mapped_column(String(16), default="drop", index=True)
    address_id: Mapped[str | None] = mapped_column(ForeignKey("addresses.id"), nullable=True, index=True)
    window_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    window_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    fleetbase_stop_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    order: Mapped[Order] = relationship(back_populates="stops")
    address: Mapped[Address | None] = relationship()


def _stamp_order_sla(_mapper, _connection, target: Order) -> None:
    from porterchain_api.booking_engine.order_sla import stamp_sla_deadline

    stamp_sla_deadline(target)


event.listen(Order, "before_insert", _stamp_order_sla)
event.listen(Order, "before_update", _stamp_order_sla)
