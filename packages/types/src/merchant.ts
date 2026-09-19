/** Shared merchant order wire fields (keep in sync with MerchantOrderResponse). */

export type MerchantOrder = {
  order_id: string;
  order_number: string;
  tracking_number: string;
  state: string;
  amount_cents: number;
  currency: string;
  scheduled_at: string;
  pickup: Record<string, unknown>;
  dropoff: Record<string, unknown>;
  internal_reference?: string | null;
  purchase_order_number?: string | null;
  cost_centre?: string | null;
  /** True when the booking is sandbox/test capacity (no live dispatch). */
  is_sandbox: boolean;
  created_at: string;
};
