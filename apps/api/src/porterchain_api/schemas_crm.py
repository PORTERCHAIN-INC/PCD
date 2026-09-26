"""Pydantic schemas for the Porterchain Merchant CRM API."""

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class _ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --------------------------------------------------------------------------- #
# Companies
# --------------------------------------------------------------------------- #
class CompanyBase(BaseModel):
    legal_name: str
    operating_name: str | None = None
    business_number: str | None = None
    hst_number: str | None = None
    industry: str | None = None
    business_type: str | None = None
    website: str | None = None
    linkedin_url: str | None = None
    logo_url: str | None = None
    phone: str | None = None
    email: str | None = None
    address: dict[str, Any] = Field(default_factory=dict)
    branches: list[Any] = Field(default_factory=list)
    warehouse_locations: list[Any] = Field(default_factory=list)
    pickup_locations: list[Any] = Field(default_factory=list)
    billing_details: dict[str, Any] = Field(default_factory=dict)
    estimated_deliveries_per_month: int | None = None
    estimated_monthly_revenue_cents: int | None = None
    preferred_vehicle: str | None = None
    service_area: str | None = None
    current_logistics_provider: str | None = None
    merchant_status: str = "lead"
    owner_id: str | None = None
    tags: list[str] = Field(default_factory=list)
    custom_fields: dict[str, Any] = Field(default_factory=dict)


class CompanyCreate(CompanyBase):
    pass


class CompanyUpdate(BaseModel):
    legal_name: str | None = None
    operating_name: str | None = None
    business_number: str | None = None
    hst_number: str | None = None
    industry: str | None = None
    business_type: str | None = None
    website: str | None = None
    linkedin_url: str | None = None
    logo_url: str | None = None
    phone: str | None = None
    email: str | None = None
    address: dict[str, Any] | None = None
    branches: list[Any] | None = None
    warehouse_locations: list[Any] | None = None
    pickup_locations: list[Any] | None = None
    billing_details: dict[str, Any] | None = None
    estimated_deliveries_per_month: int | None = None
    estimated_monthly_revenue_cents: int | None = None
    preferred_vehicle: str | None = None
    service_area: str | None = None
    current_logistics_provider: str | None = None
    merchant_status: str | None = None
    owner_id: str | None = None
    tags: list[str] | None = None
    is_pinned: bool | None = None
    is_favorite: bool | None = None
    custom_fields: dict[str, Any] | None = None


class CompanyOut(_ORM):
    id: str
    legal_name: str
    operating_name: str | None
    business_number: str | None
    hst_number: str | None
    industry: str | None
    business_type: str | None
    website: str | None
    linkedin_url: str | None
    logo_url: str | None
    phone: str | None
    email: str | None
    address: dict[str, Any]
    branches: list[Any]
    warehouse_locations: list[Any]
    pickup_locations: list[Any]
    billing_details: dict[str, Any]
    estimated_deliveries_per_month: int | None
    estimated_monthly_revenue_cents: int | None
    preferred_vehicle: str | None
    service_area: str | None
    current_logistics_provider: str | None
    merchant_status: str
    merchant_id: str | None
    owner_id: str | None
    tags: list[str]
    is_pinned: bool
    is_favorite: bool
    custom_fields: dict[str, Any]
    created_at: datetime
    updated_at: datetime


# --------------------------------------------------------------------------- #
# Contacts
# --------------------------------------------------------------------------- #
class ContactBase(BaseModel):
    company_id: str | None = None
    first_name: str
    last_name: str | None = None
    designation: str | None = None
    department: str | None = None
    phone: str | None = None
    mobile: str | None = None
    email: str | None = None
    linkedin: str | None = None
    birthday: date | None = None
    roles: list[str] = Field(default_factory=list)
    is_primary: bool = False


class ContactCreate(ContactBase):
    pass


class ContactUpdate(BaseModel):
    company_id: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    designation: str | None = None
    department: str | None = None
    phone: str | None = None
    mobile: str | None = None
    email: str | None = None
    linkedin: str | None = None
    birthday: date | None = None
    roles: list[str] | None = None
    is_primary: bool | None = None


class ContactOut(_ORM):
    id: str
    company_id: str | None
    first_name: str
    last_name: str | None
    designation: str | None
    department: str | None
    phone: str | None
    mobile: str | None
    email: str | None
    linkedin: str | None
    birthday: date | None
    roles: list[str]
    is_primary: bool
    created_at: datetime


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


class LeadConvertResponse(BaseModel):
    company_id: str
    contact_id: str | None
    deal_id: str | None


# --------------------------------------------------------------------------- #
# Deals
# --------------------------------------------------------------------------- #
class DealBase(BaseModel):
    name: str
    company_id: str | None = None
    contact_id: str | None = None
    pipeline: str = "merchant_acquisition"
    stage: str = "prospecting"
    expected_revenue_cents: int = 0
    probability: int = 10
    expected_close_date: date | None = None
    competitor: str | None = None
    reason_lost: str | None = None
    owner_id: str | None = None
    tags: list[str] = Field(default_factory=list)


class DealCreate(DealBase):
    pass


