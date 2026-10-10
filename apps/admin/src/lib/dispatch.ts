import { adminFetch } from "@/lib/api";

const B = "/v1/admin/operations/dispatch";

export const DISPATCH_VIEWS = ["today", "plan", "live", "exceptions", "fleet", "metrics"] as const;
export type DispatchView = (typeof DISPATCH_VIEWS)[number];

export function isDispatchView(v: string | undefined | null): v is DispatchView {
  return !!v && (DISPATCH_VIEWS as readonly string[]).includes(v);
}

/** Legacy /operations?view=…&tool=… → new Dispatch route (single hop). */
export function legacyOperationsTarget(view?: string | null, tool?: string | null): string {
  const v = (view ?? "").toLowerCase();
  const t = (tool ?? "").toLowerCase();
  if (v === "orders") return "/orders";
  if (["attention", "exceptions", "sla"].includes(v)) return "/dispatch/exceptions";
  if (v === "map") return "/dispatch/live";
  if (["optimize", "scheduled"].includes(v) || ["optimize", "scheduled", "ai", "copilot"].includes(t))
    return "/dispatch/plan";
  if (v === "utilization" || t === "utilization") return "/dispatch/fleet";
  if (["ai", "copilot"].includes(v)) return "/dispatch/plan";
  return "/dispatch/today";
}

export type DispatchMetrics = {
  window_days: number;
  orders_created: number;
  delivered: number;
  order_to_dispatch_min: number | null;
  on_time_pct: number | null;
  first_attempt_pct: number | null;
  cost_per_stop_cents: number | null;
  fill_pct: number | null;
  stops_per_driver_hour: number | null;
  driver_hours: number;
  hourly_cost_cents: number;
};

export type DispatchExceptionItem = {
  id: string;
  kind: string;
  type: string;
  severity: "critical" | "high" | "medium" | "low";
  order_id: string;
  order_number: string;
  state: string;
  age_min: number | null;
  status: string;
  exception_id?: string;
  eta?: string | null;
  promise?: string | null;
};

export type DispatchExceptions = {
  items: DispatchExceptionItem[];
  counts: Record<string, number>;
  total: number;
  eta: "ok" | "unavailable";
};

export type RecommendDriver = {
  driver_id: string;
  name: string;
  vehicle_class: string | null;
  active_jobs: number;
  fill_after_pct: number | null;
  insertion_minutes: number | null;
  cost_cents: number | null;
  start_source: string;
  reasons: string[];
  blocked: string | null;
};

export type Recommendation = {
  order_id: string;
  order_number: string;
  load: { kg: number; m3: number; boxes: number };
  vehicle: { id: string; label: string; fill_pct: number } | null;
  vehicle_reason: string;
  matrix: "valhalla" | "unavailable";
  drivers: RecommendDriver[];
  best_driver_id: string | null;
  hourly_cost_cents: number;
};

export type JobOffer = {
  id: string;
  order_id: string;
  driver_id: string;
  status: "pending" | "accepted" | "declined" | "expired" | "cancelled";
  rank: number;
  expires_at: string;
  seconds_left: number;
};

export type LiveEta = {
  order_id: string;
  order_number: string;
  state: string;
  driver_id: string | null;
  eta: string | null;
  promise: string | null;
  status: "on_time" | "at_risk" | "late" | "unknown";
  has_gps: boolean;
};

export type FleetVehicle = {
  id: string;
  label: string;
  max_kg: number;
  max_m3: number;
  max_boxes: number;
  cost_per_km_cents: number;
  enabled: boolean;
};

export type FleetCapacity = {
  schema: number;
  hourly_cost_cents: number;
  max_fill: number;
  offer_ttl_seconds: number;
  service_minutes_per_stop: number;
  at_risk_minutes: number;
  vehicles: FleetVehicle[];
};


export type PlanStop = {
  key: string;
  order_id: string;
  order_number?: string | null;
  kind: "pickup" | "drop" | "return_pickup" | "return_drop" | "hub" | "handoff";
  fsa: string | null;
  eta_s: number;
};

export type PlanRoute = {
  id: string;
  vehicle_class: string;
  driver_id: string | null;
  driver_name: string | null;
  seconds: number;
  cost_cents: number;
  fill_pct: number;
  status: string;
  stops: PlanStop[];
};

