export type JobBucket = "current" | "upcoming" | "completed";

export type JobUrgency = "critical" | "high" | "medium" | "normal";

export type JobLeg = "pickup" | "delivery" | "completed";

export type JobActionKey =
  | "arrive_pickup"
  | "confirm_pickup"
  | "arrive_delivery"
  | "confirm_delivery";

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
  status?: string | null;
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
  optimized_stops: Array<Record<string, unknown>>;
  metrics: DriverRouteMetrics & Record<string, unknown>;
  warnings: string[];
  order_ids: string[];
  jobs: DriverJobsList;
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
  packages: Array<Record<string, unknown>>;
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
  otp_required: boolean;
  incidents: Array<{
    id: string;
    incident_type: string;
    description: string;
    status: string;
    created_at: string;
  }>;
  amount_cents: number;
  currency: string;
  updated_at: string | null;
  route_id: string | null;
}

const PICKUP_LEG = new Set([
  "DRIVER_ASSIGNED",
  "DRIVER_ACCEPTED",
  "DRIVER_EN_ROUTE",
  "AT_PICKUP",
]);
const DELIVERY_LEG = new Set(["PICKED_UP", "IN_TRANSIT", "AT_DESTINATION"]);
const DONE = new Set(["DELIVERED", "POD_COMPLETED", "INVOICED", "CLOSED"]);

export const JOB_STEPS = [
  { key: "assigned", label: "Assigned", states: ["DRIVER_ASSIGNED", "DRIVER_ACCEPTED"] },
  { key: "en_route", label: "En Route", states: ["DRIVER_EN_ROUTE", "IN_TRANSIT"] },
  { key: "at_stop", label: "At Stop", states: ["AT_PICKUP", "AT_DESTINATION"] },
  { key: "picked_up", label: "Picked Up", states: ["PICKED_UP"] },
  { key: "delivered", label: "Delivered", states: ["DELIVERED", "POD_COMPLETED", "INVOICED", "CLOSED"] },
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
    stop_not_found: "Stop not found or not assigned to you.",
  };
  return map[code] ?? code.replace(/_/g, " ");
}

export function jobStatusLabel(state: string): string {
  return state.replace(/_/g, " ").toLowerCase().replace(/\b\w/g, (c) => c.toUpperCase());
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

export function isInPickupPhase(job: Pick<DriverJobDetail, "state" | "pickup_completed" | "current_leg">): boolean {
  return job.current_leg === "pickup" || getJobLeg(job.state) === "pickup";
}

export function isInDeliveryPhase(job: Pick<DriverJobDetail, "state" | "pickup_completed" | "current_leg">): boolean {
  if (job.pickup_completed || getJobLeg(job.state) === "delivery") return true;
  return job.current_leg === "delivery";
}

export function isJobCompleted(job: Pick<DriverJobDetail, "state" | "current_leg" | "delivery_completed">): boolean {
  return job.current_leg === "completed" || job.delivery_completed || DONE.has(job.state.toUpperCase());
}
