import { z } from "zod";
import { STAFF_COOKIE_TOKEN } from "@/lib/staff-session";
import { adminFetch } from "@/lib/api";
import type { Lead } from "@/lib/crm";

export type AgentActivityRow = {
  id: string;
  company_name?: string;
  email?: string | null;
  phone?: string | null;
  source?: string | null;
  channel?: string | null;
  status?: string | null;
  priority?: string | null;
  city?: string | null;
  tags?: string[];
  marketing_consent?: boolean;
  agent_status?: string | null;
  last_channel?: string | null;
  last_send_at?: string | null;
  last_trigger?: string | null;
  blocks?: string[];
  reason?: string | null;
  welcomed?: boolean;
  needs_enrich?: boolean;
  created_at?: string | null;
  updated_at?: string | null;
  assigned?: boolean;
  notice_kind?: "unassigned" | "sla";
  notice_subject?: string;
  notice_body?: string;
  nba?: Record<string, unknown>;
};

export type LeadAgentActivity = {
  config: {
    auto_send_enabled: boolean;
    whatsapp_cloud_configured: boolean;
    kill_switch_env: string;
    internal_email?: boolean;
  };
  counts: {
    welcomed: number;
    needs_enrich: number;
    awaiting_welcome: number;
    blocked: number;
    new_total: number;
    unassigned: number;
    notices: number;
  };
  inbox: {
    unassigned: AgentActivityRow[];
    notices: AgentActivityRow[];
  };
  lanes: {
    welcomed: AgentActivityRow[];
    needs_enrich: AgentActivityRow[];
    awaiting_welcome: AgentActivityRow[];
    blocked: AgentActivityRow[];
    recent: AgentActivityRow[];
  };
  generated_at: string;
};

/** Five-stage pipeline (+ archived = hidden). Old names are mapped server-side. */
export const LEAD_STATUSES = ["new", "replied", "quoted", "won", "lost", "archived"] as const;

export const LOST_REASONS = [
  { key: "price", label: "Price" },
  { key: "timing", label: "Timing" },
  { key: "no_response", label: "No response" },
  { key: "competitor", label: "Went with a competitor" },
  { key: "out_of_area", label: "Out of area" },
  { key: "not_a_fit", label: "Not a fit" },
  { key: "other", label: "Other" },
] as const;

export const LEAD_PRIORITIES = ["low", "medium", "high", "urgent"] as const;

export const LEAD_CHANNELS = [
  "website",
  "instagram",
  "facebook",
  "linkedin",
  "twitter",
  "youtube",
  "whatsapp",
  "google_ads",
  "google_business_profile",
  "merchant_referral",
  "phone_call",
  "sms",
  "manual",
  "capacity_guide",
  "website_booking",
  "email",
  "app_install",
  "merchant_signup",
  "driver_signup",
  "other",
] as const;

export const LEAD_INTENT_TYPES = [
  "merchant",
  "retail_customer",
  "driver_partner",
  "unknown",
] as const;

export const LEAD_DECISION_STATUSES = [
  "new",
  "researching",
  "questions_open",
  "objection",
  "ready_to_convert",
  "deferred",
  "lost",
  "converted",
] as const;

export const LEAD_SOURCES = [
  "website_business",
  "website_contact",
  "website_quote",
  "website_demo",
  "website_newsletter",
  "website_booking",
  "website_driver_partner",
  "website_capacity_guide",
  "instagram",
  "facebook",
  "linkedin",
  "twitter",
  "youtube",
  "whatsapp",
  "google_ads",
  "google_business_profile",
  "merchant_referral",
  "phone_call",
  "sms",
  "manual",
  "vendor_import",
] as const;

export type LeadFilters = {
  status?: string;
  priority?: string;
  source?: string;
  channel?: string;
  intent_type?: string;
  decision_status?: string;
  assigned_to?: string;
  unassigned?: boolean;
  merge_candidates?: boolean;
  sla_breached?: boolean;
  has_open_draft?: boolean;
  nurture_scheduled?: boolean;
  has_abandoned?: boolean;
  include_archived?: boolean;
  sort?: "smart" | "created_at";
  search?: string;
  city?: string;
  tag?: string;
  has_phone?: boolean;
  /** Unified inbox: someone wrote in and is waiting on us. */
  awaiting_reply?: boolean;
  /** "buyers" hides driver applicants; "drivers" shows only them. */
  view?: "now" | "waiting" | "buyers" | "drivers";
  limit?: number;
  offset?: number;
};

