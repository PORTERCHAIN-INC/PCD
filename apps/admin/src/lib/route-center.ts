import { adminFetch } from "@/lib/api";

const PREFIX = "/v1/admin/route-center";

export type RouteCenterDashboard = {
  routes_waiting: number;
  routes_planned: number;
  routes_optimized: number;
  routes_dispatched: number;
  routes_active: number;
  routes_completed: number;
  drivers_available: number;
  drivers_busy: number;
  vehicles_available: number;
  vehicles_busy: number;
  orders_waiting: number;
  capacity_utilization_pct: number;
  todays_distance_km: number;
  fuel_estimate_liters: number;
  average_eta_minutes: number;
  late_routes: number;
  on_time_pct: number;
  orders_in_flight: number;
};

export type RouteStop = {
  order_id: string;
  tracking_number?: string;
  type: "pickup" | "delivery";
  location?: Record<string, unknown>;
  address?: string;
  priority?: string;
  status?: string;
};

export type RoutePlan = {
  id: string;
  name: string;
  status: string;
  strategy: string;
  zone: string | null;
  order_ids: string[];
  stops: RouteStop[];
  driver_id: string | null;
  vehicle_id: string | null;
  simulation: Record<string, number | string | boolean>;
  recommendations: Record<string, unknown>;
  fleetbase_run_id: string | null;
  template_id: string | null;
  requires_approval: boolean;
  approved_by: string | null;
  created_at: string | null;
  updated_at: string | null;
  dispatched_at: string | null;
  completed_at: string | null;
  audit_log?: Array<{
    id: string;
    action: string;
    actor_user_id: string | null;
    payload: Record<string, unknown>;
    created_at: string | null;
  }>;
  live_map?: Record<string, unknown>;
};

export type RouteTemplate = {
  id: string;
  name: string;
  template_type: string;
  merchant_id: string | null;
  zone: string | null;
  schedule: Record<string, unknown>;
  stops: RouteStop[];
  config: Record<string, unknown>;
  created_at: string | null;
};

export type PlanningQueue = {
  website_orders: Array<Record<string, unknown>>;
  merchant_orders: Array<Record<string, unknown>>;
  scheduled_orders: Array<Record<string, unknown>>;
  returns: Array<Record<string, unknown>>;
  express_orders: Array<Record<string, unknown>>;
  grouped_orders: Array<Record<string, unknown>>;
  ready_for_planning: Array<Record<string, unknown>>;
};

export const routeCenter = {
  meta: (token: string) =>
    adminFetch<{ statuses: string[]; strategies: string[] }>(`${PREFIX}/meta`, token),
  dashboard: (token: string) => adminFetch<RouteCenterDashboard>(`${PREFIX}/dashboard`, token),
  planningQueue: (token: string) => adminFetch<PlanningQueue>(`${PREFIX}/planning-queue`, token),
  listPlans: (token: string, params?: { status?: string; search?: string }) => {
    const q = new URLSearchParams();
    if (params?.status) q.set("status", params.status);
    if (params?.search) q.set("search", params.search);
    const suffix = q.toString() ? `?${q}` : "";
    return adminFetch<RoutePlan[]>(`${PREFIX}/plans${suffix}`, token);
  },
  getPlan: (token: string, id: string) => adminFetch<RoutePlan>(`${PREFIX}/plans/${id}`, token),
  createPlan: (token: string, body: { name: string; order_ids: string[]; strategy?: string }) =>
    adminFetch<RoutePlan>(`${PREFIX}/plans`, token, { method: "POST", body: JSON.stringify(body) }),
  updatePlan: (token: string, id: string, body: Record<string, unknown>) =>
    adminFetch<RoutePlan>(`${PREFIX}/plans/${id}`, token, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  clonePlan: (token: string, id: string) =>
    adminFetch<RoutePlan>(`${PREFIX}/plans/${id}/clone`, token, { method: "POST" }),
  optimizePlan: (token: string, id: string, body?: { strategy?: string; engine?: string }) =>
    adminFetch<RoutePlan>(`${PREFIX}/plans/${id}/optimize`, token, {
      method: "POST",
      body: JSON.stringify(body ?? {}),
    }),
  simulatePlan: (token: string, id: string) =>
    adminFetch<Record<string, unknown>>(`${PREFIX}/plans/${id}/simulate`, token, {
      method: "POST",
    }),
  dispatchPlan: (
    token: string,
    id: string,
    body: { driver_id: string; vehicle_id?: string; approve?: boolean }
  ) =>
    adminFetch<RoutePlan>(`${PREFIX}/plans/${id}/dispatch`, token, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  recommendations: (token: string, id: string) =>
    adminFetch<Record<string, unknown>>(`${PREFIX}/plans/${id}/recommendations`, token),
  templates: (token: string) => adminFetch<RouteTemplate[]>(`${PREFIX}/templates`, token),
  saveTemplate: (token: string, planId: string, body: { name: string; template_type?: string }) =>
    adminFetch<RouteTemplate>(`${PREFIX}/plans/${planId}/save-template`, token, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  createFromTemplate: (token: string, templateId: string, name?: string) =>
    adminFetch<RoutePlan>(`${PREFIX}/templates/${templateId}/create-plan`, token, {
      method: "POST",
      body: JSON.stringify({ name }),
    }),
  analytics: (token: string) => adminFetch<Record<string, number>>(`${PREFIX}/analytics`, token),
  history: (token: string) => adminFetch<RoutePlan[]>(`${PREFIX}/history`, token),
  liveExecution: (token: string) =>
    adminFetch<Record<string, unknown>>(`${PREFIX}/live-execution`, token),
};
