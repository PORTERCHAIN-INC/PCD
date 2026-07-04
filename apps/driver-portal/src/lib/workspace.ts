import { differenceInMinutes, format } from "date-fns";

export interface DriverStop {
  stop_id: string;
  order_id: string;
  sequence: number;
  stop_type: string;
  status: string;
  address: { formatted?: string; line1?: string; city?: string; [key: string]: unknown };
  scheduled_at: string | null;
  tracking_number: string;
  order_number: string;
  special_instructions?: string | null;
}

export interface DriverRoute {
  route_id: string;
  driver_id: string;
  status: string;
  stops: DriverStop[];
  route_polyline?: string | null;
  earnings_cents: number;
  started_at: string | null;
}

const COMPLETED_STATUSES = new Set(["delivered", "completed", "pod_completed", "picked_up"]);

const DELIVERY_DONE_STATUSES = new Set(["delivered", "completed", "pod_completed"]);

export function isStopCompleted(status: string): boolean {
  return COMPLETED_STATUSES.has(status.toLowerCase());
}

export function isDeliveryCompleted(status: string): boolean {
  return DELIVERY_DONE_STATUSES.has(status.toLowerCase());
}

export function formatStopAddress(stop: DriverStop): string {
  const addr = stop.address;
  return addr.formatted || [addr.line1, addr.city].filter(Boolean).join(", ") || "Address pending";
}

export function splitQueues(stops: DriverStop[]) {
  const sorted = [...stops].sort((a, b) => a.sequence - b.sequence);
  const pickupQueue = sorted.filter(
    (s) => s.stop_type === "pickup" && !isStopCompleted(s.status) && s.status !== "locked"
  );
  const deliveryQueue = sorted.filter(
    (s) => s.stop_type === "dropoff" && s.status !== "locked" && !isDeliveryCompleted(s.status)
  );
  const nextStop =
    sorted.find((s) => {
      if (s.status === "locked") return false;
      return s.stop_type === "dropoff"
        ? !isDeliveryCompleted(s.status)
        : !isStopCompleted(s.status);
    }) ?? null;

  const completedDeliveries = sorted.filter(
    (s) => s.stop_type === "dropoff" && isDeliveryCompleted(s.status)
  ).length;

  const todaysDeliveries = sorted.filter((s) => s.stop_type === "dropoff").length;

  return { pickupQueue, deliveryQueue, nextStop, completedDeliveries, todaysDeliveries };
}

export function shiftStatusLabel(opts: {
  isOnline: boolean;
  routeStatus: string | null;
  availability: string;
  shiftActive?: boolean;
}): string {
  if (opts.shiftActive) {
    if (opts.availability === "on_break") return "On Break";
    return "On Shift";
  }
  if (opts.availability === "busy") return "Busy";
  if (opts.availability === "idle") return "Idle";
  if (opts.routeStatus === "in_progress") return "On Route";
  if (opts.isOnline || opts.availability === "available") return "Online";
  if (opts.availability === "offline") return "Off Duty";
  return "Standby";
}

export function formatWorkingHours(startedAt: string | null, now = new Date()): string {
  if (!startedAt) return "—";
  const start = new Date(startedAt);
  if (Number.isNaN(start.getTime())) return "—";
  const minutes = differenceInMinutes(now, start);
  const hours = Math.floor(minutes / 60);
  const mins = minutes % 60;
  if (hours === 0) return `${mins}m`;
  return `${hours}h ${mins}m`;
}

export function formatDistanceKm(km: number | null | undefined): string {
  if (km == null || Number.isNaN(km)) return "—";
  return `${km.toFixed(1)} km`;
}

export function formatLastUpdated(date: Date): string {
  return format(date, "h:mm:ss a");
}

export function countOpenClaims(incidents: { status: string; incident_type: string }[]): number {
  return incidents.filter(
    (i) =>
      i.status === "open" && ["damage", "loss", "claim"].includes(i.incident_type.toLowerCase())
  ).length;
}

export function countUnreadNotifications(opts: {
  pendingDocuments: number;
  bonusesAvailable: number;
  openTickets: number;
}): number {
  return opts.pendingDocuments + opts.bonusesAvailable + opts.openTickets;
}