const leadSchema = z.object({
  id: z.string(),
  company_name: z.string(),
  industry: z.string().nullable(),
  website: z.string().nullable(),
  business_type: z.string().nullable(),
  address: z.record(z.string(), z.unknown()),
  primary_contact_name: z.string().nullable(),
  phone: z.string().nullable(),
  email: z.string().nullable(),
  estimated_deliveries_per_month: z.number().nullable(),
  estimated_revenue_cents: z.number().nullable(),
  preferred_vehicle: z.string().nullable(),
  service_area: z.string().nullable(),
  current_logistics_provider: z.string().nullable(),
  source: z.string(),
  channel: z.string().optional().default("website"),
  intent_type: z.string().optional().default("merchant"),
  decision_status: z.string().optional().default("new"),
  status: z.string(),
  priority: z.string(),
  assigned_to: z.string().nullable(),
  expected_close_date: z.string().nullable(),
  tags: z.array(z.string()),
  internal_notes: z.string().nullable(),
  lead_score: z.number(),
  company_id: z.string().nullable(),
  deal_id: z.string().nullable(),
  contact_id: z.string().nullable(),
  referred_by_merchant_id: z.string().nullable().optional(),
  merge_candidate_of: z.string().nullable().optional(),
  sla_first_response_due_at: z.string().nullable().optional(),
  last_touch_at: z.string().nullable().optional(),
  consent: z.record(z.string(), z.unknown()).nullable().optional(),
  custom_fields: z.record(z.string(), z.unknown()).nullable(),
  quote_id: z.string().nullable().optional(),
  visitor_session_id: z.string().nullable().optional(),
  booking_draft_id: z.string().nullable().optional(),
  awaiting_reply: z.boolean().optional().default(false),
  last_inbound_at: z.string().nullable().optional(),
  first_response_at: z.string().nullable().optional(),
  quoted_at: z.string().nullable().optional(),
  won_at: z.string().nullable().optional(),
  lost_at: z.string().nullable().optional(),
  lost_reason: z.string().nullable().optional(),
  order_id: z.string().nullable().optional(),
  created_at: z.string(),
  updated_at: z.string(),
});

const lead360Schema = z.object({
  lead: leadSchema,
  retail_lead: z
    .object({
      id: z.string(),
      email: z.string(),
      phone: z.string().nullable().optional(),
      quote_id: z.string().nullable().optional(),
      customer_id: z.string().nullable().optional(),
      crm_lead_id: z.string().nullable().optional(),
      stage: z.string(),
      source: z.string(),
      created_at: z.string().nullable().optional(),
    })
    .nullable()
    .optional(),
  identities: z.array(z.record(z.string(), z.unknown())).default([]),
  conversations: z.array(z.record(z.string(), z.unknown())).default([]),
  tasks: z.array(z.record(z.string(), z.unknown())).default([]),
  nurture: z.record(z.string(), z.unknown()).default({}),
  activities: z.array(z.record(z.string(), z.unknown())).default([]),
  visitor: z.record(z.string(), z.unknown()).default({}),
  quotes: z.array(z.record(z.string(), z.unknown())).default([]),
  drafts: z
    .array(
      z.object({
        id: z.string(),
        session_id: z.string(),
        quote_id: z.string().nullable().optional(),
        state: z.string(),
        current_step: z.string().nullable().optional(),
        amount_cents: z.number().nullable().optional(),
        updated_at: z.string().nullable().optional(),
        draft_abandoned: z.boolean().optional(),
        draft_abandoned_reason: z.string().nullable().optional(),
        kind: z.string().optional(),
      })
    )
    .default([]),
  abandoned_checkouts: z
    .array(
      z.object({
        id: z.string(),
        quote_id: z.string(),
        email: z.string(),
        reason: z.string(),
        created_at: z.string().nullable().optional(),
        kind: z.string().optional(),
      })
    )
    .default([]),
  referral: z.record(z.string(), z.unknown()).nullable().optional(),
  sla: z.record(z.string(), z.unknown()).default({}),
  assignee: z
    .object({
      id: z.string(),
      name: z.string().nullable().optional(),
      email: z.string().nullable().optional(),
    })
    .nullable()
    .optional(),
  consent: z.record(z.string(), z.unknown()).default({}),
  score: z.record(z.string(), z.unknown()).default({}),
  merge_candidate_of: z.string().nullable().optional(),
  urgent_unassigned_tasks: z.array(z.record(z.string(), z.unknown())).default([]),
  linked_merchant_id: z.string().nullable().optional(),
  linked_customer_id: z.string().nullable().optional(),
  linked_driver_id: z.string().nullable().optional(),
  last_capi: z.unknown().optional(),
});

