"""Pydantic schemas for the Porterchain Merchant CRM API."""

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class _ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --------------------------------------------------------------------------- #
# Leads
# --------------------------------------------------------------------------- #
class LeadBase(BaseModel):
    company_name: str
    industry: str | None = None
    website: str | None = None
    business_type: str | None = None
    address: dict[str, Any] = Field(default_factory=dict)
    primary_contact_name: str | None = None
    phone: str | None = None
    email: str | None = None
    estimated_deliveries_per_month: int | None = None
    estimated_revenue_cents: int | None = None
    preferred_vehicle: str | None = None
    service_area: str | None = None
    current_logistics_provider: str | None = None
    source: str = "website"
    channel: str | None = None
    intent_type: str = "merchant"
    decision_status: str = "new"
    status: str = "new"
    priority: str = "medium"
    assigned_to: str | None = None
    expected_close_date: date | None = None
    tags: list[str] = Field(default_factory=list)
    internal_notes: str | None = None
    custom_fields: dict[str, Any] = Field(default_factory=dict)
    consent: dict[str, Any] = Field(default_factory=dict)
    referred_by_merchant_id: str | None = None


class LeadCreate(LeadBase):
    pass


class LeadUpdate(BaseModel):
    company_name: str | None = None
    industry: str | None = None
    website: str | None = None
    business_type: str | None = None
    address: dict[str, Any] | None = None
    primary_contact_name: str | None = None
    phone: str | None = None
    email: str | None = None
    estimated_deliveries_per_month: int | None = None
    estimated_revenue_cents: int | None = None
    preferred_vehicle: str | None = None
    service_area: str | None = None
    current_logistics_provider: str | None = None
    source: str | None = None
    channel: str | None = None
    intent_type: str | None = None
    decision_status: str | None = None
    status: str | None = None
    priority: str | None = None
    assigned_to: str | None = None
    expected_close_date: date | None = None
    tags: list[str] | None = None
    internal_notes: str | None = None
    custom_fields: dict[str, Any] | None = None
    consent: dict[str, Any] | None = None
    referred_by_merchant_id: str | None = None


class LeadOut(_ORM):
    id: str
    company_name: str
    industry: str | None
    website: str | None
    business_type: str | None
    address: dict[str, Any]
    primary_contact_name: str | None
    phone: str | None
    email: str | None
    estimated_deliveries_per_month: int | None
    estimated_revenue_cents: int | None
    preferred_vehicle: str | None
    service_area: str | None
    current_logistics_provider: str | None
    source: str
    channel: str = "website"
    intent_type: str = "merchant"
    decision_status: str = "new"
    status: str
    priority: str
    assigned_to: str | None
    expected_close_date: date | None
    tags: list[str]
    internal_notes: str | None
    lead_score: int
    company_id: str | None
    deal_id: str | None
    contact_id: str | None
    referred_by_merchant_id: str | None = None
    merge_candidate_of: str | None = None
    sla_first_response_due_at: datetime | None = None
    last_touch_at: datetime | None = None
    consent: dict[str, Any] | None = None
    custom_fields: dict[str, Any] | None = None
    quote_id: str | None = None
    visitor_session_id: str | None = None
    booking_draft_id: str | None = None
    created_at: datetime
    updated_at: datetime


class LeadConvertRequest(BaseModel):
    create_deal: bool = True
    deal_name: str | None = None
    expected_revenue_cents: int | None = None
    target_stage: str | None = None
    to_merchant: bool = Field(
        default=False,
        description="Also create/link a PorterChain merchant (seat-reserve owner).",
    )
    outcome: str | None = Field(
        default=None,
        description="merchant | retail_customer | driver_partner — defaults from lead.intent_type",
    )


# --------------------------------------------------------------------------- #
# Contracts
# --------------------------------------------------------------------------- #
class ContractCreate(BaseModel):
    company_id: str | None = None
    deal_id: str | None = None
    quotation_id: str | None = None
    net_terms: str = "NET_30"
    sla: dict[str, Any] = Field(default_factory=dict)
    service_areas: list[Any] = Field(default_factory=list)
    vehicles: list[Any] = Field(default_factory=list)
    insurance: dict[str, Any] = Field(default_factory=dict)
    value_cents: int = 0
    effective_from: date | None = None
    expiry_date: date | None = None


class ContractUpdate(BaseModel):
    status: str | None = None
    net_terms: str | None = None
    sla: dict[str, Any] | None = None
    service_areas: list[Any] | None = None
    vehicles: list[Any] | None = None
    insurance: dict[str, Any] | None = None
    pricing_sheet_url: str | None = None
    signed_document_url: str | None = None
    documents: list[Any] | None = None
    value_cents: int | None = None
    effective_from: date | None = None
    expiry_date: date | None = None
    renewal_reminder_at: date | None = None


class ContractOut(_ORM):
    id: str
    contract_number: str
    company_id: str | None
    deal_id: str | None
    quotation_id: str | None
    status: str
    net_terms: str
    sla: dict[str, Any]
    service_areas: list[Any]
    vehicles: list[Any]
    insurance: dict[str, Any]
    pricing_sheet_url: str | None
    signed_document_url: str | None
    documents: list[Any]
    value_cents: int
    effective_from: date | None
    expiry_date: date | None
    renewal_reminder_at: date | None
    created_at: datetime
    updated_at: datetime


