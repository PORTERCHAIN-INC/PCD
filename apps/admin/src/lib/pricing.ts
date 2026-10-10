import { adminFetch } from "@/lib/api";

export type SimulateQuoteBody = {
  merchant_id?: string | null;
  channel?: string;
  vehicle_class?: string;
  distance_meters?: number;
  use_typed_distance?: boolean;
  total_pickups?: number;
  total_drops?: number;
  weight_kg?: number | null;
  requires_liftgate?: boolean;
  parcel_count?: number | null;
  pickup?: { lat?: number; lng?: number; formatted?: string; postal?: string };
  dropoff?: { lat?: number; lng?: number; formatted?: string; postal?: string };
  extra_pickups?: Array<{ formatted?: string; postal?: string }>;
  extra_drops?: Array<{ formatted?: string; postal?: string }>;
  smart_overrides?: Record<string, unknown> | null;
};

/** Smart route quote (new engine) shown next to the current price. */
export type SmartQuote = {
  total_cents: number;
  current_cents: number | null;
  shape: string;
  unit: string;
  sequence: string[];
  route_distance: number;
  drive_minutes: number;
  lines: Array<{ code: string; label: string; cents: number }>;
  marginal_stops: Array<{
    stop: string;
    kind: string;
    insertion_km: number;
    insertion_cents: number;
  }>;
  confidence: number;
  matrix_source: string;
  notes: string[];
  custom_quote: boolean;
  error?: string;
};

export type SimulateQuoteResult = {
  final_cents: number;
  subtotal_cents: number;
  tax_cents: number;
  base_cents: number;
  currency: string;
  pricing_model: string | null;
  pricing_model_requested: string | null;
  items: Array<{ code: string; label: string; amount_cents: number }>;
  metadata: Record<string, unknown>;
  what_won: string;
  smart?: SmartQuote | null;
  margin?: {
    status: "ok" | "thin" | "below_cost";
    price_cents: number;
    cost_cents: number;
    margin_cents: number;
    margin_pct: number;
    driver_minutes: number;
    labour_cents: number;
    vehicle_cents: number;
    insurance_cents?: number;
    explain: string;
  } | null;
  distance_flag?: string | null;
};

/** Admin-editable cost inputs behind the margin check (Settings key pricing_margin_estimates). */
export type MarginEstimates = {
  driver_hourly_cents: number;
  avg_speed_kmh: number;
  pickup_minutes: number;
  drop_minutes: number;
  deadhead_factor: number;
  vehicle_cents_per_km: number;
  thin_margin_pct: number;
  working_days_per_month: number;
  working_hours_per_day: number;
  insurance_monthly_cents: Record<string, number>;
};

export const pricingApi = {
  simulate: (token: string, body: SimulateQuoteBody) =>
    adminFetch<SimulateQuoteResult>("/v1/pricing/simulate", token, {
      method: "POST",
      body: JSON.stringify(body),
    }),
};
