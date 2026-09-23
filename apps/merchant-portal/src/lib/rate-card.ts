export type MerchantRateCardVehicle = {
  id: string;
  label: string;
  base_cents: number;
  extra_km_cents: number;
  extra_pickup_cents: number;
  extra_drop_cents: number;
};

export type MerchantRateCard = {
  pricing_model: string;
  what_wins: string;
  vehicles: MerchantRateCardVehicle[];
  included_km: number;
  size_tiers: Array<{
    label?: string;
    surcharge_cents: number;
    max_length?: number | null;
    max_width?: number | null;
    max_height?: number | null;
    dimension_unit?: string;
    max_weight?: number | null;
    weight_unit?: string;
  }>;
  surcharges: {
    downtown: boolean;
    upper_zone: boolean;
    downtown_cents?: number;
    upper_zone_cents?: number;
  };
  liftgate_cents: number;
  fuel_surcharge_percent: number;
  schedule?: {
    fuel_surcharge_percent: number | null;
    fsa_miss: string;
    origin_pickup_cents: number;
    origin_pickup_vehicle_classes: string[];
    route_minimums_cents: Record<string, number>;
    compact: { enabled: boolean; route_minimum_cents: number };
    size_match: string;
  };
  tax: { hst_percent: number; tax_included: boolean };
  weight: { threshold_kg: number; cents_per_kg: number };
  fsa_rate_count: number;
  platform_fsa_rate_count: number;
  currency: string;
};

export function pricingModelLabel(model: string): string {
  if (model === "fsa") return "Ontario FSA flat rates";
  if (model === "distance") return "Distance and vehicle";
  return "Distance and vehicle";
}
