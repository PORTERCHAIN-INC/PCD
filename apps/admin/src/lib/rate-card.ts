import { adminFetch } from "@/lib/api";

/** Doc 72: the one Standard card + org Custom pricing (API under /v1/pricing). */
export type RateCardLines = {
  currency: string;
  hst_rate: number;
  dim_factor_cm3_per_kg: number;
  zone_adder_cents: Record<string, number>;
  bands: Record<string, { label: string; max_kg: number; max_side_cm: number; z1_cents: number }>;
  furniture_classes: Record<
    string,
    { label: string; z1_cents: number; two_person_included?: boolean }
  >;
  add_ons: Record<
    string,
    { label: string; cents: number; b2b_only?: boolean; retired?: boolean; alias_of?: string }
  >;
  guardrails?: { min_pct: number; max_pct: number };
  [k: string]: unknown;
};

export type RateCardVersion = {
  id: string;
  version: number;
  status: "draft" | "published" | "retired";
  notes: string | null;
  effective_from: string | null;
  published_at: string | null;
  lines?: RateCardLines;
};

export type StandardCard = {
  code: string;
  name: string;
  published: RateCardVersion | null;
  draft: RateCardVersion | null;
  versions: RateCardVersion[];
  can_edit: boolean;
};

export type PreviewRow = {
  sample: string;
  standard_cents: number;
  custom_cents: number;
  hst_cents: number;
};

export type OrgPricing = {
  org_id: string;
  mode: "standard" | "custom";
  preset_pct: number | null;
  preset_per_stop_cents: number | null;
  flat_parcel_cents: number | null;
  band_overrides: Record<string, number>;
  contract_document_id?: string | null;
  red_reason?: string | null;
  preview?: PreviewRow[];
};

export type OrgPricingBody = {
  mode: "standard" | "custom";
  preset_pct?: number | null;
  preset_per_stop_cents?: number | null;
  flat_parcel_cents?: number | null;
  band_overrides?: Record<string, number>;
  contract_document_id?: string | null;
  red_reason?: string | null;
  reason?: string | null;
};

export type SentQuote = {
  id: string;
  token: string;
  email: string;
  total_cents: number;
  status: "sent" | "accepted" | "expired" | "void";
  expires_at: string;
  link?: string;
  delivery?: { sent: boolean; reason?: string };
};

export type QuoteItemInput = {
  kind?: string;
  weight_kg: number;
  length_cm?: number;
  width_cm?: number;
  height_cm?: number;
  qty?: number;
};

export type OrderAdjustments = {
  order_amount_cents: number;
  adjustments_cents: number;
  adjusted_total_cents: number;
  limit_cents: number;
  categories: string[];
  items: {
    id: string;
    cents: number;
    category: string;
    reason: string;
    actor_role: string | null;
    created_at: string | null;
  }[];
};

const post = (body: unknown) => ({ method: "POST", body: JSON.stringify(body) });

export const rateCardApi = {
  standard: (t: string) => adminFetch<StandardCard>("/v1/pricing/rate-cards/standard", t),
  saveDraft: (t: string, lines: RateCardLines, notes?: string) =>
    adminFetch<RateCardVersion>("/v1/pricing/rate-cards/standard/draft", t, post({ lines, notes })),
  preview: (t: string, lines: RateCardLines) =>
    adminFetch<{
      rows: PreviewRow[];
      live_rows: PreviewRow[];
      diff: Record<string, { from: unknown; to: unknown }>;
    }>("/v1/pricing/rate-cards/standard/preview", t, post({ lines })),
  publish: (t: string, reason: string) =>
    adminFetch<RateCardVersion>("/v1/pricing/rate-cards/standard/publish", t, post({ reason })),
  rollback: (t: string, version: number, reason: string) =>
    adminFetch<RateCardVersion>(
      "/v1/pricing/rate-cards/standard/rollback",
      t,
      post({ version, reason })
    ),
  org: (t: string, orgId: string) =>
    adminFetch<OrgPricing>(`/v1/pricing/orgs/${encodeURIComponent(orgId)}`, t),
  previewOrg: (t: string, orgId: string, body: OrgPricingBody) =>
    adminFetch<{ rows: PreviewRow[] }>(
      `/v1/pricing/orgs/${encodeURIComponent(orgId)}/preview`,
      t,
      post(body)
    ),
  sendQuote: (
    t: string,
    body: {
      email: string;
      items: QuoteItemInput[];
      zone: string;
      audience: "retail" | "b2b";
      org_id?: string;
      lead_id?: string;
    }
  ) => adminFetch<SentQuote>("/v1/pricing/quotes/send", t, post(body)),
  sentQuotes: (t: string, q: { org_id?: string; lead_id?: string } = {}) =>
    adminFetch<{ items: SentQuote[] }>(
      `/v1/pricing/quotes/sent?${new URLSearchParams(q as Record<string, string>)}`,
      t
    ),
  voidQuote: (t: string, id: string) =>
    adminFetch<SentQuote>(`/v1/pricing/quotes/${encodeURIComponent(id)}/void`, t, post({})),
  adjustments: (t: string, orderId: string) =>
    adminFetch<OrderAdjustments>(
      `/v1/pricing/orders/${encodeURIComponent(orderId)}/adjustments`,
      t
    ),
  addAdjustment: (
    t: string,
    orderId: string,
    body: { cents: number; category: string; reason: string }
  ) =>
    adminFetch<OrderAdjustments>(
      `/v1/pricing/orders/${encodeURIComponent(orderId)}/adjustments`,
      t,
      post(body)
    ),
  saveOrg: (t: string, orgId: string, body: OrgPricingBody) =>
    adminFetch<OrgPricing>(`/v1/pricing/orgs/${encodeURIComponent(orgId)}`, t, {
      method: "PUT",
      body: JSON.stringify(body),
    }),
};

/** Signed % change of custom vs standard, one decimal. */
export function pctChange(standard: number, custom: number): number {
  if (!standard) return 0;
  return Math.round(((custom - standard) * 1000) / standard) / 10;
}

/** Guardrail colour for the preview table (doc 72 §9.2: −30 % / +50 %). */
export function guardrailTone(pct: number, min = -30, max = 50): "ok" | "warn" | "blocked" {
  if (pct < min || pct > max) return "blocked";
  if (pct <= min + 5 || pct >= max - 5) return "warn";
  return "ok";
}

/** Dollar input ("17.50") to cents; null when not a number. */
export function dollarsToCents(v: string): number | null {
  const n = Number(v.replace(/[$,\s]/g, ""));
  return Number.isFinite(n) ? Math.round(n * 100) : null;
}

/** Hours left before a sent quote expires (0 when past). */
export function hoursLeft(expiresAt: string, now: number = Date.now()): number {
  return Math.max(0, Math.floor((new Date(expiresAt).getTime() - now) / 3_600_000));
}

/** Client mirror of the API rule: |cents| within the role limit and a reason of 5+ characters. */
export function adjustmentError(
  cents: number | null,
  reason: string,
  limit: number
): string | null {
  if (cents == null || cents === 0) return "Enter a non-zero amount";
  if (Math.abs(cents) > limit) return `Over your limit (${(limit / 100).toFixed(2)})`;
  if (reason.trim().length < 5) return "Add a reason (5+ characters)";
  return null;
}
