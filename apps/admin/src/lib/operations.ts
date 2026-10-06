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
  vehicles_active: number;
  open_claims: number;
  support_tickets: number;
  open_exceptions: number;
  shopify_ingress_dlq_open?: number;
  sla_at_risk?: number;
  sla_breached?: number;
  deltas?: {
    orders_today?: number;
    revenue_today_cents?: number;
    completed_today?: number;
  };
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
  sla_deadline?: string | null;
  sla_minutes_remaining?: number | null;
  stop_count?: number;
  stops_done?: number;
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
  order_state?: string;
  tracking_number: string;
  merchant: string | null;
  merchant_id?: string | null;
  customer_email?: string | null;
  reported_by: string;
  created_at: string | null;
  acknowledged_at?: string | null;
  acknowledged_by?: string | null;
  resolution_note?: string | null;
  resolved_at?: string | null;
  source?: string;
  dlq_id?: string;
  shop_domain?: string | null;
  reason_code?: string;
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
  rating: number | null;
  is_online?: boolean;
  active_orders?: number;
  medical_transport_certified?: boolean;
};

export type SuggestedDriver = {
  id: string;
  name: string;
  rating: number | null;
  online: boolean;
  active_orders: number;
  eta_minutes: number | null;
  deadhead_km: number | null;
  eta_source: string;
  capability_match: boolean | null;
  score: number;
  reasons: string[];
};

export type DriverSuggestions = {
  order_id: string;
  pickup_coords: boolean;
  vehicle_class: string | null;
  medical_required?: boolean;
  filtered_out_count?: number;
  source?: "cache" | "stale" | "pending" | string;
  drivers: SuggestedDriver[];
};

export type LiveMapStop = { lat: number; lng: number; kind: string; label: string };
export type LiveMapOrder = {
  id: string;
  tracking_number: string;
  state: string;
  driver: string | null;
  stops: LiveMapStop[];
};
export type LiveMapDriver = {
  id: string;
  fleetbase_driver_id: string;
  name: string;
  lat: number;
  lng: number;
  online: boolean;
  gps_source?: string;
  recorded_at?: string | null;
};
export type LiveMapDensityCell = { lat: number; lng: number; weight: number };
export type LiveMapZone = {
  id: string | null;
  name: string;
  kind: string;
  color: string;
  stroke_color: string;
  path: [number, number][];
};
export type LiveMapSnapshot = {
  drivers: LiveMapDriver[];
  orders: LiveMapOrder[];
  drivers_source: string;
  density?: LiveMapDensityCell[];
  density_source?: string;
  zones?: LiveMapZone[];
  zones_source?: string;
};
export type RouteGeometry = {
  order_id: string;
  stops: LiveMapStop[];
  path: [number, number][];
  source: string;
  distance_meters: number | null;
  duration_seconds: number | null;
};
export type PlaybackPoint = {
  lat: number;
  lng: number;
  heading?: number | null;
  speed?: number | null;
  recorded_at?: string | null;
  id?: string | null;
};
export type OrderPlayback = {
  order_id: string;
  fleetbase_order_id?: string | null;
  points: PlaybackPoint[];
  source: string;
  message?: string;
};
export type UtilizationDriver = {
  id: string;
  name: string;
  fleetbase_driver_id: string | null;
  online: boolean;
  on_shift: boolean;
  on_break: boolean;
  active_orders: number;
  shift_minutes: number;
  break_minutes: number;
  status: string;
  utilization_percent: number;
  utilization_note?: string;
  rating: number | null;
};
export type UtilizationSnapshot = {
  as_of: string;
  online_source: string;
  summary: {
    drivers_total: number;
    online: number;
    on_shift: number;
    idle: number;
    busy: number;
    on_break: number;
    waiting_unassigned: number;
    active_orders: number;
    avg_load_per_online: number;
    staffing_gap: number;
  };
  drivers: UtilizationDriver[];
};
export type AiOps = {
  risk_orders: OpsOrder[];
  suggested_drivers: AssignableDriver[];
  recommendation: string;
  /** NVIDIA NIM health (ops LLM — not on pay path). */
  llm?: {
    configured: boolean;
    provider: string;
    model: string;
    api_base: string;
    circuit_open: boolean;
    fail_streak: number;
  };
  phase2?: {
    intelligence: boolean;
    ai_dispatch: boolean;
  };
};

