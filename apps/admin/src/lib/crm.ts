import { adminFetch } from "@/lib/api";

// --------------------------------------------------------------------------- //
// Types
// --------------------------------------------------------------------------- //
export type Company = {
  id: string;
  legal_name: string;
  operating_name: string | null;
  business_number: string | null;
  hst_number: string | null;
  industry: string | null;
  business_type: string | null;
  website: string | null;
  linkedin_url: string | null;
  logo_url: string | null;
  phone: string | null;
  email: string | null;
  address: Record<string, unknown>;
  branches: unknown[];
  warehouse_locations: unknown[];
  pickup_locations: unknown[];
  billing_details: Record<string, unknown>;
  estimated_deliveries_per_month: number | null;
  estimated_monthly_revenue_cents: number | null;
  preferred_vehicle: string | null;
  service_area: string | null;
  current_logistics_provider: string | null;
  merchant_status: string;
  merchant_id: string | null;
  owner_id: string | null;
  tags: string[];
  is_pinned: boolean;
  is_favorite: boolean;
  custom_fields: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type Contact = {
  id: string;
  company_id: string | null;
  first_name: string;
  last_name: string | null;
  designation: string | null;
  department: string | null;
  phone: string | null;
  mobile: string | null;
  email: string | null;
  linkedin: string | null;
  birthday: string | null;
  roles: string[];
  is_primary: boolean;
  created_at: string;
};

export type Lead = {
  id: string;
  company_name: string;
  industry: string | null;
  website: string | null;
  business_type: string | null;
  address: Record<string, unknown>;
  primary_contact_name: string | null;
  phone: string | null;
  email: string | null;
  estimated_deliveries_per_month: number | null;
  estimated_revenue_cents: number | null;
  preferred_vehicle: string | null;
  service_area: string | null;
  current_logistics_provider: string | null;
  source: string;
  status: string;
  priority: string;
  assigned_to: string | null;
  expected_close_date: string | null;
  tags: string[];
  internal_notes: string | null;
  lead_score: number;
  company_id: string | null;
  deal_id: string | null;
  contact_id: string | null;
  custom_fields: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
};

export type PipelineCard = {
  type: "lead" | "deal";
  id: string;
  title: string;
  company_name: string | null;
  value_cents: number;
  secondary: string | null;
  stage: string;
  score: number | null;
  probability: number | null;
  location: string | null;
};

export type PipelineColumn = {
  stage: string;
  cards: PipelineCard[];
  count: number;
  value_cents: number;
  hidden: number;
  lead_count: number;
  deal_count: number;
};

export type Deal = {
  id: string;
  name: string;
  company_id: string | null;
  contact_id: string | null;
  pipeline: string;
  stage: string;
  position: number;
  expected_revenue_cents: number;
  probability: number;
  expected_close_date: string | null;
  competitor: string | null;
  reason_lost: string | null;
  owner_id: string | null;
  tags: string[];
  closed_at: string | null;
  created_at: string;
  updated_at: string;
  company_name: string | null;
};

export type BoardColumn = {
  stage: string;
  deals: Deal[];
  count: number;
  value_cents: number;
};

export type QuotationLineItem = {
  label: string;
  quantity: number;
  unit_price_cents: number;
  amount_cents: number;
};

export type Quotation = {
  id: string;
  quote_number: string;
  version: number;
  deal_id: string | null;
  company_id: string | null;
  status: string;
  line_items: QuotationLineItem[];
  subtotal_cents: number;
  tax_cents: number;
  total_cents: number;
  currency: string;
  valid_until: string | null;
  notes: string | null;
  approved_by: string | null;
  sent_at: string | null;
  created_at: string;
  updated_at: string;
};

export type Contract = {
  id: string;
  contract_number: string;
  company_id: string | null;
  deal_id: string | null;
  quotation_id: string | null;
  status: string;
  net_terms: string;
  sla: Record<string, unknown>;
  service_areas: unknown[];
  vehicles: unknown[];
  insurance: Record<string, unknown>;
  pricing_sheet_url: string | null;
  signed_document_url: string | null;
  documents: unknown[];
  value_cents: number;
  effective_from: string | null;
  expiry_date: string | null;
  renewal_reminder_at: string | null;
  created_at: string;
  updated_at: string;
};

export type Activity = {
  id: string;
  entity_type: string;
  entity_id: string;
  activity_type: string;
  subject: string | null;
  body: string | null;
  metadata: Record<string, unknown>;
  actor_id: string | null;
  occurred_at: string;
  created_at: string;
};

export type Task = {
  id: string;
  title: string;
  description: string | null;
  task_type: string;
  status: string;
  priority: string;
  entity_type: string | null;
  entity_id: string | null;
  company_id: string | null;
  deal_id: string | null;
  assigned_to: string | null;
  due_at: string | null;
  remind_at: string | null;
  zoho_event_uid: string | null;
  is_recurring: boolean;
  recurrence_rule: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
};

export type CrmCalendarEvent = {
  id: string;
  title: string;
  start: string | null;
  end: string | null;
  source: "crm" | "zoho";
  task_type?: string | null;
  status?: string | null;
  zoho_event_uid?: string | null;
  entity_type?: string | null;
  entity_id?: string | null;
  location?: string | null;
  organizer?: string | null;
};

export type CrmCalendarPayload = {
  integration: {
    provider: string;
    configured: boolean;
    accounts_url: string;
    api_base: string;
    calendar_uid: string | null;
    timezone: string;
    missing: string[];
    sync_task_types: string[];
  };
  crm_events: CrmCalendarEvent[];
  zoho_events: CrmCalendarEvent[];
  zoho_error: string | null;
};

export type Invoice = {
  id: string;
  invoice_number: string;
  company_id: string | null;
  deal_id: string | null;
  contract_id: string | null;
  status: string;
  amount_cents: number;
  tax_cents: number;
  total_cents: number;
  currency: string;
  net_terms: string;
  line_items: Array<{
    label: string;
    quantity: number;
    unit_price_cents: number;
    amount_cents: number;
  }>;
  notes: string | null;
  issue_date: string | null;
  due_date: string | null;
  paid_at: string | null;
  created_at: string;
  updated_at: string;
};

export type CompanyFacets = {
  industries: string[];
  statuses: Array<{ value: string; count: number }>;
  cities: Array<{ name: string; count: number }>;
  provinces: Array<{ code: string; count: number }>;
};

export type CompanyStats = {
  total: number;
  active_merchants: number;
  converted: number;
  conversion_rate_percent: number;
  monthly_pipeline_value_cents: number;
  by_status: Array<{ status: string; count: number }>;
  by_industry: Array<{ industry: string; count: number }>;
  by_province: Array<{ province: string; count: number }>;
  top_companies: Array<{ id: string; name: string; value_cents: number; merchant_status: string }>;
};

export type CrmDashboard = {
  new_leads: number;
  todays_follow_ups: number;
  overdue_tasks: number;
  meetings_today: number;
  contracts_pending: number;
  quotes_pending: number;
  merchant_conversions: number;
  pipeline_value_cents: number;
  monthly_revenue_forecast_cents: number;
  open_deals: number;
  won_deals_this_month: number;
  active_companies: number;
  recent_activities: Array<Record<string, unknown>>;
  lead_sources: Array<{ source: string; count: number }>;
  top_sales_reps: Array<{ owner_id: string; won_deals: number; revenue_cents: number }>;
  pipeline_by_stage: Array<{ stage: string; count: number; value_cents: number }>;
};

export type CrmReports = {
  pipeline: Array<{ stage: string; count: number; value_cents: number }>;
  conversion_rate_percent: number;
  revenue_forecast_cents: number;
  lead_sources: Array<{ source: string; count: number }>;
  sales_performance: Array<{ owner_id: string; deals: number; revenue_cents: number }>;
  merchant_acquisition_cost_cents: number;
  avg_time_to_close_days: number;
  quote_win_rate_percent: number;
};

export type CrmMeta = {
  pipeline_stages: string[];
  stage_probability: Record<string, number>;
  contact_roles: string[];
};

export type ImportResult = {
  entity: string;
  total: number;
  imported: number;
  duplicates: number;
  errors: Array<{ row: number; error: string }>;
};

const qs = (params: Record<string, string | number | boolean | undefined | null>) => {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== "") search.set(key, String(value));
  }
  const s = search.toString();
  return s ? `?${s}` : "";
};