export type Lead360 = z.infer<typeof lead360Schema>;

/** Build list query string for `/v1/admin/leads` (exported for unit tests). */
export function buildLeadFiltersQuery(filters: LeadFilters): string {
  const params = new URLSearchParams();
  if (filters.status) params.set("status", filters.status);
  if (filters.priority) params.set("priority", filters.priority);
  if (filters.source) params.set("source", filters.source);
  if (filters.channel) params.set("channel", filters.channel);
  if (filters.intent_type) params.set("intent_type", filters.intent_type);
  if (filters.decision_status) params.set("decision_status", filters.decision_status);
  if (filters.assigned_to) params.set("assigned_to", filters.assigned_to);
  if (filters.unassigned) params.set("unassigned", "true");
  if (filters.merge_candidates) params.set("merge_candidates", "true");
  if (filters.sla_breached) params.set("sla_breached", "true");
  if (filters.has_open_draft) params.set("has_open_draft", "true");
  if (filters.nurture_scheduled) params.set("nurture_scheduled", "true");
  if (filters.has_abandoned) params.set("has_abandoned", "true");
  if (filters.include_archived) params.set("include_archived", "true");
  if (filters.sort) params.set("sort", filters.sort);
  else params.set("sort", "smart");
  if (filters.city) params.set("city", filters.city);
  if (filters.tag) params.set("tag", filters.tag);
  if (filters.has_phone === true) params.set("has_phone", "true");
  if (filters.has_phone === false) params.set("has_phone", "false");
  if (filters.awaiting_reply) params.set("awaiting_reply", "true");
  if (filters.view) params.set("view", filters.view);
  if (filters.search) params.set("search", filters.search);
  if (filters.limit != null) params.set("limit", String(filters.limit));
  if (filters.offset != null) params.set("offset", String(filters.offset));
  const q = params.toString();
  return q ? `?${q}` : "";
}

function qs(filters: LeadFilters): string {
  return buildLeadFiltersQuery(filters);
}

export type LeadMetrics = {
  window_days: number;
  ingest: { total: number; by_channel: Record<string, number> };
  leads: {
    total: number;
    converted: number;
    conversion_rate: number;
    merge_candidates: number;
    soft_duplicate_rate_pct: number;
    merge_accept?: number;
    merge_reject?: number;
  };
  sla: {
    open_new_with_due: number;
    breached_new: number;
    median_first_touch_minutes: number | null;
  };
  capi: {
    meta_lead_id_leads: number;
    meta_family_leads_window: number;
    meta_lead_id_coverage_pct: number | null;
  };
  assist: {
    nim_calls: number;
    accepted?: number;
    rejected?: number;
    accept_rate_pct?: number | null;
  };
};

export type ReplyChannelStatus = {
  enabled: boolean;
  reason: string | null;
  transport?: string | null;
  from?: string;
  in_service_window?: boolean;
  window_closes_at?: string | null;
};

export type ReplyChannels = {
  email: ReplyChannelStatus;
  whatsapp: ReplyChannelStatus;
  call_outcomes: string[];
};

export type BulkLeadUpdate = {
  lead_ids: string[];
  assigned_to?: string;
  unassign?: boolean;
  status?: string;
  priority?: string;
};