export type ScheduledBatchOrder = {
  id: string;
  order_number: string;
  tracking_number: string;
  state: string;
  scheduled_at: string | null;
  pickup: string | null;
  stop_count: number;
  order_kind?: string | null;
  amount_cents: number;
  fleetbase_order_id: string | null;
  pickup_window_start?: string | null;
  pickup_window_end?: string | null;
};

export type ScheduledBatch = {
  merchant_id: string | null;
  merchant_name: string | null;
  pickup_address: string | null;
  pickup_window_start: string | null;
  pickup_window_end: string | null;
  order_count: number;
  amount_cents: number;
  orders: ScheduledBatchOrder[];
};

export type ScheduledBatchesResponse = {
  date: string;
  batch_count: number;
  order_count: number;
  batches: ScheduledBatch[];
};

export type DayManifest = {
  id?: string | null;
  public_id?: string | null;
  status?: string | null;
  scheduled_date?: string | null;
  driver_id?: string | null;
  driver_name?: string | null;
  vehicle_id?: string | null;
  vehicle_name?: string | null;
  stop_count?: number | null;
  stops?: Array<{
    id?: string | null;
    sequence?: number;
    status?: string | null;
    order_id?: string | null;
  }>;
};

export type ManifestsResponse = {
  date: string;
  source: string;
  manifest_count: number;
  manifests: DayManifest[];
  note?: string;
};

export type OptimizeAssignment = {
  order_id?: string | null;
  porterchain_order_id?: string | null;
  vehicle_id?: string | null;
  driver_id?: string | null;
  distance_m?: number | null;
  duration_s?: number | null;
  sequence?: number | null;
};

export type OptimizeMetrics = {
  assigned_count?: number;
  unassigned_count?: number;
  capacity_reject_count?: number;
  vehicles_used?: number;
  after_distance_m?: number;
  after_duration_s?: number;
  after_distance_km?: number;
  after_duration_min?: number;
  utilization_orders_per_vehicle?: number;
  before_order_count?: number;
  estimated_fuel_liters?: number;
  estimated_fuel_cents?: number;
  liters_per_100km?: number;
  fuel_price_cents_per_liter?: number;
  cents_per_km?: number | null;
  fuel_delta_cents?: number;
  distance_delta_km?: number;
  valhalla_costing?: string;
  fuel_vehicle_class?: string;
  cuopt_shadow?: {
    status?: string;
    winner?: string;
    ortools_distance_km?: number | null;
    vroom_distance_km?: number | null;
    cuopt_distance_km?: number | null;
    delta_km_ortools_minus_cuopt?: number | null;
    reason?: string;
    note?: string;
    commit_sot?: string;
  };
};

export type OptimizeUnassignedDetail = {
  order_id: string;
  reason?: string;
  hint?: string;
  porterchain_order_id?: string;
};

export type OptimizeRunResult = {
  run_id?: string;
  status?: "pending" | "ready" | "error";
  ok?: boolean;
  error?: string | null;
  hint?: string | null;
  message?: string | null;
  assignments: OptimizeAssignment[];
  unassigned?: string[];
  unassigned_details?: OptimizeUnassignedDetail[];
  metrics?: OptimizeMetrics;
  missing_sync?: string[];
  queued_at?: string | null;
};

export type OptimizePool = {
  order_count: number;
  eligible_count?: number;
  preview_cap?: number;
  offset?: number;
  remaining_after_page?: number;
  excluded?: {
    missing_coords?: number;
    sandbox?: number;
    shopify_ingress_paused?: number;
  };
  orders: Array<{
    id: string;
    tracking_number: string;
    state: string;
    order_source?: string;
    fleetbase_order_id: string | null;
    merchant_id?: string | null;
    scheduled_at?: string | null;
    weight_kg?: number | null;
  }>;
  merchants?: Array<{ merchant_id: string | null; order_count: number }>;
  vehicle_ids?: string[];
  driver_ids?: string[];
  missing_sync?: string[];
  placeholder_skipped?: number;
};

export type OptimizeCommitResult = {
  ok?: boolean;
  error?: string | null;
  manifest_count?: number;
  committed?: unknown[];
  failed?: unknown[];
  run_id?: string | null;
  idempotent?: boolean;
  scheduled_date?: string;
  committed_at?: string;
};

