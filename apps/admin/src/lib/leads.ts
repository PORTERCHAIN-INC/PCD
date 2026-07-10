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

export const LEAD_SOURCES = [
  "website_business",
  "website_contact",
  "website_quote",
  "website_demo",
  "website_newsletter",
  "website_booking",
] as const;

export type LeadFilters = {
  status?: string;
  priority?: string;
  source?: string;
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
  custom_fields: z.record(z.string(), z.unknown()).nullable(),
  created_at: z.string(),
  updated_at: z.string(),
});

function qs(filters: LeadFilters): string {
  const params = new URLSearchParams();
  if (filters.status) params.set("status", filters.status);
  if (filters.priority) params.set("priority", filters.priority);
  if (filters.source) params.set("source", filters.source);
  if (filters.search) params.set("search", filters.search);
  const q = params.toString();
  return q ? `?${q}` : "";
}

export const leadsApi = {
  async list(token: string, filters: LeadFilters = {}): Promise<Lead[]> {
    const rows = await adminFetch<unknown[]>(`/v1/admin/leads${qs(filters)}`, token);
    return z.array(leadSchema).parse(rows);
  },

  async detail(token: string, id: string): Promise<Lead> {
    const row = await adminFetch<unknown>(`/v1/admin/leads/${id}`, token);
    return leadSchema.parse(row);
  },

  async update(
    token: string,
    id: string,
    patch: { status?: string; priority?: string; internal_notes?: string }
  ): Promise<Lead> {
    const row = await adminFetch<unknown>(`/v1/admin/leads/${id}`, token, {
      method: "PATCH",
      body: JSON.stringify(patch),
    });
    return leadSchema.parse(row);
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