export type SolverResult = { cost_cents?: number; feasible?: boolean; dropped?: number; status?: string };

export type FleetPlan = {
  id: string;
  status: "draft" | "committed" | "superseded" | "discarded";
  solver: "ortools" | "cuopt";
  version: number;
  parent_id: string | null;
  service_date: string;
  created_at: string | null;
  committed_at: string | null;
  summary: {
    orders?: number;
    pairs?: number;
    shapes?: Record<string, number>;
    skipped?: { order_id: string; order_number: string; reason: string }[];
    matrix?: "valhalla";
    cost_cents?: number;
    vehicles_used?: number;
    dropped?: string[];
    feasible?: boolean;
    compare?: Record<string, SolverResult>;
    kind?: "plan" | "replan";
    commit?: { assigned: number; skipped: { order_id: string; reason: string }[] };
  };
  routes: PlanRoute[];
};

export type PlanExplanation = {
  source: "rules" | "nvidia_nim";
  explanation: string[];
  suggestions: string[];
  suggest_only: true;
  llm_error?: string;
};

export type LogisticsPartner = {
  id?: string;
  name: string;
  kind: "warehouse" | "ftl" | "ltl" | "3pl";
  lat: number | null;
  lng: number | null;
  fsa_coverage: string[];
  rate_per_kg_cents: number;
  min_charge_cents: number;
  transit_days: number;
  cutoff_local: string | null;
  contact_email?: string | null;
  active: boolean;
};

export type Retention = { gps_days: number; pod_days: number; enabled: boolean };
export type RetentionRun = {
  dry_run: boolean;
  gps_pings: number;
  pod_refs: number;
  pod_files?: number;
  pod_file_bytes?: number;
  pod_files_deleted?: number;
  gps_before?: string;
  pod_before?: string;
};

export type LegStatus = "planned" | "requested" | "accepted" | "picked_up" | "delivered" | "cancelled";

export type PartnerLeg = {
  id: string;
  order_id: string;
  order_number: string | null;
  seq: number;
  mode: "warehouse" | "ftl" | "ltl" | "3pl" | "local";
  status: LegStatus;
  partner_id: string | null;
  partner_name: string | null;
  from_label: string | null;
  to_label: string | null;
  est_cost_cents: number | null;
  next: LegStatus[];
  history: { from: LegStatus; to: LegStatus; at: string; note: string | null }[];
  has_draft: boolean;
};

export type PartnerEmailDraft = { to: string | null; subject: string; body: string; attachment: string; status: string };

export const LEG_STATUS_LABEL: Record<LegStatus, string> = {
  planned: "Planned",
  requested: "Requested",
  accepted: "Accepted",
  picked_up: "Picked up",
  delivered: "Delivered",
  cancelled: "Cancelled",
};

export const STOP_KIND_LABEL: Record<PlanStop["kind"], string> = {
  pickup: "Pickup",
  drop: "Drop",
  return_pickup: "Return pickup",
  return_drop: "Return drop",
  hub: "Hub",
  handoff: "Handoff",
};

/** Pickups/drops per route — a 1→N route reads "1 pickup · 3 drops". */
export function routeMix(stops: PlanStop[]): string {
  const p = stops.filter((s) => s.kind === "pickup" || s.kind === "return_pickup").length;
  const d = stops.length - p;
  return `${p} pickup${p === 1 ? "" : "s"} · ${d} drop${d === 1 ? "" : "s"}`;
}

/** One row per physical stop: consecutive split pickups/drops of the same order at one place merge. */
export function groupStops(stops: PlanStop[]): (PlanStop & { count: number })[] {
  const out: (PlanStop & { count: number })[] = [];
  for (const s of stops) {
    const last = out[out.length - 1];
    const place = (k: string) => k.split(":")[1];
    if (last && last.order_id === s.order_id && last.kind === s.kind && place(last.key) === place(s.key)) {
      last.count += 1;
      last.eta_s = s.eta_s;
    } else {
      out.push({ ...s, count: 1 });
    }
  }
  return out;
}

export function minutes(seconds: number): string {
  const m = Math.round(seconds / 60);
  return m >= 60 ? `${Math.floor(m / 60)}h ${m % 60}m` : `${m}m`;
}