export type CopilotAlternate = {
  driver_id: string;
  driver_name?: string | null;
  eta_minutes?: number | null;
  eta_source?: string | null;
  score?: number | null;
};

export type CopilotAction = {
  id: string;
  kind: string;
  title: string;
  summary: string;
  order_id: string;
  tracking_number: string;
  driver_id: string;
  driver_name?: string | null;
  eta_minutes?: number | null;
  eta_source?: string | null;
  savings_minutes?: number | null;
  score?: number | null;
  reasons?: string[];
  rationale_narrative?: string | null;
  alternates?: CopilotAlternate[];
};

export type CopilotResponse = {
  generated_at: string;
  action_count: number;
  actions: CopilotAction[];
  pending_ranking?: number;
  note?: string;
};

export type CopilotAuditEvent = {
  id: string;
  event_type: string;
  order_id: string;
  actor_id?: string | null;
  payload?: Record<string, unknown>;
  occurred_at: string | null;
};

export type OpsSearchResult = {
  q: string;
  orders: Array<{
    id: string;
    tracking_number: string;
    order_number: string;
    state: string;
    kind: "order";
  }>;
  drivers: Array<{
    id: string;
    name: string;
    online: boolean;
    kind: "driver";
  }>;
};

const B = "/v1/admin/operations";