export type LogCallInput = {
  direction: "inbound" | "outbound";
  outcome: string;
  notes?: string;
  duration_minutes?: number;
  follow_up_at?: string;
};

/** Human copy for a disabled reply channel (composer explains *why*). */
export function replyDisabledReason(reason: string | null | undefined): string {
  switch (reason) {
    case "email_reply_transport_not_configured":
      return "Email replies are off — set LEAD_REPLY_EMAIL_TRANSPORT (zeptomail or zoho_smtp).";
    case "zeptomail_token_missing":
      return "ZeptoMail token missing on the API.";
    case "zoho_smtp_credentials_missing":
      return "Zoho SMTP needs ZOHO_MAIL_USER + ZOHO_MAIL_APP_PASSWORD.";
    case "whatsapp_cloud_disabled":
      return "WhatsApp Cloud API is off (WHATSAPP_CLOUD_ENABLED=false). Reply from the WhatsApp Business app.";
    case "whatsapp_cloud_not_configured":
      return "WhatsApp Cloud API token / phone number id not set.";
    case "lead_has_no_whatsapp_number":
      return "This lead has no WhatsApp number.";
    case "outside_24h_service_window":
      return "Outside WhatsApp's 24-hour window — the lead has to message first (or use a template).";
    case "lead_has_no_email":
      return "This lead has no email address.";
    case "suppressed":
      return "Do-not-contact: this lead unsubscribed or is suppressed.";
    default:
      return reason ? reason.replace(/_/g, " ") : "Not available.";
  }
}

/** Minutes until (positive) or since (negative) the first-response SLA. */
export function slaMinutesLeft(lead: Pick<Lead, "sla_first_response_due_at">, now = Date.now()) {
  if (!lead.sla_first_response_due_at) return null;
  const due = new Date(lead.sla_first_response_due_at).getTime();
  if (Number.isNaN(due)) return null;
  return Math.round((due - now) / 60_000);
}

export function formatSla(minutes: number): string {
  const abs = Math.abs(minutes);
  const text = abs >= 60 ? `${Math.floor(abs / 60)}h ${abs % 60}m` : `${abs}m`;
  return minutes >= 0 ? `${text} left` : `${text} over`;
}

export type LeadQuote =
  | { available: false; reason: string }
  | {
      available: true;
      amount_cents: number;
      amount_display: string;
      pricing: "retail" | "merchant";
      vehicle_class: string;
      vehicle_label: string;
      pickup_fsa: string;
      dropoff_fsa: string;
      parcel_count: number;
      distance_km: number | null;
      lines: { label: string; amount_cents: number }[];
      tax_cents: number;
      booking_url: string;
      note: string;
    };

export type LeadFitScore = {
  score: number;
  reasons: { label: string; points: number }[];
  version: string;
};

export type LeadDraft = {
  channel: "email" | "whatsapp";
  subject: string | null;
  body: string;
  template: string;
  with_quote: boolean;
  source: "template" | "template+ai";
};

export type ReplyPrefill = {
  channel: "email" | "whatsapp";
  subject?: string | null;
  body: string;
  attachQuote: boolean;
  nonce: number;
};

export type SpeedWindow = {
  days: number;
  leads: number;
  answered: number;
  median_first_reply_minutes: number | null;
  answered_within_5m_pct: number | null;
  quoted: number;
  quote_to_booking_pct: number | null;
  booked: number;
  booking_to_repeat_pct: number | null;
  win_rate_by_channel: { channel: string; leads: number; won: number; lost: number; win_rate: number | null }[];
};

export type LeadSpeed = { generated_at: string; windows: SpeedWindow[] };

export type LeadWeeklySummary = {
  won: number;
  lost: number;
  win_rate: number | null;
  by_channel: { channel: string; won: number; lost: number; win_rate: number | null }[];
  lost_reasons: { reason: string; count: number }[];
};

/** Digits for tel:/wa.me (10-digit NANP → 1 prefix). */
export function dialDigits(phone: string | null | undefined): string {
  const d = String(phone ?? "").replace(/\D/g, "");
  return d.length === 10 ? `1${d}` : d;
}