class DealUpdate(BaseModel):
    name: str | None = None
    company_id: str | None = None
    contact_id: str | None = None
    stage: str | None = None
    position: int | None = None
    expected_revenue_cents: int | None = None
    probability: int | None = None
    expected_close_date: date | None = None
    competitor: str | None = None
    reason_lost: str | None = None
    owner_id: str | None = None
    tags: list[str] | None = None


class DealStageUpdate(BaseModel):
    stage: str
    position: int = 0


class DealOut(_ORM):
    id: str
    name: str
    company_id: str | None
    contact_id: str | None
    pipeline: str
    stage: str
    position: int
    expected_revenue_cents: int
    probability: int
    expected_close_date: date | None
    competitor: str | None
    reason_lost: str | None
    owner_id: str | None
    tags: list[str]
    closed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    company_name: str | None = None


# --------------------------------------------------------------------------- #
# Quotations
# --------------------------------------------------------------------------- #
class QuotationLineItem(BaseModel):
    label: str
    quantity: float = 1
    unit_price_cents: int = 0
    amount_cents: int = 0


class QuotationCreate(BaseModel):
    deal_id: str | None = None
    company_id: str | None = None
    line_items: list[QuotationLineItem] = Field(default_factory=list)
    tax_cents: int = 0
    currency: str = "cad"
    valid_until: date | None = None
    notes: str | None = None


class QuotationUpdate(BaseModel):
    status: str | None = None
    line_items: list[QuotationLineItem] | None = None
    tax_cents: int | None = None
    valid_until: date | None = None
    notes: str | None = None


class QuotationOut(_ORM):
    id: str
    quote_number: str
    version: int
    deal_id: str | None
    company_id: str | None
    status: str
    line_items: list[Any]
    subtotal_cents: int
    tax_cents: int
    total_cents: int
    currency: str
    valid_until: date | None
    notes: str | None
    approved_by: str | None
    sent_at: datetime | None
    created_at: datetime
    updated_at: datetime


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


class CrmCalendarStatusResponse(BaseModel):
    provider: str
    configured: bool
    accounts_url: str
    api_base: str
    calendar_uid: str | None = None
    timezone: str
    missing: list[str] = Field(default_factory=list)
    sync_task_types: list[str] = Field(default_factory=list)


class CrmCalendarEventItem(BaseModel):
    id: str
    title: str
    start: str | None = None
    end: str | None = None
    source: str
    task_type: str | None = None
    status: str | None = None
    zoho_event_uid: str | None = None
    entity_type: str | None = None
    entity_id: str | None = None
    location: str | None = None
    organizer: str | None = None


class CrmCalendarEventsResponse(BaseModel):
    integration: CrmCalendarStatusResponse
    crm_events: list[CrmCalendarEventItem]
    zoho_events: list[CrmCalendarEventItem]
    zoho_error: str | None = None


# --------------------------------------------------------------------------- #
# Dashboard / reports / import
# --------------------------------------------------------------------------- #
class CrmDashboardResponse(BaseModel):
    new_leads: int
    todays_follow_ups: int
    overdue_tasks: int
    meetings_today: int
    contracts_pending: int
    quotes_pending: int
    merchant_conversions: int
    pipeline_value_cents: int
    monthly_revenue_forecast_cents: int
    open_deals: int
    won_deals_this_month: int
    active_companies: int
    recent_activities: list[dict[str, Any]] = Field(default_factory=list)
    lead_sources: list[dict[str, Any]] = Field(default_factory=list)
    top_sales_reps: list[dict[str, Any]] = Field(default_factory=list)
    pipeline_by_stage: list[dict[str, Any]] = Field(default_factory=list)


class CrmReportsResponse(BaseModel):
    pipeline: list[dict[str, Any]]
    conversion_rate_percent: float
    revenue_forecast_cents: int
    lead_sources: list[dict[str, Any]]
    sales_performance: list[dict[str, Any]]
    merchant_acquisition_cost_cents: int
    avg_time_to_close_days: float
    quote_win_rate_percent: float


class CsvImportRow(BaseModel):
    data: dict[str, Any]


class CsvImportRequest(BaseModel):
    entity: str  # companies | contacts | leads | deals
    rows: list[dict[str, Any]]
    dedupe: bool = True


class CsvImportResult(BaseModel):
    entity: str
    total: int
    imported: int
    duplicates: int
    errors: list[dict[str, Any]] = Field(default_factory=list)


class InvoiceLineItem(BaseModel):
    label: str
    quantity: float = 1
    unit_price_cents: int = 0
    amount_cents: int = 0


class InvoiceCreate(BaseModel):
    company_id: str | None = None
    deal_id: str | None = None
    contract_id: str | None = None
    line_items: list[InvoiceLineItem] = Field(default_factory=list)
    amount_cents: int = 0
    tax_cents: int = 0
    currency: str = "cad"
    net_terms: str = "NET_30"
    issue_date: date | None = None
    due_date: date | None = None
    notes: str | None = None


class InvoiceUpdate(BaseModel):
    status: str | None = None
    amount_cents: int | None = None
    tax_cents: int | None = None
    net_terms: str | None = None
    issue_date: date | None = None
    due_date: date | None = None
    notes: str | None = None


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
