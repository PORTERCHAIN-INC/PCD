import { z } from "zod";
import { adminFetch } from "@/lib/api";

export const VEHICLE_CLASSES = [
  "sedan",
  "suv",
  "pickup",
  "cargoVan",
  "highRoof",
  "box16",
  "box20",
] as const;

export const TARIFF_TYPES = [
  "vehicle",
  "zone",
  "distance",
  "weight",
  "merchant",
  "contract",
  "express",
  "same_day",
  "scheduled",
  "fuel",
  "rush",
  "holiday",
  "weekend",
  "after_hours",
  "cancellation",
  "public",
] as const;

export const RULE_STATUSES = ["draft", "pending_approval", "approved", "published", "archived"] as const;

const tariffSchema = z.object({
  id: z.string(),
  name: z.string(),
  tariff_type: z.string(),
  vehicle_class: z.string().nullable().optional(),
  zone: z.string().nullable().optional(),
  merchant_id: z.string().nullable().optional(),
  merchant_name: z.string().nullable().optional(),
  base_cents: z.number(),
  per_km_cents: z.number(),
  fuel_surcharge_percent: z.number(),
  is_active: z.boolean(),
  status: z.string(),
  version: z.number(),
  priority: z.number(),
  effective_from: z.string().nullable().optional(),
  effective_to: z.string().nullable().optional(),
  created_at: z.string().nullable().optional(),
});

export type TariffRow = z.infer<typeof tariffSchema>;

const promotionSchema = z.object({
  id: z.string(),
  code: z.string(),
  promotion_type: z.string(),
  merchant_id: z.string().nullable().optional(),
  merchant_name: z.string().nullable().optional(),
  discount_percent: z.number().nullable().optional(),
  discount_cents: z.number().nullable().optional(),
  is_active: z.boolean(),
  expires_at: z.string().nullable().optional(),
  status: z.string(),
  created_at: z.string().nullable().optional(),
});

export type PromotionRow = z.infer<typeof promotionSchema>;

const zoneSchema = z.object({
  id: z.string(),
  code: z.string(),
  name: z.string(),
  multiplier: z.number(),
  is_active: z.boolean(),
  bounds: z.record(z.string(), z.unknown()).optional(),
  created_at: z.string().nullable().optional(),
});

export type ZoneRow = z.infer<typeof zoneSchema>;

const contractSchema = z.object({
  id: z.string(),
  merchant_id: z.string(),
  merchant_name: z.string().nullable().optional(),
  name: z.string(),
  minimum_monthly_commitment_cents: z.number(),
  is_active: z.boolean(),
  effective_from: z.string().nullable().optional(),
  effective_to: z.string().nullable().optional(),
  created_at: z.string().nullable().optional(),
});

export type ContractRow = z.infer<typeof contractSchema>;

export type PricingDashboard = {
  active_pricing_rules: number;
  merchant_contracts: number;
  vehicle_pricing_rules: number;
  zone_pricing_rules: number;
  distance_pricing_rules: number;
  weight_pricing_rules: number;
  fuel_surcharge_percent: number;
  tax_hst_percent: number;
  active_coupons: number;
  active_promotions: number;
  revenue_forecast_cents: number;
  monthly_quotes: number;
  recent_changes: Array<Record<string, unknown>>;
  upcoming_scheduled: Array<Record<string, unknown>>;
  conflict_count: number;
};

export type TariffFilters = {
  tariff_type?: string;
  vehicle_class?: string;
  merchant_id?: string;
  zone?: string;
  status?: string;
  search?: string;
};

export type SimulateRequest = {
  pickup: { lat?: number; lng?: number; formatted: string };
  dropoff: { lat?: number; lng?: number; formatted: string };
  vehicle_class: string;
  package_type?: string;
  service_type?: string;
  weight_kg?: number;
  merchant_id?: string;
  promo_code?: string;
  distance_meters?: number;
  channel?: string;
};

