import { adminFetch } from "@/lib/api";
import type { Activity, Task } from "@/lib/crm";

export type DriverRow = {
  id: string;
  full_name: string;
  email: string;
  phone: string | null;
  photo_url: string | null;
  status: string;
  availability: string;
  is_online: boolean;
  vehicle: string | null;
  vehicle_type: string | null;
  license_class: string | null;
  service_area: string | null;
  province: string | null;
  city: string | null;
  rating: number | null;
  acceptance_rate: number;
  completion_rate: number;
  orders_today: number;
  weekly_earnings_cents: number;
  outstanding_payout_cents: number;
  wallet_balance_cents: number;
  health_score: number;
  license_verified: boolean;
  insurance_verified: boolean;
  vehicle_verified: boolean;
  background_check_status: string;
  last_active_at: string | null;
  created_at: string;
  tags: string[];
};

export type DriverAi = {
  fraud_risk: string;
  burnout_risk: string;
  late_delivery_risk: string;
  maintenance_risk: string;
  payout_anomaly: string;
  recommended_training: string[];
  suggested_actions: string[];
};

export type DriverDetail = DriverRow & {
  health: number;
  ai: DriverAi;
  documents: Record<string, unknown>;
  performance: Record<string, unknown>;
  fleetbase_driver_id: string | null;
  metrics: {
    orders_today: number;
    in_progress: number;
    completed_today: number;
    revenue_today_cents: number;
    revenue_week_cents: number;
    revenue_month_cents: number;
    lifetime_orders: number;
    lifetime_completed: number;
    acceptance_rate: number;
    completion_rate: number;
    cancellation_rate: number;
    on_time_percent: number;
    weekly_earnings_cents: number;
    wallet_balance_cents: number;
    pending_payout_cents: number;
    incidents: number;
    last_active_at: string | null;
  };
  counts: Record<string, number>;
};

export type DriverStats = {
  total: number;
  approved: number;
  pending: number;
  suspended: number;
  online: number;
  pending_payout_cents: number;
};

export type DriverFacets = {
  statuses: Array<{ value: string; count: number }>;
  availability: Array<{ value: string; count: number }>;
  background_check: Array<{ value: string; count: number }>;
  vehicle_types: Array<{ value: string; count: number }>;
};

export type DriverOrder = {
  id: string;
  order_number: string;
  tracking_number: string;
  state: string;
  amount_cents: number;
  scheduled_at: string | null;
  created_at: string | null;
  dropoff: Record<string, unknown>;
};

export type DriverVehicle = {
  id: string;
  vehicle_class: string;
  plate_number: string;
  make_model: string | null;
  capacity_kg: number | null;
  compliance_expires_at: string | null;
  is_active: boolean;
};

export type DriverPayouts = {
  wallet_balance_cents: number;
  pending_cents: number;
  paid_cents: number;
  payouts: Array<{
    id: string;
    amount_cents: number;
    currency: string;
    status: string;
    reference: string | null;
    created_at: string;
  }>;
};

export type DriverDocuments = {
  verification: {
    license_verified: boolean;
    insurance_verified: boolean;
    vehicle_verified: boolean;
    background_check_status: string;
  };
  files: Array<Record<string, unknown>>;
  expiries: Array<{ label: string; expires_at: string }>;
  raw: Record<string, unknown>;
};

export type DriverIncidents = {
  incidents: Array<{
    id: string;
    type: string;
    status: string;
    order_id: string;
    created_at: string | null;
  }>;
  claims: Array<{
    id: string;
    claim_type: string;
    status: string;
    order_id: string;
    created_at: string | null;
  }>;
};

export type DriverAnalytics = {
  by_month: Array<{ month: string; orders: number; completed: number; revenue_cents: number }>;
  lifetime_orders: number;
};

export type TimelineEvent = { kind: string; type: string; title: string; at: string | null };

const qs = (params: Record<string, string | undefined>) => {
  const s = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) if (v) s.set(k, v);
  const out = s.toString();
  return out ? `?${out}` : "";
};

const B = "/v1/admin/drivers";

export const drivers = {
  list: (t: string, params: Record<string, string | undefined> = {}) =>
    adminFetch<DriverRow[]>(`${B}${qs(params)}`, t),
  facets: (t: string) => adminFetch<DriverFacets>(`${B}/facets`, t),
  stats: (t: string) => adminFetch<DriverStats>(`${B}/stats`, t),
  detail: (t: string, id: string) => adminFetch<DriverDetail>(`${B}/${id}`, t),
  approve: (t: string, id: string) =>
    adminFetch<DriverDetail>(`${B}/${id}/approve`, t, { method: "POST" }),
  suspend: (t: string, id: string) =>
    adminFetch<DriverDetail>(`${B}/${id}/suspend`, t, { method: "POST" }),
  verify: (
    t: string,
    id: string,
    body: {
      license_verified?: boolean;
      insurance_verified?: boolean;
      vehicle_verified?: boolean;
      background_check_status?: string;
    }
  ) =>
    adminFetch<DriverDetail>(`${B}/${id}/verification`, t, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  action: (t: string, id: string, body: { type: string; message?: string }) =>
    adminFetch<{ ok: boolean; action: string }>(`${B}/${id}/action`, t, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  orders: (t: string, id: string, params: Record<string, string | undefined> = {}) =>
    adminFetch<DriverOrder[]>(`${B}/${id}/orders${qs(params)}`, t),
  vehicles: (t: string, id: string) => adminFetch<DriverVehicle[]>(`${B}/${id}/vehicles`, t),
  payouts: (t: string, id: string) => adminFetch<DriverPayouts>(`${B}/${id}/payouts`, t),
  documents: (t: string, id: string) => adminFetch<DriverDocuments>(`${B}/${id}/documents`, t),
  incidents: (t: string, id: string) => adminFetch<DriverIncidents>(`${B}/${id}/incidents`, t),
  analytics: (t: string, id: string) => adminFetch<DriverAnalytics>(`${B}/${id}/analytics`, t),
  timeline: (t: string, id: string) => adminFetch<TimelineEvent[]>(`${B}/${id}/timeline`, t),
  activities: (t: string, id: string) => adminFetch<Activity[]>(`${B}/${id}/activities`, t),
  tasks: (t: string, id: string) => adminFetch<Task[]>(`${B}/${id}/tasks`, t),
};

export function healthTone(score: number): string {
  if (score >= 70) return "green";
  if (score >= 40) return "amber";
  return "red";
}
