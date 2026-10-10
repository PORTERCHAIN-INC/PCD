import { adminFetch } from "@/lib/api";

export type MarginGroup = {
  key: string;
  stops: number;
  revenue_cents: number;
  margin_cents: number;
  margin_pct: number | null;
  name?: string;
};

export type OpsAnalytics = {
  days: number;
  generated_at: string;
  kpis: {
    orders: number;
    delivered_stops: number;
    revenue_cents: number;
    margin_cents: number;
    margin_pct: number | null;
    cost_per_stop_cents: number | null;
    on_time_pct: number | null;
    on_time_sample: number;
    failed: number;
    failed_pct: number | null;
    routes: number;
    fill_pct: number | null;
    estimated_cost_share: number;
  };
  margin_by: {
    merchant: MarginGroup[];
    fsa: MarginGroup[];
    vehicle: MarginGroup[];
    route: Array<MarginGroup & { route_id: string; cost_source: string }>;
  };
  drivers: Array<{
    driver_id: string;
    name?: string;
    routes: number;
    stops: number;
    revenue_cents: number;
    stops_per_route: number;
  }>;
  trend: Array<{ day: string; stops: number; revenue_cents: number; margin_cents: number }>;
  forecast: Array<{
    fsa: string;
    next7_total: number;
    days: Array<{ day: string; expected: number }>;
  }>;
  failed_recent: Array<{ order_id: string; order_number: string; state: string; fsa: string }>;
};

export const analyticsApi = {
  ops: (t: string, days = 30) =>
    adminFetch<OpsAnalytics>(`/v1/admin/analytics/ops?days=${days}`, t),
};
