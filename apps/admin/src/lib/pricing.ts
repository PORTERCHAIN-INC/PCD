import { adminFetch } from "@/lib/api";

export type SimulateQuoteBody = {
  merchant_id?: string | null;
  channel?: string;
  vehicle_class?: string;
  distance_meters?: number;
  total_pickups?: number;
  total_drops?: number;
  weight_kg?: number | null;
  requires_liftgate?: boolean;
  pickup?: { lat?: number; lng?: number; formatted?: string; postal?: string };
  dropoff?: { lat?: number; lng?: number; formatted?: string; postal?: string };
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
};

export const pricingApi = {
  simulate: (token: string, body: SimulateQuoteBody) =>
    adminFetch<SimulateQuoteResult>("/v1/pricing/simulate", token, {
      method: "POST",
      body: JSON.stringify(body),
    }),
};
