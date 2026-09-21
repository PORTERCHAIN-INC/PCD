export type JobBucket = "current" | "upcoming" | "completed";

export type JobUrgency = "critical" | "high" | "medium" | "normal";

export type JobLeg = "pickup" | "delivery" | "completed";

export type JobActionKey =
  "arrive_pickup" | "confirm_pickup" | "arrive_delivery" | "confirm_delivery";

export interface DriverNextStop {
  stop_id: string;
  stop_type: string;
  order_id: string;
  order_number?: string | null;
  tracking_number?: string | null;
  sequence: number;
  address: Record<string, unknown>;
  formatted_address: string;
  distance_m?: number | null;
  eta_minutes?: number | null;
  source?: string | null;
  status?: string | null;
  special_instructions?: string | null;
  access_unit?: string | null;
  access_buzzer?: string | null;
  access_dock?: string | null;
  call_on_arrival?: boolean;
  contact_phone_masked?: string | null;
  delivery_attempts?: number;
  max_delivery_attempts?: number;
}

export interface DriverScanProgress {
  scanned: number;
  required: number;
  complete: boolean;
  missing_suffixes: string[];
}

export interface DriverJobSummary {
  order_id: string;
  order_number: string;
  tracking_number: string;
  state: string;
  status: string;
  bucket: JobBucket;
  pickup_address: string;
  delivery_address: string;
  pickup_stop_id: string;
  delivery_stop_id: string;
  scheduled_at: string | null;
  special_instructions?: string | null;
  urgency: JobUrgency;
  high_priority: boolean;
  priority_rank: number | null;
  current_leg?: JobLeg;
  pickup_completed?: boolean;
  delivery_completed?: boolean;
  is_current_job?: boolean;
  route_id?: string | null;
  scan_pickup?: DriverScanProgress;
  scan_delivery?: DriverScanProgress;
}

export interface DriverRouteMetrics {
  stop_count?: number;
  order_count?: number;
  distance_km?: number;
  duration_minutes?: number;
}

export interface DriverJobsList {
  route_id: string | null;
  route_status: string | null;
  plan_id: string | null;
  route_metrics: DriverRouteMetrics | null;
  optimize_available: boolean;
  next_stop: DriverNextStop | null;
  current: DriverJobSummary | null;
  upcoming: DriverJobSummary[];
  completed: DriverJobSummary[];
  jobs: DriverJobSummary[];
}

export interface DriverJobsOptimizeResult {
  plan_id: string;
  run_id?: string | null;
  status?: string;
  optimized_stops: Array<Record<string, unknown>>;
  metrics: DriverRouteMetrics & Record<string, unknown>;
  warnings: string[];
  order_ids: string[];
  message?: string | null;
  jobs: DriverJobsList;
  sequence_version?: number | null;
  preview?: boolean | null;
  applied?: boolean | null;
  apply_on_ready?: boolean | null;
  ok?: boolean | null;
  error?: string | null;
}

export interface DriverJobDetail extends DriverJobSummary {
  pickup_detail: Record<string, unknown>;
  delivery_detail: Record<string, unknown>;
  pickup_stop: Record<string, unknown>;
  delivery_stop: Record<string, unknown>;
  allowed_actions: JobActionKey[];
  next_stop: DriverNextStop | null;
  is_current_job: boolean;
  pickup_completed_at: string | null;
  delivery_completed_at: string | null;
  merchant: {
    id: string;
    company_name: string;
    email: string;
    phone: string | null;
  } | null;
  customer: {
    id: string | null;
    email: string | null;
    phone: string | null;
    name: string | null;
  };
  packages: Array<{
    id?: string;
    parcel_index?: number;
    total_parcels?: number;
    tracking_suffix?: string;
    status?: string;
    weight_kg?: number | null;
    dimensions?: unknown;
    scanned_pickup?: boolean;
    scanned_delivery?: boolean;
    package_type?: string;
    vehicle_class?: string;
  }>;
  packages_error?: string | null;
  scan_pickup?: DriverScanProgress;
  scan_delivery?: DriverScanProgress;
  timeline: Array<{
    event_type: string;
    label: string;
    from_state: string | null;
    to_state: string | null;
    occurred_at: string | null;
    actor_type: string | null;
  }>;
  photos: Array<Record<string, unknown>>;
  signatures: Array<Record<string, unknown>>;
  documents: Array<Record<string, unknown>>;
  proof_of_delivery: {
    completed: boolean;
    proofs: Array<Record<string, unknown>>;
    otp_verified: boolean;
  };
  otp_required?: boolean;
  incidents: Array<{
    id: string;
    incident_type: string;
    description: string;
    status: string;
    created_at: string;
  }>;
  amount_cents: number;
  cod_amount_cents?: number | null;
  cod_status?: string | null;
  currency: string;
  updated_at: string | null;
  route_id: string | null;
  delivery_attempts?: number;
  max_delivery_attempts?: number;
}

