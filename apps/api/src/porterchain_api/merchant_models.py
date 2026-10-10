import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from porterchain_api.db import Base
from porterchain_api.domain.merchant_states import MerchantStatus


def _uuid() -> str:
    return str(uuid.uuid4())


class Merchant(Base):
    __tablename__ = "merchants"
    __table_args__ = (
        CheckConstraint("pricing_model IN ('fsa', 'distance')", name="ck_merchants_pricing_model"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    status: Mapped[str] = mapped_column(String(32), default=MerchantStatus.PENDING.value, index=True)
    company_name: Mapped[str] = mapped_column(String(255))
    legal_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    clerk_org_id: Mapped[str | None] = mapped_column(String(128), unique=True, nullable=True, index=True)
    parent_merchant_id: Mapped[str | None] = mapped_column(
        ForeignKey("merchants.id"), nullable=True, index=True
    )
    email: Mapped[str] = mapped_column(String(320), index=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    payment_terms: Mapped[str] = mapped_column(String(16), default="NET_30")
    billing_cycle: Mapped[str] = mapped_column(String(16), default="MONTHLY")
    credit_limit_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    stripe_connect_account_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    cod_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    hst_number: Mapped[str | None] = mapped_column(String(32), nullable=True)
    business_number: Mapped[str | None] = mapped_column(String(32), nullable=True)
    website: Mapped[str | None] = mapped_column(String(512), nullable=True)
    industry: Mapped[str | None] = mapped_column(String(128), nullable=True)
    stripe_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    billing_address: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    profile: Mapped[dict] = mapped_column(JSON, default=dict)
    pricing_config: Mapped[dict] = mapped_column(JSON, default=dict)
    # SoT for merchant rate plan. pricing_config keeps surcharges + size_tiers only.
    pricing_model: Mapped[str] = mapped_column(String(16), default="distance", index=True)
    preferred_vehicles: Mapped[list | None] = mapped_column(JSON, nullable=True)
    delivery_zones: Mapped[list | None] = mapped_column(JSON, nullable=True)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    users: Mapped[list["MerchantUser"]] = relationship(back_populates="merchant")
    saved_addresses: Mapped[list["SavedAddress"]] = relationship(back_populates="merchant")
    recipients: Mapped[list["MerchantRecipient"]] = relationship(back_populates="merchant")
    api_keys: Mapped[list["MerchantApiKey"]] = relationship(back_populates="merchant")
    webhooks: Mapped[list["MerchantWebhook"]] = relationship(back_populates="merchant")
    bulk_imports: Mapped[list["BulkImportJob"]] = relationship(back_populates="merchant")
    audit_logs: Mapped[list["MerchantAuditLog"]] = relationship(back_populates="merchant")
    shopify_shops: Mapped[list["ShopifyShop"]] = relationship(back_populates="merchant")


class MerchantUser(Base):
    __tablename__ = "merchant_users"
    __table_args__ = (
        # M-26: same Clerk subject may hold seats on multiple merchants.
        UniqueConstraint("clerk_user_id", "merchant_id", name="uq_merchant_users_clerk_merchant"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    merchant_id: Mapped[str] = mapped_column(ForeignKey("merchants.id"), index=True)
    clerk_user_id: Mapped[str] = mapped_column(String(128), index=True)
    # Phase 8 — internal UUID FK (nullable until backfill); clerk_user_id retained
    porterchain_user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("porterchain_users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    email: Mapped[str] = mapped_column(String(320))
    role: Mapped[str] = mapped_column(String(32), default="merchant_ops")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    merchant: Mapped[Merchant] = relationship(back_populates="users")


class SavedAddress(Base):
    __tablename__ = "saved_addresses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    merchant_id: Mapped[str] = mapped_column(ForeignKey("merchants.id"), index=True)
    label: Mapped[str] = mapped_column(String(128))
    address_type: Mapped[str] = mapped_column(String(32), default="pickup")
    formatted: Mapped[str] = mapped_column(String(512))
    place_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    lat: Mapped[float | None] = mapped_column(nullable=True)
    lng: Mapped[float | None] = mapped_column(nullable=True)
    postal: Mapped[str | None] = mapped_column(String(16), nullable=True)
    address_id: Mapped[str | None] = mapped_column(ForeignKey("addresses.id"), nullable=True, index=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    merchant: Mapped[Merchant] = relationship(back_populates="saved_addresses")


class MerchantRecipient(Base):
    __tablename__ = "merchant_recipients"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    merchant_id: Mapped[str] = mapped_column(ForeignKey("merchants.id"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    company: Mapped[str | None] = mapped_column(String(255), nullable=True)
    default_address: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    merchant: Mapped[Merchant] = relationship(back_populates="recipients")


class MerchantApiKey(Base):
    __tablename__ = "merchant_api_keys"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    merchant_id: Mapped[str] = mapped_column(ForeignKey("merchants.id"), index=True)
    name: Mapped[str] = mapped_column(String(128))
    key_prefix: Mapped[str] = mapped_column(String(16), index=True)
    key_hash: Mapped[str] = mapped_column(String(128))
    scopes: Mapped[list] = mapped_column(JSON, default=list)
    environment: Mapped[str] = mapped_column(String(16), default="sandbox")
    rate_limit_per_minute: Mapped[int] = mapped_column(Integer, default=60)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    merchant: Mapped[Merchant] = relationship(back_populates="api_keys")


class MerchantWebhook(Base):
    __tablename__ = "merchant_webhooks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    merchant_id: Mapped[str] = mapped_column(ForeignKey("merchants.id"), index=True)
    url: Mapped[str] = mapped_column(String(512))
    events: Mapped[list] = mapped_column(JSON, default=list)
    secret_hash: Mapped[str] = mapped_column(String(128))
    encrypted_signing_secret: Mapped[str | None] = mapped_column(String(512), nullable=True)
    # sandbox | production — fanout only delivers matching order.is_sandbox
    environment: Mapped[str] = mapped_column(String(16), default="production", index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    merchant: Mapped[Merchant] = relationship(back_populates="webhooks")
    deliveries: Mapped[list["MerchantWebhookDelivery"]] = relationship(back_populates="webhook")


class MerchantApiUsageLog(Base):
    __tablename__ = "merchant_api_usage_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    merchant_id: Mapped[str] = mapped_column(ForeignKey("merchants.id"), index=True)
    api_key_id: Mapped[str] = mapped_column(ForeignKey("merchant_api_keys.id"), index=True)
    method: Mapped[str] = mapped_column(String(16))
    path: Mapped[str] = mapped_column(String(255), index=True)
    status_code: Mapped[int] = mapped_column(Integer, default=200)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    environment: Mapped[str] = mapped_column(String(16), default="sandbox")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


class MerchantWebhookDelivery(Base):
    __tablename__ = "merchant_webhook_deliveries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    merchant_id: Mapped[str] = mapped_column(ForeignKey("merchants.id"), index=True)
    webhook_id: Mapped[str] = mapped_column(ForeignKey("merchant_webhooks.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(128), index=True)
    request_body: Mapped[dict] = mapped_column(JSON, default=dict)
    response_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempt: Mapped[int] = mapped_column(Integer, default=1)
    success: Mapped[bool] = mapped_column(Boolean, default=False)
    error_message: Mapped[str | None] = mapped_column(String(512), nullable=True)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    webhook: Mapped[MerchantWebhook] = relationship(back_populates="deliveries")


class BulkImportJob(Base):
    __tablename__ = "bulk_import_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    merchant_id: Mapped[str] = mapped_column(ForeignKey("merchants.id"), index=True)
    status: Mapped[str] = mapped_column(String(32), default="UPLOADED", index=True)
    kind: Mapped[str] = mapped_column(String(32), default="classic", index=True)
    filename: Mapped[str] = mapped_column(String(255))
    total_rows: Mapped[int] = mapped_column(Integer, default=0)
    valid_rows: Mapped[int] = mapped_column(Integer, default=0)
    error_rows: Mapped[int] = mapped_column(Integer, default=0)
    duplicate_rows: Mapped[int] = mapped_column(Integer, default=0)
    preview: Mapped[list] = mapped_column(JSON, default=list)
    errors: Mapped[list] = mapped_column(JSON, default=list)
    order_ids: Mapped[list] = mapped_column(JSON, default=list)
    job_config: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    merchant: Mapped[Merchant] = relationship(back_populates="bulk_imports")


class MerchantAuditLog(Base):
    __tablename__ = "merchant_audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    merchant_id: Mapped[str] = mapped_column(ForeignKey("merchants.id"), index=True)
    actor_user_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    action: Mapped[str] = mapped_column(String(64), index=True)
    resource_type: Mapped[str] = mapped_column(String(32))
    resource_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    merchant: Mapped[Merchant] = relationship(back_populates="audit_logs")


class MerchantBookingTemplate(Base):
    __tablename__ = "merchant_booking_templates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    merchant_id: Mapped[str] = mapped_column(ForeignKey("merchants.id"), index=True)
    name: Mapped[str] = mapped_column(String(128))
    payload: Mapped[dict] = mapped_column(JSON)
    is_recurring: Mapped[bool] = mapped_column(Boolean, default=False)
    recurrence_rule: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class StandingOrder(Base):
    """Recurring merchant bookings materialized by worker cron (§8.1.11)."""

    __tablename__ = "standing_orders"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    merchant_id: Mapped[str] = mapped_column(ForeignKey("merchants.id"), index=True)
    booking_template_id: Mapped[str] = mapped_column(ForeignKey("merchant_booking_templates.id"), index=True)
    recurrence_rule: Mapped[str] = mapped_column(String(64), default="weekly")
    next_run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_order_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ShopifyShop(Base):
    """One Shopify store connected to a PorterChain merchant."""

    __tablename__ = "shopify_shops"
    __table_args__ = (UniqueConstraint("shop_domain", name="uq_shopify_shops_shop_domain"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    merchant_id: Mapped[str] = mapped_column(ForeignKey("merchants.id"), index=True)
    shop_domain: Mapped[str] = mapped_column(String(255), index=True)
    encrypted_access_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Expiring offline token (1 h) + refresh token (90 d). See shopify_tokens.py.
    access_token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    encrypted_refresh_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    refresh_token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # expiring | custom_app | token_reauth_required; NULL = legacy non-expiring token.
    token_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    encrypted_webhook_secret: Mapped[str | None] = mapped_column(String(512), nullable=True)
    default_pickup_address_id: Mapped[str | None] = mapped_column(
        ForeignKey("saved_addresses.id"), nullable=True, index=True
    )
    shopify_shop_gid: Mapped[str | None] = mapped_column(String(128), nullable=True)
    scopes: Mapped[str | None] = mapped_column(String(512), nullable=True)
    installed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    uninstalled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_webhook_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Soft pause: accept webhooks but do not book capacity (≠ force-disconnect).
    ingress_paused: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    # When False, book stays BOOKED until an admin releases it to dispatch.
    # New shops default False (ops release); set True only after onboarding is green.
    auto_dispatch: Mapped[bool] = mapped_column(Boolean, default=False)
    default_vehicle_class: Mapped[str | None] = mapped_column(String(64), nullable=True)
    default_package_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    carrier_service_gid: Mapped[str | None] = mapped_column(String(128), nullable=True)
    fulfillment_service_gid: Mapped[str | None] = mapped_column(String(128), nullable=True)
    location_gid: Mapped[str | None] = mapped_column(String(128), nullable=True)
    # Capped list of X-Shopify-Webhook-Id values. Duplicate deliveries ack without a second book.
    seen_webhook_ids: Mapped[list | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    merchant: Mapped[Merchant] = relationship(back_populates="shopify_shops")


class ShopifyIngressDlq(Base):
    """Failed / held Shopify webhook books — admin ledger + replay source."""

    __tablename__ = "shopify_ingress_dlq"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    merchant_id: Mapped[str] = mapped_column(ForeignKey("merchants.id"), index=True)
    shop_id: Mapped[str | None] = mapped_column(ForeignKey("shopify_shops.id"), nullable=True, index=True)
    shop_domain: Mapped[str] = mapped_column(String(255))
    topic: Mapped[str | None] = mapped_column(String(128), nullable=True)
    action: Mapped[str] = mapped_column(String(64))
    shopify_order_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    reason_code: Mapped[str] = mapped_column(String(64))
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_body: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="open", index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    porterchain_order_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_by_admin_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ShopifyDataSubjectRequest(Base):
    """Shopify GDPR / PIPEDA access or erasure case. Webhook id is the idempotency key."""

    __tablename__ = "shopify_data_subject_requests"
    __table_args__ = (
        UniqueConstraint("shopify_webhook_id", name="uq_shopify_dsr_webhook_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    shop_id: Mapped[str | None] = mapped_column(
        ForeignKey("shopify_shops.id"), nullable=True, index=True
    )
    merchant_id: Mapped[str | None] = mapped_column(
        ForeignKey("merchants.id"), nullable=True, index=True
    )
    topic: Mapped[str] = mapped_column(String(64), index=True)
    shopify_webhook_id: Mapped[str] = mapped_column(String(128))
    shopify_customer_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    email_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    phone_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    orders_requested: Mapped[list | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="received", index=True)
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    export_ciphertext: Mapped[str | None] = mapped_column(Text, nullable=True)
    orders_touched: Mapped[int] = mapped_column(Integer, default=0)
    hold_reason: Mapped[str | None] = mapped_column(String(32), nullable=True)
    fulfilled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ShopifyRateQuote(Base):
    """Checkout CarrierService quote — must match create_shipment for same request_hash."""

    __tablename__ = "shopify_rate_quotes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    shop_id: Mapped[str] = mapped_column(ForeignKey("shopify_shops.id"), index=True)
    merchant_id: Mapped[str] = mapped_column(ForeignKey("merchants.id"), index=True)
    request_hash: Mapped[str] = mapped_column(String(64), index=True)
    total_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(8), default="CAD")
    breakdown: Mapped[dict] = mapped_column(JSON, default=dict)
    pickup_postal: Mapped[str | None] = mapped_column(String(32), nullable=True)
    dropoff_postal: Mapped[str | None] = mapped_column(String(32), nullable=True)
    weight_kg: Mapped[str | None] = mapped_column(String(32), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