const J = { "Content-Type": "application/json" };

export const dispatch = {
  metrics: (t: string, days = 7) => adminFetch<DispatchMetrics>(`${B}/metrics?days=${days}`, t),
  exceptions: (t: string) => adminFetch<DispatchExceptions>(`${B}/exceptions`, t),
  liveEta: (t: string) => adminFetch<{ items: LiveEta[] }>(`${B}/live-eta`, t),
  recommend: (t: string, orderId: string) =>
    adminFetch<Recommendation>(`${B}/orders/${encodeURIComponent(orderId)}/recommend`, t),
  offers: (t: string, orderId: string) =>
    adminFetch<{ items: JobOffer[] }>(`${B}/orders/${encodeURIComponent(orderId)}/offers`, t),
  offer: (t: string, orderId: string) =>
    adminFetch<{ offer: JobOffer | null; created: boolean }>(
      `${B}/orders/${encodeURIComponent(orderId)}/offer`,
      t,
      { method: "POST" }
    ),
  fleet: (t: string) => adminFetch<FleetCapacity>(`${B}/fleet-capacity`, t),
  saveFleet: (t: string, body: FleetCapacity) =>
    adminFetch<FleetCapacity>(`${B}/fleet-capacity`, t, {
      method: "PUT",
      body: JSON.stringify(body),
      headers: { "Content-Type": "application/json" },
    }),
  latestPlan: (t: string) => adminFetch<{ plan: FleetPlan | null }>(`${B}/plans/latest`, t),
  planDay: (t: string, body: { order_ids?: string[]; time_limit_s?: number } = {}) =>
    adminFetch<FleetPlan>(`${B}/plans`, t, { method: "POST", body: JSON.stringify(body), headers: J }),
  replan: (t: string, id: string) =>
    adminFetch<FleetPlan>(`${B}/plans/${encodeURIComponent(id)}/replan`, t, { method: "POST" }),
  commitPlan: (t: string, id: string) =>
    adminFetch<FleetPlan>(`${B}/plans/${encodeURIComponent(id)}/commit`, t, { method: "POST" }),
  explainPlan: (t: string, id: string) =>
    adminFetch<PlanExplanation>(`${B}/plans/${encodeURIComponent(id)}/explain`, t, { method: "POST" }),
  partners: (t: string) => adminFetch<{ items: LogisticsPartner[] }>(`${B}/partners`, t),
  savePartner: (t: string, body: LogisticsPartner) =>
    adminFetch<LogisticsPartner>(body.id ? `${B}/partners/${encodeURIComponent(body.id)}` : `${B}/partners`, t, {
      method: body.id ? "PUT" : "POST",
      body: JSON.stringify(body),
      headers: J,
    }),
  partnerLegs: (t: string, status?: LegStatus) =>
    adminFetch<{ items: PartnerLeg[] }>(`${B}/partner-legs${status ? `?status=${status}` : ""}`, t),
  draftPartnerLeg: (t: string, id: string) =>
    adminFetch<PartnerEmailDraft>(`${B}/partner-legs/${encodeURIComponent(id)}/draft`, t, { method: "POST" }),
  setPartnerLegStatus: (t: string, id: string, status: LegStatus, note?: string) =>
    adminFetch<PartnerLeg>(`${B}/partner-legs/${encodeURIComponent(id)}/status`, t, {
      method: "POST",
      body: JSON.stringify({ status, note }),
      headers: J,
    }),
  /** BFF path for the PDF (opened in a new tab). */
  partnerLegPdfPath: (id: string) => `${B}/partner-legs/${encodeURIComponent(id)}/job-sheet.pdf`,
  retention: (t: string) => adminFetch<Retention>(`${B}/retention`, t),
  saveRetention: (t: string, body: Retention) =>
    adminFetch<Retention>(`${B}/retention`, t, { method: "PUT", body: JSON.stringify(body), headers: J }),
  runRetention: (t: string, dryRun: boolean) =>
    adminFetch<RetentionRun>(`${B}/retention/run?dry_run=${dryRun}`, t, { method: "POST" }),
};

export function money(cents: number | null | undefined): string {
  if (cents == null) return "—";
  return `$${(cents / 100).toFixed(2)}`;
}