const PICKUP_LEG = new Set(["DRIVER_ASSIGNED", "DRIVER_ACCEPTED", "DRIVER_EN_ROUTE", "AT_PICKUP"]);
const DELIVERY_LEG = new Set(["PICKED_UP", "IN_TRANSIT", "AT_DESTINATION"]);
const DONE = new Set(["DELIVERED", "POD_COMPLETED", "INVOICED", "CLOSED"]);

export const JOB_STEPS = [
  { key: "assigned", label: "Assigned", states: ["DRIVER_ASSIGNED", "DRIVER_ACCEPTED"] },
  { key: "en_route", label: "En Route", states: ["DRIVER_EN_ROUTE", "IN_TRANSIT"] },
  { key: "at_stop", label: "At Stop", states: ["AT_PICKUP", "AT_DESTINATION"] },
  { key: "picked_up", label: "Picked Up", states: ["PICKED_UP"] },
  {
    key: "delivered",
    label: "Delivered",
    states: ["DELIVERED", "POD_COMPLETED", "INVOICED", "CLOSED"],
  },
] as const;

export function getJobLeg(state: string): JobLeg {
  const s = state.toUpperCase();
  if (DONE.has(s)) return "completed";
  if (DELIVERY_LEG.has(s)) return "delivery";
  return "pickup";
}

export function legLabel(leg: JobLeg): string {
  if (leg === "pickup") return "Pickup";
  if (leg === "delivery") return "Delivery";
  return "Completed";
}

export function resolveScanProgress(
  job: Pick<DriverJobDetail, "packages" | "scan_pickup" | "scan_delivery">,
  phase: "pickup" | "delivery"
): DriverScanProgress {
  const named = phase === "delivery" ? job.scan_delivery : job.scan_pickup;
  if (named && named.required > 0) return named;
  const pkgs = job.packages.filter((p) => Boolean(p.tracking_suffix || p.id));
  if (pkgs.length === 0) {
    return named ?? { scanned: 0, required: 0, complete: false, missing_suffixes: [] };
  }
  const scanned = pkgs.filter((p) =>
    phase === "delivery" ? Boolean(p.scanned_delivery) : Boolean(p.scanned_pickup)
  ).length;
  return {
    scanned,
    required: pkgs.length,
    complete: scanned === pkgs.length,
    missing_suffixes: pkgs
      .filter((p) => !(phase === "delivery" ? p.scanned_delivery : p.scanned_pickup))
      .map((p) => p.tracking_suffix ?? "")
      .filter(Boolean),
  };
}

export function getPrimaryAction(
  state: string,
  allowed: JobActionKey[] = []
): { key: JobActionKey; label: string } | null {
  const s = state.toUpperCase();
  const leg = getJobLeg(s);
  if (leg === "completed") return null;

  if (leg === "pickup") {
    if (s === "AT_PICKUP") {
      return { key: "confirm_pickup", label: "Confirm Pickup" };
    }
    return { key: "arrive_pickup", label: "Arrive at Pickup" };
  }

  if (s === "AT_DESTINATION") {
    return { key: "confirm_delivery", label: "Confirm Delivery" };
  }
  if (allowed.includes("confirm_delivery") && !allowed.includes("arrive_delivery")) {
    return { key: "confirm_delivery", label: "Confirm Delivery" };
  }
  return { key: "arrive_delivery", label: "Arrive at Delivery" };
}

export function actionErrorMessage(code: string): string {
  const map: Record<string, string> = {
    pickup_required: "Complete pickup before starting delivery.",
    pickup_already_completed: "Parcel already picked up.",
    not_current_stop: "This is not your next stop — finish the current job first.",
    not_at_stop:
      "GPS says you are not at this stop yet. Drive into the 150 m zone, then tap arrived.",
    pretrip_required: "Complete the 30-second vehicle check before starting shift.",
    shift_required: "Start shift (30-second vehicle check) before going online.",
    stop_not_found: "Stop not found or not assigned to you.",
    packages_incomplete: "Scan all package labels before confirming.",
    invalid_label_qr: "That is not a PorterChain package label.",
    qr_order_mismatch: "That label belongs to a different order.",
    scan_pickup_required_first: "Scan this box at pickup before delivery scan.",
    invalid_otp: "That OTP does not match. Ask the receiver for the current code.",
    otp_required: "This delivery requires the receiver OTP before you can complete proof.",
    package_not_found: "Package not found on this order.",
  };
  return map[code] ?? code.replace(/_/g, " ");
}

