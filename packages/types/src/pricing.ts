/** Human label for a merchant's pricing_model (fsa | distance). */
export function pricingModelLabel(model: string): string {
  return model === "fsa" ? "Ontario FSA flat rates" : "Distance and vehicle";
}

/**
 * Compact (sedan / SUV) stop-banding defaults. Mirrors
 * porterchain_pricing.policy COMPACT_DEFAULT_* — a test fails if they drift.
 * Values pending the commercial rate PDF; change both together.
 */
export const COMPACT_SCHEDULE_DEFAULTS = {
  parcels_per_stop: 3,
  stop_rates_cents: [
    { max_stops: 4, cents: 1000 },
    { max_stops: null, cents: 600 },
  ],
  route_minimum_cents: 5000,
} as const;

/** Matches porterchain_pricing.gta_rate.DEFAULT_DOWNTOWN_FEE_CAD. */
export const DEFAULT_DOWNTOWN_FEE_CAD = 25;