export type SimulateResult = {
  base_cents: number;
  distance_cents: number;
  vehicle_cents: number;
  weight_cents: number;
  fuel_cents: number;
  tax_cents: number;
  discount_cents: number;
  subtotal_cents: number;
  final_cents: number;
  currency: string;
  items: Array<{ code: string; label: string; amount_cents: number }>;
  metadata?: Record<string, unknown>;
};

const B = "/v1/admin/pricing";

function qs(filters?: TariffFilters): string {
  if (!filters) return "";
  const p = new URLSearchParams();
  Object.entries(filters).forEach(([k, v]) => {
    if (v) p.set(k, v);
  });
  const q = p.toString();
  return q ? `?${q}` : "";
}

export const pricingApi = {
  dashboard: (token: string) => adminFetch<PricingDashboard>(`${B}/dashboard`, token),
  reports: (token: string) => adminFetch<Record<string, unknown>>(`${B}/reports`, token),
  conflicts: (token: string) => adminFetch<Array<Record<string, unknown>>>(`${B}/conflicts`, token),
  tariffs: async (token: string, filters?: TariffFilters) => {
    const raw = await adminFetch<unknown[]>(`${B}/tariffs${qs(filters)}`, token);
    return z.array(tariffSchema).parse(raw);
  },
  createTariff: (token: string, body: Record<string, unknown>) =>
    adminFetch<TariffRow>(`${B}/tariffs`, token, { method: "POST", body: JSON.stringify(body) }),
  publishTariff: (token: string, id: string) =>
    adminFetch<TariffRow>(`${B}/tariffs/${id}/publish`, token, { method: "POST" }),
  promotions: async (token: string) => {
    const raw = await adminFetch<unknown[]>(`${B}/promotions`, token);
    return z.array(promotionSchema).parse(raw);
  },
  zones: async (token: string) => {
    const raw = await adminFetch<unknown[]>(`${B}/zones`, token);
    return z.array(zoneSchema).parse(raw);
  },
  contracts: async (token: string) => {
    const raw = await adminFetch<unknown[]>(`${B}/contracts`, token);
    return z.array(contractSchema).parse(raw);
  },
  tax: (token: string) => adminFetch<Record<string, unknown>>(`${B}/tax`, token),
  updateTax: (token: string, body: Record<string, unknown>) =>
    adminFetch<Record<string, unknown>>(`${B}/tax`, token, { method: "PUT", body: JSON.stringify(body) }),
  fuel: (token: string) => adminFetch<Record<string, unknown>>(`${B}/fuel`, token),
  updateFuel: (token: string, body: Record<string, unknown>) =>
    adminFetch<Record<string, unknown>>(`${B}/fuel`, token, { method: "PUT", body: JSON.stringify(body) }),
  simulate: (token: string, body: SimulateRequest) =>
    adminFetch<SimulateResult>(`${B}/simulate`, token, { method: "POST", body: JSON.stringify(body) }),
};

export const STATUS_STYLES: Record<string, string> = {
  draft: "bg-gray-100 text-gray-600",
  pending_approval: "bg-amber-100 text-amber-800",
  approved: "bg-blue-100 text-blue-700",
  published: "bg-green-100 text-green-700",
  archived: "bg-gray-100 text-gray-500",
};

export function exportTariffsCsv(rows: TariffRow[], filename = "pricing-rules.csv") {
  const headers = ["name", "tariff_type", "vehicle_class", "zone", "merchant_name", "base_cents", "per_km_cents", "status", "version"];
  const lines = [
    headers.join(","),
    ...rows.map((r) =>
      headers.map((h) => {
        const v = r[h as keyof TariffRow];
        const s = v == null ? "" : String(v);
        return s.includes(",") ? `"${s.replace(/"/g, '""')}"` : s;
      }).join(",")
    ),
  ];
  const blob = new Blob([lines.join("\n")], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