export function jobStatusLabel(state: string): string {
  return state
    .replace(/_/g, " ")
    .toLowerCase()
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

export function jobStatusColor(state: string): string {
  const s = state.toUpperCase();
  if (["POD_COMPLETED", "CLOSED", "INVOICED", "DELIVERED"].includes(s)) return "emerald";
  if (["CANCELLED", "FAILED", "DAMAGED", "LOST"].includes(s)) return "red";
  if (["DRIVER_EN_ROUTE", "IN_TRANSIT", "AT_PICKUP", "AT_DESTINATION", "PICKED_UP"].includes(s))
    return "amber";
  return "slate";
}

export function urgencyLabel(urgency: JobUrgency): string {
  const map: Record<JobUrgency, string> = {
    critical: "Critical",
    high: "High",
    medium: "Medium",
    normal: "Normal",
  };
  return map[urgency] ?? urgency;
}

export function urgencyColor(urgency: JobUrgency): string {
  if (urgency === "critical") return "bg-red-600 text-white";
  if (urgency === "high") return "bg-orange-100 text-orange-900";
  if (urgency === "medium") return "bg-amber-100 text-amber-900";
  return "bg-slate-100 text-slate-700";
}

export function stepIndexForState(state: string): number {
  const s = state.toUpperCase();
  if (DONE.has(s)) return 4;
  if (s === "PICKED_UP") return 3;
  if (s === "AT_DESTINATION") return 4;
  if (s === "AT_PICKUP") return 2;
  if (DELIVERY_LEG.has(s)) return 3;
  if (s === "DRIVER_EN_ROUTE") return 1;
  return 0;
}

export function isInPickupPhase(
  job: Pick<DriverJobDetail, "state" | "pickup_completed" | "current_leg">
): boolean {
  return job.current_leg === "pickup" || getJobLeg(job.state) === "pickup";
}

export function isInDeliveryPhase(
  job: Pick<DriverJobDetail, "state" | "pickup_completed" | "current_leg">
): boolean {
  if (job.pickup_completed || getJobLeg(job.state) === "delivery") return true;
  return job.current_leg === "delivery";
}

export function isJobCompleted(
  job: Pick<DriverJobDetail, "state" | "current_leg" | "delivery_completed">
): boolean {
  return (
    job.current_leg === "completed" || job.delivery_completed || DONE.has(job.state.toUpperCase())
  );
}

export function groupJobsByDay(
  jobs: DriverJobSummary[]
): { key: string; label: string; jobs: DriverJobSummary[] }[] {
  const groups: { key: string; label: string; jobs: DriverJobSummary[] }[] = [];
  const index = new Map<string, number>();
  for (const job of jobs) {
    const fromRoute = (job.route_id || "").replace(/^route-/, "");
    const key = /^\d{4}-\d{2}-\d{2}$/.test(fromRoute)
      ? fromRoute
      : (job.scheduled_at || "").slice(0, 10) || "unknown";
    let i = index.get(key);
    if (i === undefined) {
      i = groups.length;
      index.set(key, i);
      const label =
        key === "unknown"
          ? "Earlier"
          : new Date(`${key}T12:00:00Z`).toLocaleDateString("en-CA", {
              weekday: "short",
              month: "short",
              day: "numeric",
            });
      groups.push({ key, label, jobs: [] });
    }
    const group = groups[i];
    if (!group) continue;
    group.jobs.push(job);
  }
  return groups;
}

export function parcelScanLabel(
  job: Pick<DriverJobSummary, "scan_pickup" | "scan_delivery">
): string | null {
  const pickup = job.scan_pickup;
  const delivery = job.scan_delivery;
  const required = Math.max(pickup?.required ?? 0, delivery?.required ?? 0);
  if (required <= 0) return null;
  return `Parcels pickup ${pickup?.scanned ?? 0}/${pickup?.required ?? 0} · delivery ${delivery?.scanned ?? 0}/${delivery?.required ?? 0}`;
}

export const STOP_EXCEPTION_TYPES = [
  {
    id: "customer_not_available",
    label: "Not home / no answer",
    retryable: true,
    photoRequired: false,
  },
  { id: "closed", label: "Business closed", retryable: true, photoRequired: false },
  {
    id: "no_access",
    label: "No access (condo / dock / buzzer)",
    retryable: true,
    photoRequired: false,
  },
  { id: "weather_ice", label: "Weather / ice", retryable: true, photoRequired: false },
  { id: "refused", label: "Receiver refused", retryable: false, photoRequired: true },
  { id: "damaged_parcel", label: "Parcel damaged", retryable: false, photoRequired: true },
  { id: "unsafe", label: "Unsafe stop", retryable: false, photoRequired: true },
  { id: "unable_to_deliver", label: "Unable to deliver", retryable: false, photoRequired: false },
] as const;

export function formatAccessLine(bits: {
  special_instructions?: string | null;
  access_unit?: string | null;
  access_buzzer?: string | null;
  access_dock?: string | null;
  call_on_arrival?: boolean | null;
  contact_phone_masked?: string | null;
}): string | null {
  const parts: string[] = [];
  if (bits.access_unit) parts.push(`Unit ${bits.access_unit}`);
  if (bits.access_buzzer) parts.push(`Buzzer ${bits.access_buzzer}`);
  if (bits.access_dock) parts.push(`Dock ${bits.access_dock}`);
  if (bits.call_on_arrival) parts.push("Call on arrival");
  if (bits.contact_phone_masked) parts.push(bits.contact_phone_masked);
  if (bits.special_instructions) parts.push(bits.special_instructions);
  return parts.length ? parts.join(" · ") : null;
}