const B = "/v1/admin/crm";

// --------------------------------------------------------------------------- //
// Client
// --------------------------------------------------------------------------- //
export const crm = {
  meta: (t: string) => adminFetch<CrmMeta>(`${B}/meta`, t),
  dashboard: (t: string) => adminFetch<CrmDashboard>(`${B}/dashboard`, t),
  reports: (t: string) => adminFetch<CrmReports>(`${B}/reports`, t),

  // Companies
  companies: (t: string, params: Record<string, string | undefined> = {}) =>
    adminFetch<Company[]>(`${B}/companies${qs(params)}`, t),
  companyFacets: (t: string) => adminFetch<CompanyFacets>(`${B}/companies/facets`, t),
  companyStats: (t: string) => adminFetch<CompanyStats>(`${B}/companies/stats`, t),
  company: (t: string, id: string) => adminFetch<Company>(`${B}/companies/${id}`, t),
  createCompany: (t: string, body: Partial<Company>) =>
    adminFetch<Company>(`${B}/companies`, t, { method: "POST", body: JSON.stringify(body) }),
  updateCompany: (t: string, id: string, body: Partial<Company>) =>
    adminFetch<Company>(`${B}/companies/${id}`, t, { method: "PATCH", body: JSON.stringify(body) }),
  deleteCompany: (t: string, id: string) =>
    adminFetch<void>(`${B}/companies/${id}`, t, { method: "DELETE" }),
  convertMerchant: (t: string, id: string) =>
    adminFetch<{
      merchant_id: string;
      created: boolean;
      invitation_sent: boolean;
      invitation_email?: string;
    }>(`${B}/companies/${id}/convert-merchant`, t, { method: "POST" }),

  // Contacts
  contacts: (t: string, params: Record<string, string | undefined> = {}) =>
    adminFetch<Contact[]>(`${B}/contacts${qs(params)}`, t),
  createContact: (t: string, body: Partial<Contact>) =>
    adminFetch<Contact>(`${B}/contacts`, t, { method: "POST", body: JSON.stringify(body) }),
  updateContact: (t: string, id: string, body: Partial<Contact>) =>
    adminFetch<Contact>(`${B}/contacts/${id}`, t, { method: "PATCH", body: JSON.stringify(body) }),
  deleteContact: (t: string, id: string) =>
    adminFetch<void>(`${B}/contacts/${id}`, t, { method: "DELETE" }),

  // Leads
  leads: (t: string, params: Record<string, string | undefined> = {}) =>
    adminFetch<Lead[]>(`${B}/leads${qs(params)}`, t),
  lead: (t: string, id: string) => adminFetch<Lead>(`${B}/leads/${id}`, t),
  leadFacets: (t: string) =>
    adminFetch<{
      industries: string[];
      sources: string[];
      cities: Array<{ name: string; count: number }>;
      provinces: Array<{ code: string; count: number }>;
    }>(`${B}/leads/facets`, t),
  createLead: (t: string, body: Partial<Lead>) =>
    adminFetch<Lead>(`${B}/leads`, t, { method: "POST", body: JSON.stringify(body) }),
  updateLead: (t: string, id: string, body: Partial<Lead>) =>
    adminFetch<Lead>(`${B}/leads/${id}`, t, { method: "PATCH", body: JSON.stringify(body) }),
  deleteLead: (t: string, id: string) =>
    adminFetch<void>(`${B}/leads/${id}`, t, { method: "DELETE" }),
  convertLead: (
    t: string,
    id: string,
    body: {
      create_deal?: boolean;
      deal_name?: string;
      expected_revenue_cents?: number;
      target_stage?: string;
    }
  ) =>
    adminFetch<{ company_id: string; contact_id: string | null; deal_id: string | null }>(
      `${B}/leads/${id}/convert`,
      t,
      { method: "POST", body: JSON.stringify(body) }
    ),

  // Deals
  board: (t: string) => adminFetch<BoardColumn[]>(`${B}/deals/board`, t),
  pipeline: (t: string, params: Record<string, string | undefined> = {}) =>
    adminFetch<PipelineColumn[]>(`${B}/pipeline${qs(params)}`, t),
  deals: (t: string, params: Record<string, string | undefined> = {}) =>
    adminFetch<Deal[]>(`${B}/deals${qs(params)}`, t),
  deal: (t: string, id: string) => adminFetch<Deal>(`${B}/deals/${id}`, t),
  createDeal: (t: string, body: Partial<Deal>) =>
    adminFetch<Deal>(`${B}/deals`, t, { method: "POST", body: JSON.stringify(body) }),
  updateDeal: (t: string, id: string, body: Partial<Deal>) =>
    adminFetch<Deal>(`${B}/deals/${id}`, t, { method: "PATCH", body: JSON.stringify(body) }),
  moveDeal: (t: string, id: string, stage: string, position: number) =>
    adminFetch<Deal>(`${B}/deals/${id}/move`, t, {
      method: "POST",
      body: JSON.stringify({ stage, position }),
    }),
  deleteDeal: (t: string, id: string) =>
    adminFetch<void>(`${B}/deals/${id}`, t, { method: "DELETE" }),

  // Quotations
  quotations: (t: string, params: Record<string, string | undefined> = {}) =>
    adminFetch<Quotation[]>(`${B}/quotations${qs(params)}`, t),
  createQuotation: (
    t: string,
    body: {
      deal_id?: string;
      company_id?: string;
      line_items: Array<{ label: string; quantity: number; unit_price_cents: number }>;
      tax_cents?: number;
      valid_until?: string;
      notes?: string;
    }
  ) => adminFetch<Quotation>(`${B}/quotations`, t, { method: "POST", body: JSON.stringify(body) }),
  setQuotationStatus: (t: string, id: string, status: string) =>
    adminFetch<Quotation>(`${B}/quotations/${id}/status${qs({ status })}`, t, { method: "POST" }),
  convertQuotation: (t: string, id: string) =>
    adminFetch<Contract>(`${B}/quotations/${id}/convert-contract`, t, { method: "POST" }),

  // Contracts
  contracts: (t: string, params: Record<string, string | undefined> = {}) =>
    adminFetch<Contract[]>(`${B}/contracts${qs(params)}`, t),
  createContract: (t: string, body: Partial<Contract>) =>
    adminFetch<Contract>(`${B}/contracts`, t, { method: "POST", body: JSON.stringify(body) }),
  updateContract: (t: string, id: string, body: Partial<Contract>) =>
    adminFetch<Contract>(`${B}/contracts/${id}`, t, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),

  // Invoices
  invoices: (t: string, params: Record<string, string | undefined> = {}) =>
    adminFetch<Invoice[]>(`${B}/invoices${qs(params)}`, t),
  createInvoice: (
    t: string,
    body: {
      company_id?: string;
      deal_id?: string;
      line_items?: Array<{ label: string; quantity: number; unit_price_cents: number }>;
      amount_cents?: number;
      tax_cents?: number;
      net_terms?: string;
      issue_date?: string;
      due_date?: string;
      notes?: string;
    }
  ) => adminFetch<Invoice>(`${B}/invoices`, t, { method: "POST", body: JSON.stringify(body) }),
  updateInvoice: (t: string, id: string, body: Partial<Invoice>) =>
    adminFetch<Invoice>(`${B}/invoices/${id}`, t, { method: "PATCH", body: JSON.stringify(body) }),

  // Activities
  activities: (t: string, params: Record<string, string | undefined> = {}) =>
    adminFetch<Activity[]>(`${B}/activities${qs(params)}`, t),
  createActivity: (
    t: string,
    body: {
      entity_type: string;
      entity_id: string;
      activity_type?: string;
      subject?: string;
      body?: string;
    }
  ) => adminFetch<Activity>(`${B}/activities`, t, { method: "POST", body: JSON.stringify(body) }),

  // Tasks
  tasks: (t: string, params: Record<string, string | undefined> = {}) =>
    adminFetch<Task[]>(`${B}/tasks${qs(params)}`, t),
  createTask: (t: string, body: Partial<Task>) =>
    adminFetch<Task>(`${B}/tasks`, t, { method: "POST", body: JSON.stringify(body) }),
  updateTask: (t: string, id: string, body: Partial<Task>) =>
    adminFetch<Task>(`${B}/tasks/${id}`, t, { method: "PATCH", body: JSON.stringify(body) }),
  deleteTask: (t: string, id: string) =>
    adminFetch<void>(`${B}/tasks/${id}`, t, { method: "DELETE" }),

  calendarStatus: (t: string) => adminFetch<CrmCalendarPayload["integration"]>(`${B}/calendar/status`, t),
  calendarEvents: (t: string, params: { start: string; end: string; entity_id?: string }) =>
    adminFetch<CrmCalendarPayload>(`${B}/calendar/events${qs(params)}`, t),

  // Import
  import: (t: string, entity: string, rows: Array<Record<string, unknown>>, dedupe = true) =>
    adminFetch<ImportResult>(`${B}/import`, t, {
      method: "POST",
      body: JSON.stringify({ entity, rows, dedupe }),
    }),
};
