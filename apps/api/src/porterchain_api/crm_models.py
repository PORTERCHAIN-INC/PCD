"""Porterchain Merchant CRM — SQLAlchemy models.

A logistics-specific CRM: companies (merchant prospects), their contacts,
inbound leads, the sales pipeline (deals), quotations, contracts, and the
activity timeline. Designed so every inquiry can be converted into an
active Porterchain merchant.
"""

import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from porterchain_api.db import Base
from porterchain_api.domain.crm_states import (
    CompanyMerchantStatus,
    ContractStatus,
    DealStage,
    LeadDecisionStatus,
    LeadIntentType,
    LeadPriority,
    LeadSourceChannel,
    LeadStatus,
    QuotationStatus,
)


def _uuid() -> str:
    return str(uuid.uuid4())


class CrmCompany(Base):
    """A logistics merchant prospect / account."""

    __tablename__ = "crm_companies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    legal_name: Mapped[str] = mapped_column(String(255), index=True)
    operating_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    business_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    hst_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    industry: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    business_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    website: Mapped[str | None] = mapped_column(String(512), nullable=True)
    linkedin_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    logo_url: Mapped[str | None] = mapped_column(String(512), nullable=True)

    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True, index=True)

    address: Mapped[dict] = mapped_column(JSONB, default=dict)
    branches: Mapped[list] = mapped_column(JSON, default=list)
    warehouse_locations: Mapped[list] = mapped_column(JSON, default=list)
    pickup_locations: Mapped[list] = mapped_column(JSON, default=list)
    billing_details: Mapped[dict] = mapped_column(JSON, default=dict)

    # Logistics qualification signals.
    estimated_deliveries_per_month: Mapped[int | None] = mapped_column(Integer, nullable=True)
    estimated_monthly_revenue_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    preferred_vehicle: Mapped[str | None] = mapped_column(String(64), nullable=True)
    service_area: Mapped[str | None] = mapped_column(String(255), nullable=True)
    current_logistics_provider: Mapped[str | None] = mapped_column(String(255), nullable=True)

    merchant_status: Mapped[str] = mapped_column(
        String(32), default=CompanyMerchantStatus.LEAD.value, index=True
    )
    merchant_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)

    owner_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    tags: Mapped[list] = mapped_column(JSON, default=list)
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False)
    is_favorite: Mapped[bool] = mapped_column(Boolean, default=False)
    custom_fields: Mapped[dict] = mapped_column(JSONB, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    contacts: Mapped[list["CrmContact"]] = relationship(
        back_populates="company", cascade="all, delete-orphan"
    )
    deals: Mapped[list["CrmDeal"]] = relationship(back_populates="company")


class CrmContact(Base):
    """A person at a merchant company. Companies support unlimited contacts."""

    __tablename__ = "crm_contacts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    company_id: Mapped[str | None] = mapped_column(
        ForeignKey("crm_companies.id"), nullable=True, index=True
    )
    first_name: Mapped[str] = mapped_column(String(128))
    last_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    designation: Mapped[str | None] = mapped_column(String(128), nullable=True)
    department: Mapped[str | None] = mapped_column(String(128), nullable=True)

    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    mobile: Mapped[str | None] = mapped_column(String(32), nullable=True)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True, index=True)
    linkedin: Mapped[str | None] = mapped_column(String(512), nullable=True)
    birthday: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Roles like decision_maker, accounts_payable, warehouse_manager, ...
    roles: Mapped[list] = mapped_column(JSON, default=list)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    company: Mapped[CrmCompany | None] = relationship(back_populates="contacts")


