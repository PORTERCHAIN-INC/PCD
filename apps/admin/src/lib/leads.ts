import { z } from "zod";
import { adminFetch } from "@/lib/api";
import type { Lead } from "@/lib/crm";

export const LEAD_STATUSES = [
  "new",
  "contacted",
  "qualified",
  "unqualified",
  "nurturing",
  "converted",
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
  search?: string;
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
  created_at: z.string(),
  updated_at: z.string(),
});

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
  if (filters.search) params.set("search", filters.search);
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

export const leadsApi = {
  async list(token: string, filters: LeadFilters = {}): Promise<Lead[]> {
    const rows = await adminFetch<unknown[]>(`/v1/admin/leads${qs(filters)}`, token);
    return z.array(leadSchema).parse(rows) as Lead[];
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
  contacted: "blue",
  qualified: "green",
  unqualified: "slate",
  nurturing: "violet",
  converted: "teal",
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