# --------------------------------------------------------------------------- #
# Activities
# --------------------------------------------------------------------------- #
class ActivityCreate(BaseModel):
    entity_type: str
    entity_id: str
    activity_type: str = "note"
    subject: str | None = None
    body: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    occurred_at: datetime | None = None


class ActivityOut(BaseModel):
    id: str
    entity_type: str
    entity_id: str
    activity_type: str
    subject: str | None
    body: str | None
    metadata: dict[str, Any] = Field(default_factory=dict)
    actor_id: str | None
    occurred_at: datetime
    created_at: datetime


# --------------------------------------------------------------------------- #
# Tasks
# --------------------------------------------------------------------------- #
class TaskCreate(BaseModel):
    title: str
    description: str | None = None
    task_type: str = "todo"
    priority: str = "medium"
    entity_type: str | None = None
    entity_id: str | None = None
    company_id: str | None = None
    deal_id: str | None = None
    assigned_to: str | None = None
    due_at: datetime | None = None
    remind_at: datetime | None = None
    is_recurring: bool = False
    recurrence_rule: str | None = None


class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    task_type: str | None = None
    status: str | None = None
    priority: str | None = None
    assigned_to: str | None = None
    due_at: datetime | None = None
    remind_at: datetime | None = None


class TaskOut(_ORM):
    id: str
    title: str
    description: str | None
    task_type: str
    status: str
    priority: str
    entity_type: str | None
    entity_id: str | None
    company_id: str | None
    deal_id: str | None
    assigned_to: str | None
    due_at: datetime | None
    remind_at: datetime | None
    zoho_event_uid: str | None = None
    is_recurring: bool
    recurrence_rule: str | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class Lead360RetailLead(BaseModel):
    id: str
    email: str
    phone: str | None = None
    quote_id: str | None = None
    customer_id: str | None = None
    crm_lead_id: str | None = None
    stage: str
    source: str
    created_at: datetime | None = None


class Lead360Assignee(BaseModel):
    id: str
    name: str | None = None
    email: str | None = None


class Lead360DraftItem(BaseModel):
    id: str
    session_id: str
    quote_id: str | None = None
    state: str
    current_step: str | None = None
    amount_cents: int | None = None
    updated_at: datetime | None = None
    draft_abandoned: bool = False
    draft_abandoned_reason: str | None = None
    kind: str = "booking_draft"


class Lead360AbandonedCheckoutItem(BaseModel):
    id: str
    quote_id: str
    email: str
    reason: str
    created_at: datetime | None = None
    kind: str = "stripe_abandoned_checkout"


class Lead360Response(BaseModel):
    """Single round-trip Lead 360 composition. Cap list sizes in the service."""

    lead: LeadOut
    retail_lead: Lead360RetailLead | None = None
    identities: list[dict[str, Any]] = Field(default_factory=list)
    conversations: list[dict[str, Any]] = Field(default_factory=list)
    tasks: list[TaskOut] = Field(default_factory=list)
    nurture: dict[str, Any] = Field(default_factory=dict)
    activities: list[dict[str, Any]] = Field(default_factory=list)
    visitor: dict[str, Any] = Field(default_factory=dict)
    quotes: list[dict[str, Any]] = Field(default_factory=list)
    drafts: list[Lead360DraftItem] = Field(default_factory=list)
    abandoned_checkouts: list[Lead360AbandonedCheckoutItem] = Field(default_factory=list)
    referral: dict[str, Any] | None = None
    sla: dict[str, Any] = Field(default_factory=dict)
    assignee: Lead360Assignee | None = None
    consent: dict[str, Any] = Field(default_factory=dict)
    score: dict[str, Any] = Field(default_factory=dict)
    merge_candidate_of: str | None = None
    urgent_unassigned_tasks: list[dict[str, Any]] = Field(default_factory=list)
    linked_merchant_id: str | None = None
    linked_customer_id: str | None = None
    linked_driver_id: str | None = None
    last_capi: Any = None


class InvoiceOut(_ORM):
    id: str
    invoice_number: str
    company_id: str | None
    deal_id: str | None
    contract_id: str | None
    status: str
    amount_cents: int
    tax_cents: int
    total_cents: int
    currency: str
    net_terms: str
    line_items: list[Any]
    notes: str | None
    issue_date: date | None
    due_date: date | None
    paid_at: datetime | None
    created_at: datetime
    updated_at: datetime


class PipelineCard(BaseModel):
    type: str  # "lead" | "deal"
    id: str
    title: str
    company_name: str | None = None
    value_cents: int = 0
    secondary: str | None = None
    stage: str
    score: int | None = None
    probability: int | None = None
    location: str | None = None


class PipelineColumn(BaseModel):
    stage: str
    cards: list[PipelineCard]
    count: int
    value_cents: int
    hidden: int = 0
    lead_count: int = 0
    deal_count: int = 0