class CrmLead(Base):
    """An inbound business inquiry. Every inquiry becomes a lead."""

    __tablename__ = "crm_leads"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    company_name: Mapped[str] = mapped_column(String(255), index=True)
    industry: Mapped[str | None] = mapped_column(String(128), nullable=True)
    website: Mapped[str | None] = mapped_column(String(512), nullable=True)
    business_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    address: Mapped[dict] = mapped_column(JSONB, default=dict)

    primary_contact_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True, index=True)
    quote_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    # First-class visitor spine (was custom_fields.visitor_id / session_id).
    visitor_session_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    booking_draft_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)

    estimated_deliveries_per_month: Mapped[int | None] = mapped_column(Integer, nullable=True)
    estimated_revenue_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    preferred_vehicle: Mapped[str | None] = mapped_column(String(64), nullable=True)
    service_area: Mapped[str | None] = mapped_column(String(255), nullable=True)
    current_logistics_provider: Mapped[str | None] = mapped_column(String(255), nullable=True)

    source: Mapped[str] = mapped_column(String(64), default="website", index=True)
    channel: Mapped[str] = mapped_column(
        String(64), default=LeadSourceChannel.WEBSITE.value, index=True
    )
    intent_type: Mapped[str] = mapped_column(
        String(32), default=LeadIntentType.MERCHANT.value, index=True
    )
    decision_status: Mapped[str] = mapped_column(
        String(32), default=LeadDecisionStatus.NEW.value, index=True
    )
    status: Mapped[str] = mapped_column(String(32), default=LeadStatus.NEW.value, index=True)
    priority: Mapped[str] = mapped_column(String(16), default=LeadPriority.MEDIUM.value)
    assigned_to: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    expected_close_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    tags: Mapped[list] = mapped_column(JSON, default=list)
    internal_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    lead_score: Mapped[int] = mapped_column(Integer, default=0)

    company_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    deal_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    contact_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    referred_by_merchant_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    merge_candidate_of: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)

    sla_first_response_due_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_touch_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    consent: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Flexible storage so any CSV column / ad-hoc attribute can live on a lead.
    custom_fields: Mapped[dict] = mapped_column(JSONB, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class CrmDeal(Base):
    """A sales opportunity moving through the pipeline."""

    __tablename__ = "crm_deals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255))
    company_id: Mapped[str | None] = mapped_column(
        ForeignKey("crm_companies.id"), nullable=True, index=True
    )
    contact_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    pipeline: Mapped[str] = mapped_column(String(64), default="merchant_acquisition")
    stage: Mapped[str] = mapped_column(String(32), default=DealStage.PROSPECTING.value, index=True)
    position: Mapped[int] = mapped_column(Integer, default=0)

    expected_revenue_cents: Mapped[int] = mapped_column(Integer, default=0)
    probability: Mapped[int] = mapped_column(Integer, default=10)
    expected_close_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    competitor: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reason_lost: Mapped[str | None] = mapped_column(String(255), nullable=True)
    owner_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    tags: Mapped[list] = mapped_column(JSON, default=list)

    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    company: Mapped[CrmCompany | None] = relationship(back_populates="deals")


class CrmQuotation(Base):
    """A versioned quotation that can be converted into a contract."""

    __tablename__ = "crm_quotations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    quote_number: Mapped[str] = mapped_column(String(32), index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    deal_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    company_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)

    status: Mapped[str] = mapped_column(String(32), default=QuotationStatus.DRAFT.value, index=True)
    line_items: Mapped[list] = mapped_column(JSON, default=list)
    subtotal_cents: Mapped[int] = mapped_column(Integer, default=0)
    tax_cents: Mapped[int] = mapped_column(Integer, default=0)
    total_cents: Mapped[int] = mapped_column(Integer, default=0)
    currency: Mapped[str] = mapped_column(String(8), default="cad")

    valid_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    approved_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class CrmContract(Base):
    """A signed merchant agreement with SLA, pricing, and renewal tracking."""

    __tablename__ = "crm_contracts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    contract_number: Mapped[str] = mapped_column(String(32), index=True)
    company_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    deal_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    quotation_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    status: Mapped[str] = mapped_column(String(32), default=ContractStatus.DRAFT.value, index=True)
    net_terms: Mapped[str] = mapped_column(String(16), default="NET_30")
    sla: Mapped[dict] = mapped_column(JSON, default=dict)
    service_areas: Mapped[list] = mapped_column(JSON, default=list)
    vehicles: Mapped[list] = mapped_column(JSON, default=list)
    insurance: Mapped[dict] = mapped_column(JSON, default=dict)
    pricing_sheet_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    signed_document_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    documents: Mapped[list] = mapped_column(JSON, default=list)
    value_cents: Mapped[int] = mapped_column(Integer, default=0)

    effective_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    renewal_reminder_at: Mapped[date | None] = mapped_column(Date, nullable=True)

    created_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class CrmActivity(Base):
    """Unified activity timeline (notes, calls, emails, meetings, status changes)."""

    __tablename__ = "crm_activities"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    entity_type: Mapped[str] = mapped_column(String(32), index=True)
    entity_id: Mapped[str] = mapped_column(String(36), index=True)
    activity_type: Mapped[str] = mapped_column(String(32), default="note", index=True)
    subject: Mapped[str | None] = mapped_column(String(255), nullable=True)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    actor_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CrmSalesTask(Base):
    """Rich CRM task: calls, follow-ups, contract reviews, merchant visits, demos."""

    __tablename__ = "crm_sales_tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    task_type: Mapped[str] = mapped_column(String(32), default="todo", index=True)
    status: Mapped[str] = mapped_column(String(32), default="open", index=True)
    priority: Mapped[str] = mapped_column(String(16), default="medium")

    entity_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    entity_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    company_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    deal_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)

    assigned_to: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    remind_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    zoho_event_uid: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    is_recurring: Mapped[bool] = mapped_column(Boolean, default=False)
    recurrence_rule: Mapped[str | None] = mapped_column(String(128), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class CrmInvoice(Base):
    """A merchant/account invoice tracked inside the CRM."""

    __tablename__ = "crm_invoices"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    invoice_number: Mapped[str] = mapped_column(String(32), index=True)
    company_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    deal_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    contract_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    status: Mapped[str] = mapped_column(String(32), default="draft", index=True)
    amount_cents: Mapped[int] = mapped_column(Integer, default=0)
    tax_cents: Mapped[int] = mapped_column(Integer, default=0)
    total_cents: Mapped[int] = mapped_column(Integer, default=0)
    currency: Mapped[str] = mapped_column(String(8), default="cad")
    net_terms: Mapped[str] = mapped_column(String(16), default="NET_30")
    line_items: Mapped[list] = mapped_column(JSON, default=list)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    issue_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    operational_invoice_id: Mapped[str | None] = mapped_column(
        ForeignKey("invoices.id"), nullable=True, index=True
    )

    created_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class CrmDocument(Base):
    """Documents attached to CRM entities (contracts, insurance, NDAs, etc.)."""

    __tablename__ = "crm_documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    entity_type: Mapped[str] = mapped_column(String(32), index=True)
    entity_id: Mapped[str] = mapped_column(String(36), index=True)
    name: Mapped[str] = mapped_column(String(255))
    category: Mapped[str] = mapped_column(String(64), default="other", index=True)
    url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    uploaded_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CrmLeadIngestEvent(Base):
    """Durable idempotent raw ingest (Stripe-style redelivery safety)."""

    __tablename__ = "crm_lead_ingest_events"
    __table_args__ = (
        UniqueConstraint("provider", "external_event_id", name="uq_crm_lead_ingest_provider_ext"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    provider: Mapped[str] = mapped_column(String(64), index=True)
    external_event_id: Mapped[str] = mapped_column(String(255))
    channel: Mapped[str | None] = mapped_column(String(64), nullable=True)
    lead_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    status: Mapped[str] = mapped_column(String(32), default="processed", index=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CrmLeadIdentity(Base):
    """Cross-channel identity keys attached to a CrmLead."""

    __tablename__ = "crm_lead_identities"
    __table_args__ = (
        UniqueConstraint("kind", "value_normalized", name="uq_crm_lead_identity_kind_value"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    lead_id: Mapped[str] = mapped_column(
        ForeignKey("crm_leads.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[str] = mapped_column(String(64), index=True)
    value_normalized: Mapped[str] = mapped_column(String(320))
    raw_value: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CrmConversation(Base):
    """Channel thread attached to a lead (WhatsApp/DM/call notes)."""

    __tablename__ = "crm_conversations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    lead_id: Mapped[str] = mapped_column(
        ForeignKey("crm_leads.id", ondelete="CASCADE"), index=True
    )
    channel: Mapped[str] = mapped_column(String(64), index=True)
    external_thread_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(32), default="open", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    messages: Mapped[list["CrmConversationMessage"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan"
    )


class CrmConversationMessage(Base):
    """Single message in a CRM conversation thread."""

    __tablename__ = "crm_conversation_messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    conversation_id: Mapped[str] = mapped_column(
        ForeignKey("crm_conversations.id", ondelete="CASCADE"), index=True
    )
    direction: Mapped[str] = mapped_column(String(16), default="inbound")  # inbound|outbound|system
    body: Mapped[str] = mapped_column(Text)
    actor_type: Mapped[str] = mapped_column(String(32), default="prospect")
    actor_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    external_message_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    conversation: Mapped[CrmConversation] = relationship(back_populates="messages")


class CrmReferralCredit(Base):
    """Network credit when a merchant-referred lead converts."""

    __tablename__ = "crm_referral_credits"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    referring_merchant_id: Mapped[str] = mapped_column(String(36), index=True)
    lead_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    company_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    amount_cents: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    granted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CrmSuppression(Base):
    """Global do-not-contact store — hashed email/phone only (CASL / GDPR object)."""

    __tablename__ = "crm_suppressions"
    __table_args__ = (
        UniqueConstraint("hash_kind", "value_hash", name="uq_crm_suppressions_kind_hash"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    hash_kind: Mapped[str] = mapped_column(String(16), index=True)  # email | phone
    value_hash: Mapped[str] = mapped_column(String(64), index=True)
    source: Mapped[str] = mapped_column(String(64), default="unsubscribe")
    lead_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