export const ops = {
  stats: (t: string) => adminFetch<OpsStats>(`${B}/stats`, t),
  board: (t: string) => adminFetch<BoardColumn[]>(`${B}/board`, t),
  moveBoardOrder: (t: string, orderId: string, toColumn: string, reason?: string) =>
    adminFetch<OpsOrder>(`${B}/board/move`, t, {
      method: "POST",
      body: JSON.stringify({
        order_id: orderId,
        to_column: toColumn,
        reason: reason?.trim() || null,
      }),
    }),
  orders: (t: string, search?: string) =>
    adminFetch<OpsOrder[]>(
      `${B}/orders${search ? `?search=${encodeURIComponent(search)}` : ""}`,
      t
    ),
  queue: (t: string) => adminFetch<QueueOrder[]>(`${B}/queue`, t),
  assignableDrivers: (t: string) => adminFetch<AssignableDriver[]>(`${B}/assignable-drivers`, t),
  driverSuggestions: (t: string, orderId: string) =>
    adminFetch<DriverSuggestions>(`${B}/orders/${orderId}/driver-suggestions`, t),
  liveMap: (t: string) => adminFetch<LiveMapSnapshot>(`${B}/live-map`, t),
  routeGeometry: (t: string, orderId: string) =>
    adminFetch<RouteGeometry>(`${B}/orders/${orderId}/route-geometry`, t),
  playback: (t: string, orderId: string) =>
    adminFetch<OrderPlayback>(`${B}/orders/${orderId}/playback`, t),
  utilization: (t: string) => adminFetch<UtilizationSnapshot>(`${B}/utilization`, t),
  exceptions: (t: string) => adminFetch<OpsException[]>(`${B}/exceptions`, t),
  acknowledgeException: (t: string, id: string) =>
    adminFetch<OpsException>(`${B}/exceptions/${id}/acknowledge`, t, { method: "POST" }),
  resolveException: (t: string, id: string, note?: string) =>
    adminFetch<OpsException>(`${B}/exceptions/${id}/resolve`, t, {
      method: "POST",
      body: JSON.stringify({ note: note ?? null }),
    }),
  retryException: (t: string, id: string) =>
    adminFetch<{ exception: OpsException; order_state: string }>(`${B}/exceptions/${id}/retry`, t, {
      method: "POST",
    }),
  sla: (t: string) => adminFetch<SlaResponse>(`${B}/sla`, t),
  activity: (t: string) => adminFetch<ActivityEvent[]>(`${B}/activity`, t),
  ai: (t: string) => adminFetch<AiOps>(`${B}/ai`, t),
  scheduledBatches: (t: string, day?: string, merchantId?: string) => {
    const q = new URLSearchParams();
    if (day) q.set("day", day);
    if (merchantId) q.set("merchant_id", merchantId);
    const qs = q.toString();
    return adminFetch<ScheduledBatchesResponse>(`${B}/scheduled-batches${qs ? `?${qs}` : ""}`, t);
  },
  manifests: (t: string, scheduledDate?: string, status?: string) => {
    const q = new URLSearchParams();
    if (scheduledDate) q.set("scheduled_date", scheduledDate);
    if (status) q.set("status", status);
    const qs = q.toString();
    return adminFetch<ManifestsResponse>(`${B}/manifests${qs ? `?${qs}` : ""}`, t);
  },
  optimizePool: (t: string) => adminFetch<OptimizePool>(`${B}/optimize/pool`, t),
  optimizeEngines: (t: string) =>
    adminFetch<{ engines: Array<{ id?: string; name?: string }> }>(`${B}/optimize/engines`, t),
  syncHealth: (t: string) =>
    adminFetch<{
      queue: Record<string, number | string | null>;
      dead_letters: Array<{
        id: string;
        kind: string;
        direction: string;
        order_id: string | null;
        attempts: number;
        last_error: string | null;
      }>;
      recent_audit: Array<{
        direction: string;
        kind: string;
        status: string;
        order_id: string | null;
        message: string | null;
        at: string | null;
      }>;
    }>(`${B}/sync/health`, t),
  optimizeRun: (
    t: string,
    body: {
      order_ids?: string[];
      mode?: string;
      engine?: string | null;
      shape?: "fleet" | "merchant" | "vehicle";
      merchant_id?: string | null;
      vehicle_ids?: string[];
      driver_ids?: string[];
      offset?: number;
    }
  ) =>
    adminFetch<OptimizeRunResult>(`${B}/optimize/run`, t, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  optimizeRunStatus: (t: string, runId: string) =>
    adminFetch<OptimizeRunResult>(`${B}/optimize/runs/${encodeURIComponent(runId)}`, t),
  optimizeCommit: (
    t: string,
    assignments: OptimizeAssignment[],
    opts?: {
      scheduledDate?: string;
      runId?: string | null;
      expectedSequenceVersion?: number | null;
      pcDriverId?: string | null;
    }
  ) =>
    adminFetch<OptimizeCommitResult>(`${B}/optimize/commit`, t, {
      method: "POST",
      body: JSON.stringify({
        assignments,
        scheduled_date: opts?.scheduledDate ?? null,
        run_id: opts?.runId ?? null,
        expected_sequence_version: opts?.expectedSequenceVersion ?? null,
        pc_driver_id: opts?.pcDriverId ?? null,
      }),
    }),
  copilot: (t: string) => adminFetch<CopilotResponse>(`${B}/copilot`, t),
  copilotAudit: (t: string) => adminFetch<CopilotAuditEvent[]>(`${B}/copilot/audit`, t),
  copilotAccept: (t: string, body: { action_id: string; order_id: string; driver_id: string }) =>
    adminFetch<{ ok: boolean }>(`${B}/copilot/accept`, t, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  copilotModify: (t: string, body: { action_id: string; order_id: string; driver_id: string }) =>
    adminFetch<{ ok: boolean }>(`${B}/copilot/modify`, t, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  copilotDismiss: (t: string, body: { action_id: string; order_id: string; reason?: string }) =>
    adminFetch<{ ok: boolean }>(`${B}/copilot/dismiss`, t, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  /** Read-only NVIDIA NIM ops assist (phase2). Never auto-assigns. */
  copilotLlmSuggest: (
    t: string,
    body: {
      context: string;
      enable_intelligence?: boolean;
      merchant_id?: string;
      include_sla_queue?: boolean;
    }
  ) =>
    adminFetch<{
      suggestions: Array<{
        action: string;
        rationale: string;
        priority?: string;
        confidence?: number;
        auto_apply: boolean;
      }>;
      status: string;
      provider?: string;
      model?: string;
      latency_ms?: number;
      nim?: AiOps["llm"];
      context_preview?: string;
      tools?: { tools: string[]; results: unknown[] };
    }>(`${B}/copilot/llm`, t, {
      method: "POST",
      body: JSON.stringify({
        context: body.context,
        enable_intelligence: body.enable_intelligence ?? true,
        merchant_id: body.merchant_id,
        include_sla_queue: body.include_sla_queue ?? true,
      }),
    }),
  search: (t: string, q: string) =>
    adminFetch<OpsSearchResult>(`${B}/search?q=${encodeURIComponent(q)}`, t),
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