export const leadsApi = {
  async replyChannels(token: string, leadId?: string): Promise<ReplyChannels> {
    const path = leadId
      ? `/v1/admin/leads/${encodeURIComponent(leadId)}/reply-channels`
      : "/v1/admin/leads/reply-channels";
    return adminFetch<ReplyChannels>(path, token);
  },

  async reply(
    token: string,
    leadId: string,
    body: { channel: "email" | "whatsapp"; body: string; subject?: string; attach_quote?: boolean }
  ): Promise<{ id: string; channel: string; status: string; to?: string }> {
    return adminFetch(`/v1/admin/leads/${encodeURIComponent(leadId)}/reply`, token, {
      method: "POST",
      body: JSON.stringify(body),
      timeoutMs: 45_000,
    });
  },

  async quote(token: string, leadId: string): Promise<LeadQuote> {
    return adminFetch(`/v1/admin/leads/${encodeURIComponent(leadId)}/quote`, token, { timeoutMs: 30_000 });
  },

  async fitScore(token: string, leadId: string): Promise<LeadFitScore> {
    return adminFetch(`/v1/admin/leads/${encodeURIComponent(leadId)}/score`, token);
  },

  /** Template draft (optional AI polish). Only fills the composer — never sends. */
  async draft(
    token: string,
    leadId: string,
    channel: "email" | "whatsapp",
    withQuote: boolean
  ): Promise<LeadDraft> {
    const q = new URLSearchParams({ channel, with_quote: String(withQuote) });
    return adminFetch(`/v1/admin/leads/${encodeURIComponent(leadId)}/draft?${q}`, token, {
      timeoutMs: 30_000,
    });
  },

  async rescore(token: string): Promise<{ rescored: number }> {
    return adminFetch(`/v1/admin/leads/rescore`, token, { method: "POST", timeoutMs: 60_000 });
  },

  async markLost(token: string, leadId: string, reason: string): Promise<{ status: string }> {
    return adminFetch(`/v1/admin/leads/${encodeURIComponent(leadId)}/lost`, token, {
      method: "POST",
      body: JSON.stringify({ reason }),
    });
  },

  async speed(token: string): Promise<LeadSpeed> {
    return adminFetch("/v1/admin/leads/speed", token);
  },

  async weeklySummary(token: string): Promise<LeadWeeklySummary> {
    return adminFetch("/v1/admin/leads/weekly-summary", token);
  },

  async logCall(
    token: string,
    leadId: string,
    body: LogCallInput
  ): Promise<{ id: string; status: string; task_id: string | null }> {
    return adminFetch(`/v1/admin/leads/${encodeURIComponent(leadId)}/log-call`, token, {
      method: "POST",
      body: JSON.stringify(body),
    });
  },

  async bulkUpdate(
    token: string,
    body: BulkLeadUpdate
  ): Promise<{ updated: number; missing: number }> {
    return adminFetch("/v1/admin/leads/bulk", token, {
      method: "POST",
      body: JSON.stringify(body),
    });
  },

  /** CSV of the current filter, or of `ids` when given. Returns a Blob to download. */
  async exportCsv(token: string, filters: LeadFilters, ids?: string[]): Promise<Blob> {
    const params = new URLSearchParams(
      buildLeadFiltersQuery({ ...filters, limit: undefined, offset: undefined }).slice(1)
    );
    params.delete("sort");
    for (const id of ids ?? []) params.append("ids", id);
    const bearer = token && token !== STAFF_COOKIE_TOKEN ? token : STAFF_COOKIE_TOKEN;
    const res = await fetch(`/api/porterchain/v1/admin/leads/export.csv?${params.toString()}`, {
      credentials: "include",
      headers: { Authorization: `Bearer ${bearer}` },
    });
    if (!res.ok) throw new Error(`export_failed_${res.status}`);
    return res.blob();
  },

  async list(
    token: string,
    filters: LeadFilters = {}
  ): Promise<{ items: Lead[]; total: number; limit: number; offset: number }> {
    const page = await adminFetch<{
      items: unknown[];
      total: number;
      limit: number;
      offset: number;
    }>(`/v1/admin/leads${qs(filters)}`, token);
    return {
      items: z.array(leadSchema).parse(page.items) as Lead[],
      total: page.total,
      limit: page.limit,
      offset: page.offset,
    };
  },

  async metrics(token: string, days = 30): Promise<LeadMetrics> {
    return adminFetch<LeadMetrics>(`/v1/admin/leads/metrics?days=${days}`, token);
  },

  async pipeline(
    token: string,
    opts: { search?: string; card_type?: string } = {}
  ): Promise<
    Array<{
      stage: string;
      cards: Array<{
        type: string;
        id: string;
        title: string;
        company_name: string | null;
        value_cents: number;
        secondary: string | null;
        channel?: string | null;
        score?: number | null;
        has_draft?: boolean;
        sla_breached?: boolean;
        nurture?: boolean;
      }>;
      count: number;
      value_cents: number;
      hidden: number;
      lead_count: number;
      deal_count: number;
    }>
  > {
    const params = new URLSearchParams();
    if (opts.search) params.set("search", opts.search);
    if (opts.card_type) params.set("card_type", opts.card_type);
    const q = params.toString();
    return adminFetch(`/v1/admin/leads/pipeline${q ? `?${q}` : ""}`, token);
  },

  async resolveMerge(token: string, id: string, action: "accept" | "reject"): Promise<Lead> {
    const row = await adminFetch<unknown>(`/v1/admin/leads/${id}/merge`, token, {
      method: "POST",
      body: JSON.stringify({ action }),
    });
    return leadSchema.parse(row) as Lead;
  },

  async detail(token: string, id: string): Promise<Lead> {
    const row = await adminFetch<unknown>(`/v1/admin/leads/${id}`, token);
    return leadSchema.parse(row) as Lead;
  },

  async get360(token: string, id: string): Promise<Lead360> {
    const row = await adminFetch<unknown>(`/v1/admin/leads/${id}/360`, token);
    return lead360Schema.parse(row);
  },

  async create(
    token: string,
    body: {
      company_name: string;
      primary_contact_name?: string;
      email?: string;
      phone?: string;
      source?: string;
      channel?: string;
      intent_type?: string;
      decision_status?: string;
      priority?: string;
      internal_notes?: string;
      referred_by_merchant_id?: string;
      consent?: {
        marketing?: boolean;
        sms?: boolean;
        whatsapp?: boolean;
        legal_basis?: "consent" | "legitimate_interest" | "contract";
        captured_at?: string;
      };
    }
  ): Promise<Lead> {
    const row = await adminFetch<unknown>(`/v1/admin/leads`, token, {
      method: "POST",
      body: JSON.stringify(body),
    });
    return leadSchema.parse(row) as Lead;
  },

  async update(
    token: string,
    id: string,
    patch: {
      status?: string;
      priority?: string;
      decision_status?: string;
      intent_type?: string;
      internal_notes?: string;
      primary_contact_name?: string | null;
      email?: string | null;
      phone?: string | null;
      consent?: Record<string, unknown>;
      estimated_deliveries_per_month?: number | null;
      current_logistics_provider?: string | null;
      preferred_vehicle?: string | null;
    }
  ): Promise<Lead> {
    const row = await adminFetch<unknown>(`/v1/admin/leads/${id}`, token, {
      method: "PATCH",
      body: JSON.stringify(patch),
    });
    return leadSchema.parse(row) as Lead;
  },

  async remove(token: string, id: string): Promise<void> {
    await adminFetch<void>(`/v1/admin/leads/${id}`, token, { method: "DELETE" });
  },

  async privacyExport(token: string, id: string): Promise<Record<string, unknown>> {
    return adminFetch(`/v1/admin/leads/${id}/privacy/export`, token);
  },

  async privacyDeleteRequest(
    token: string,
    id: string,
    reason?: string
  ): Promise<{ lead_id: string; status: string; reference: string }> {
    const q = reason ? `?reason=${encodeURIComponent(reason)}` : "";
    return adminFetch(`/v1/admin/leads/${id}/privacy/delete-request${q}`, token, {
      method: "POST",
    });
  },

  async privacyErase(token: string, id: string): Promise<{ lead_id: string; status: string }> {
    return adminFetch(`/v1/admin/leads/${id}/privacy/erase`, token, { method: "POST" });
  },

  async listSuppressions(
    token: string,
    opts: { limit?: number; offset?: number } = {}
  ): Promise<{
    items: Array<{
      id: string;
      hash_kind: string;
      value_hash: string;
      source: string;
      lead_id: string | null;
      created_at: string | null;
    }>;
    total: number;
    limit: number;
    offset: number;
  }> {
    const params = new URLSearchParams();
    if (opts.limit != null) params.set("limit", String(opts.limit));
    if (opts.offset != null) params.set("offset", String(opts.offset));
    const q = params.toString();
    return adminFetch(`/v1/admin/leads/suppressions${q ? `?${q}` : ""}`, token);
  },

  async deleteSuppression(token: string, id: string): Promise<void> {
    await adminFetch<void>(`/v1/admin/leads/suppressions/${id}`, token, { method: "DELETE" });
  },

  async privacyRopa(token: string): Promise<{
    controller: string;
    contact: string;
    primary_residency: string;
    multi_region: boolean;
    activities: Array<{
      activity: string;
      purpose: string;
      legal_bases: string[];
      categories: string[];
      systems: string[];
      recipients: string[];
      retention: string;
      residency: string;
    }>;
    notes: string;
  }> {
    return adminFetch(`/v1/admin/leads/privacy/ropa`, token);
  },

  async conversations(
    token: string,
    id: string
  ): Promise<
    Array<{
      id: string;
      channel: string;
      status: string;
      messages: Array<{ id: string; direction: string; body: string; occurred_at: string | null }>;
    }>
  > {
    return adminFetch(`/v1/admin/leads/${id}/conversations`, token);
  },

  async identities(
    token: string,
    id: string
  ): Promise<
    Array<{ id: string; kind: string; value_normalized: string; raw_value: string | null }>
  > {
    return adminFetch(`/v1/admin/leads/${id}/identities`, token);
  },

  /** M-19: Lead → company (+ deal); optional merchant seat (ONBOARDING). */
  async convert(
    token: string,
    id: string,
    body: {
      to_merchant?: boolean;
      create_deal?: boolean;
      outcome?: "merchant" | "retail_customer" | "driver_partner";
    } = {}
  ): Promise<{
    company_id?: string;
    deal_id?: string | null;
    to_merchant?: boolean;
    outcome?: string;
    customer_id?: string;
    merchant?: { merchant_id: string; created: boolean };
    driver_partner?: { queued: boolean; hint?: string; driver_id?: string };
  }> {
    return adminFetch(`/v1/admin/leads/${id}/convert`, token, {
      method: "POST",
      body: JSON.stringify({
        create_deal: body.create_deal ?? true,
        to_merchant: body.to_merchant ?? false,
        outcome: body.outcome,
      }),
    });
  },

  async assist(
    token: string,
    id: string
  ): Promise<{
    summary: string;
    draft_reply: string;
    suggested_decision_status: string;
    next_questions: string[];
    risks: string[];
    source: string;
    contract?: { mode: string; writes_require_confirm: boolean };
    proposals: Array<{ id: string; type: string; title: string; body: string }>;
  }> {
    return adminFetch(`/v1/admin/leads/${id}/assist`, token);
  },

  async assistDecide(
    token: string,
    id: string,
    body: {
      proposal_id: string;
      decision: "accept" | "reject";
      draft_reply?: string;
      decision_status?: string;
    }
  ): Promise<{ ok: boolean }> {
    return adminFetch(`/v1/admin/leads/${id}/assist/decide`, token, {
      method: "POST",
      body: JSON.stringify(body),
    });
  },

  async today(token: string): Promise<{
    ready: Array<Record<string, unknown>>;
    followups: Array<Record<string, unknown>>;
    interested: Array<Record<string, unknown>>;
    counts: {
      ready: number;
      followups: number;
      interested: number;
      ready_contact?: { total: number; with_phone: number; without_phone: number };
      followups_contact?: { total: number; with_phone: number; without_phone: number };
      interested_contact?: { total: number; with_phone: number; without_phone: number };
    };
  }> {
    return adminFetch(`/v1/admin/leads/today`, token);
  },

  async agentActivity(token: string): Promise<LeadAgentActivity> {
    return adminFetch(`/v1/admin/leads/agent`, token);
  },

  async dialScripts(token: string, id: string): Promise<Record<string, unknown>> {
    return adminFetch(`/v1/admin/leads/${id}/dial-scripts`, token);
  },

  async callDisposition(
    token: string,
    id: string,
    body: {
      outcome: string;
      notes?: string;
      loss_reason?: string;
      next_action?: string;
      follow_up_at?: string;
      queue?: string;
      contact_name?: string;
      email?: string;
      phone?: string;
      consent_marketing?: boolean;
    }
  ): Promise<{
    lead: Record<string, unknown>;
    outcome: string;
    status: string;
    task_id?: string | null;
    next_lead_id?: string | null;
  }> {
    return adminFetch(`/v1/admin/leads/${id}/call-disposition`, token, {
      method: "POST",
      body: JSON.stringify(body),
    });
  },

  async sendEmail(
    token: string,
    id: string,
    template_key = "lead_outbound_followup"
  ): Promise<{ ok: boolean; template_key: string }> {
    return adminFetch(`/v1/admin/leads/${id}/send-email`, token, {
      method: "POST",
      body: JSON.stringify({ template_key }),
    });
  },

  async welcome(
    token: string,
    id: string,
    body: { force?: boolean; dry_run?: boolean } = {}
  ): Promise<Record<string, unknown>> {
    return adminFetch(`/v1/admin/leads/${id}/welcome`, token, {
      method: "POST",
      body: JSON.stringify(body),
    });
  },

  async nba(token: string, id: string): Promise<Record<string, unknown>> {
    return adminFetch(`/v1/admin/leads/${id}/nba`, token);
  },

  async calendar(
    token: string,
    params: { due_after?: string; due_before?: string } = {}
  ): Promise<import("@/lib/crm").Task[]> {
    const search = new URLSearchParams();
    if (params.due_after) search.set("due_after", params.due_after);
    if (params.due_before) search.set("due_before", params.due_before);
    const q = search.toString();
    return adminFetch(`/v1/admin/leads/calendar${q ? `?${q}` : ""}`, token);
  },

  async referralCredits(
    token: string,
    params: { merchant_id?: string; status?: string } = {}
  ): Promise<
    Array<{
      id: string;
      merchant_id: string;
      lead_id: string;
      company_id: string | null;
      amount_cents: number;
      currency: string;
      status: string;
      created_at: string | null;
    }>
  > {
    const search = new URLSearchParams();
    if (params.merchant_id) search.set("merchant_id", params.merchant_id);
    if (params.status) search.set("status", params.status);
    const q = search.toString();
    return adminFetch(`/v1/admin/leads/referral-credits${q ? `?${q}` : ""}`, token);
  },
};

export function leadIntent(lead: Lead): string | null {
  const cf = lead.custom_fields ?? {};
  const intent = cf.intent;
  return typeof intent === "string" ? intent : null;
}

export function leadForm(lead: Lead): string | null {
  const cf = lead.custom_fields ?? {};
  const form = cf.form;
  return typeof form === "string" ? form : null;
}

export function leadMessage(lead: Lead): string | null {
  const cf = lead.custom_fields ?? {};
  const fromCustom = cf.message;
  if (typeof fromCustom === "string" && fromCustom.trim()) return fromCustom;
  return lead.internal_notes;
}

export const STATUS_TONES: Record<string, string> = {
  new: "sky",
  replied: "blue",
  quoted: "violet",
  won: "green",
  lost: "slate",
  archived: "slate",
};

export const PRIORITY_TONES: Record<string, string> = {
  low: "slate",
  medium: "blue",
  high: "amber",
  urgent: "red",
};

export const DECISION_TONES: Record<string, string> = {
  new: "sky",
  researching: "blue",
  questions_open: "amber",
  objection: "red",
  ready_to_convert: "green",
  deferred: "violet",
  lost: "slate",
  converted: "teal",
};
