import { adminFetch } from "@/lib/api";

export type OpsStats = {
  orders_today: number;
  revenue_today_cents: number;
  active_deliveries: number;
  waiting_dispatch: number;
  pending_pickups: number;
  pending_deliveries: number;
  delayed_orders: number;
  high_priority_orders: number;
  failed_deliveries: number;
  completed_today: number;
  drivers_online: number;
  drivers_offline: number;
  vehicles_active: number;
  open_claims: number;
  support_tickets: number;
  open_exceptions: number;
};

export type OpsOrder = {
  id: string;
  order_number: string;
  tracking_number: string;
  state: string;
  amount_cents: number;
  merchant: string | null;
  driver: string | null;
  driver_id: string | null;
  pickup: string | null;
  dropoff: string | null;
  eta: string | null;
  sla: string;
  high_priority: boolean;
  created_at: string | null;
  risk_score?: number;
  reasons?: string[];
};

export type QueueOrder = OpsOrder & {
  has_pickup_coords?: boolean;
  has_dropoff_coords?: boolean;
  stop_phase?: "full" | "delivery_only";
};

export type OptimizedStop = {
  sequence: number;
  order_id: string;
  tracking_number: string;
  type: "pickup" | "delivery";
  address: string | null;
  leg_duration_seconds?: number;
  cumulative_duration_seconds?: number;
};

export type OptimizeQueueResponse = {
  plan_id: string;
  optimized_stops: OptimizedStop[];
  metrics: {
    stop_count: number;
    order_count: number;
    distance_meters: number;
    duration_seconds: number;
    duration_minutes: number;
    distance_km: number;
    strategy: string;
    engine: string;
  };
  warnings: string[];
  order_ids: string[];
};

export type AssignBatchResponse = {
  plan_id: string;
  driver_id: string;
  assigned_count: number;
  results: Array<{ order_id: string; status: string; tracking_number?: string }>;
  errors: Array<{ order_id: string; error: string }>;
};

export type BoardColumn = {
  key: string;
  count: number;
  hidden: number;
  value_cents: number;
  orders: OpsOrder[];
};
export type SlaResponse = {
  breached: OpsOrder[];
  at_risk: OpsOrder[];
  breached_count: number;
  at_risk_count: number;
};
export type OpsException = {
  id: string;
  type: string;
  status: string;
  order_id: string;
  tracking_number: string;
  merchant: string | null;
  reported_by: string;
  created_at: string | null;
};
export type ActivityEvent = {
  id: string;
  event_type: string;
  aggregate_type: string;
  aggregate_id: string;
  actor_type: string;
  occurred_at: string | null;
};
export type AssignableDriver = {
  id: string;
  name: string;
  online: boolean;
  availability: string;
  rating: number | null;
};
export type AiOps = {
  risk_orders: OpsOrder[];
  suggested_drivers: AssignableDriver[];
  recommendation: string;
};
export type MapSnapshot = {
  drivers: Array<{ id: string; name: string; status: string; online: boolean }>;
  orders: Array<{
    order_id: string;
    tracking: string;
    state: string;
    pickup: Record<string, unknown>;
    dropoff: Record<string, unknown>;
  }>;
  fleetbase_note: string;
};

const B = "/v1/admin/operations";

export const ops = {
  stats: (t: string) => adminFetch<OpsStats>(`${B}/stats`, t),
  board: (t: string) => adminFetch<BoardColumn[]>(`${B}/board`, t),
  moveBoardOrder: (t: string, orderId: string, toColumn: string) =>
    adminFetch<OpsOrder>(`${B}/board/move`, t, {
      method: "POST",
      body: JSON.stringify({ order_id: orderId, to_column: toColumn }),
    }),
  orders: (t: string, search?: string) =>
    adminFetch<OpsOrder[]>(
      `${B}/orders${search ? `?search=${encodeURIComponent(search)}` : ""}`,
      t
    ),
  queue: (t: string) => adminFetch<QueueOrder[]>(`${B}/queue`, t),
  optimizeQueue: (t: string, orderIds: string[], opts?: { strategy?: string; engine?: string }) =>
    adminFetch<OptimizeQueueResponse>(`${B}/queue/optimize`, t, {
      method: "POST",
      timeoutMs: 60_000,
      body: JSON.stringify({
        order_ids: orderIds,
        strategy: opts?.strategy ?? "balanced",
        engine: opts?.engine ?? "valhalla",
      }),
    }),
  assignBatch: (t: string, body: { plan_id: string; driver_id: string; order_ids?: string[] }) =>
    adminFetch<AssignBatchResponse>(`${B}/queue/assign-batch`, t, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  assignableDrivers: (t: string) => adminFetch<AssignableDriver[]>(`${B}/assignable-drivers`, t),
  exceptions: (t: string) => adminFetch<OpsException[]>(`${B}/exceptions`, t),
  sla: (t: string) => adminFetch<SlaResponse>(`${B}/sla`, t),
  activity: (t: string) => adminFetch<ActivityEvent[]>(`${B}/activity`, t),
  ai: (t: string) => adminFetch<AiOps>(`${B}/ai`, t),
  map: (t: string) => adminFetch<MapSnapshot>(`${B}/map`, t),
};

export const BOARD_LABELS: Record<string, string> = {
  waiting_dispatch: "Waiting Dispatch",
  assigned: "Assigned",
  accepted: "Accepted",
  heading_to_pickup: "Heading to Pickup",
  at_pickup: "At Pickup",
  picked_up: "Picked Up",
  in_transit: "In Transit",
  near_delivery: "Near Delivery",
  delivered: "Delivered",
  failed: "Failed",
  returned: "Returned",
  lost: "Lost",
  damaged: "Damaged",
};

export const BOARD_ACCENT: Record<string, string> = {
  waiting_dispatch: "#64748b",
  assigned: "#0ea5e9",
  accepted: "#6366f1",
  heading_to_pickup: "#8b5cf6",
  at_pickup: "#a855f7",
  picked_up: "#f59e0b",
  in_transit: "#2563eb",
  near_delivery: "#0d9488",
  delivered: "#16a34a",
  failed: "#dc2626",
  returned: "#ea580c",
  lost: "#b91c1c",
  damaged: "#9f1239",
};

export const SLA_TONE: Record<string, string> = {
  ok: "green",
  met: "green",
  at_risk: "amber",
  breached: "red",
};
