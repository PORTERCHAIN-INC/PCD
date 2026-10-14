/**
 * One round-trip snapshot of the driver's world: who, on duty or not, today's jobs, and the
 * current stop. Everything on screen reads from this; stop logic derives from it (stop/stopFlow).
 */
import {
  fetchDashboard,
  fetchJob,
  fetchJobs,
  fetchMe,
  fetchNavigationSession,
  probeApi,
} from "./api";
import { formatAccessLine, formatKm } from "./format";
import { idleLocation } from "./location";
import { collectPush } from "./push";
import type { DriverJobSummary, Handshake, LocationState, PushState } from "./types";

const PUSH_IDLE: PushState = {
  kind: "unavailable",
  permission: "idle",
  tokenPreview: null,
  registered: false,
  detail: "Not checked",
};

function coord(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

export const idleHandshake = (): Handshake => ({
  api: "idle",
  auth: "idle",
  driverName: null,
  online: null,
  stopsDone: null,
  stopsTotal: null,
  jobs: [],
  routeId: null,
  stopId: null,
  stopStatus: null,
  nextStop: null,
  nextStopType: null,
  etaMinutes: null,
  currentOrderId: null,
  currentOrderNumber: null,
  currentOrderState: null,
  accessNotes: null,
  parcelLines: [],
  deliveryAttempts: null,
  maxDeliveryAttempts: null,
  navigationUrl: null,
  destLat: null,
  destLng: null,
  etaLabel: null,
  distanceLabel: null,
  otpRequired: false,
  podRequirements: null,
  scanPickup: null,
  scanDelivery: null,
  codAmountCents: null,
  codStatus: null,
  push: PUSH_IDLE,
  location: idleLocation(),
  error: null,
});

export function isOnboardingBlocked(message: string | null | undefined): boolean {
  return Boolean(message?.startsWith("driver_onboarding_blocked:"));
}

export async function runHandshake(location: LocationState = idleLocation()): Promise<Handshake> {
  const next = idleHandshake();
  next.location = location;
  if (!(await probeApi())) {
    next.api = "down";
    // Local dev: the PorterChain API must be running on :8001 (see config.ts).
    next.error = "network_unavailable";
    next.push = await collectPush().catch(() => PUSH_IDLE);
    return next;
  }
  next.api = "up";

  try {
    const [me, push] = await Promise.all([fetchMe(), collectPush().catch(() => PUSH_IDLE)]);
    next.auth = "up";
    next.driverName = me.full_name;
    next.online = me.is_online;
    next.push = push;

    const [dash, jobs] = await Promise.all([
      fetchDashboard().catch((err: unknown) => {
        next.error = err instanceof Error ? err.message : "dashboard_failed";
        return null;
      }),
      fetchJobs().catch(() => null),
    ]);
    if (dash) {
      next.online = dash.is_online;
      next.stopsDone = dash.todays_stops_completed;
      next.stopsTotal = dash.todays_stops_total;
    }
    if (!jobs) return next;

    const stop = jobs.next_stop ?? null;
    const listed = [jobs.current, ...(jobs.upcoming ?? []), ...(jobs.jobs ?? [])].filter(
      (j): j is DriverJobSummary => Boolean(j)
    );
    next.jobs = listed.filter((j, i) => listed.findIndex((x) => x.order_id === j.order_id) === i);
    next.routeId = jobs.route_id ?? dash?.active_route_id ?? null;
    next.stopId = stop?.stop_id ?? null;
    next.stopStatus = stop?.status ?? null;
    next.nextStop = stop?.formatted_address ?? null;
    next.nextStopType = stop?.stop_type ?? null;
    next.etaMinutes = stop?.eta_minutes ?? null;
    next.deliveryAttempts = stop?.delivery_attempts ?? null;
    next.maxDeliveryAttempts = stop?.max_delivery_attempts ?? null;
    next.accessNotes = stop ? formatAccessLine(stop) : null;
    next.currentOrderId = jobs.current?.order_id ?? stop?.order_id ?? null;
    next.currentOrderNumber = jobs.current?.order_number ?? null;
    const row = next.jobs.find((j) => j.order_id === next.currentOrderId);
    next.currentOrderState = row?.state ?? row?.status ?? null;
    next.destLat = coord(stop?.address?.lat);
    next.destLng = coord(stop?.address?.lng);

    if (next.currentOrderId) {
      const [job, nav] = await Promise.all([
        fetchJob(next.currentOrderId).catch(() => null),
        fetchNavigationSession(next.currentOrderId).catch(() => null),
      ]);
      if (job) {
        next.otpRequired = Boolean(job.otp_required);
        next.podRequirements = job.pod_requirements ?? null;
        next.scanPickup = job.scan_pickup ?? null;
        next.scanDelivery = job.scan_delivery ?? null;
        next.codAmountCents = job.cod_amount_cents ?? null;
        next.codStatus = job.cod_status ?? null;
        next.currentOrderNumber ??= job.order_number;
        next.currentOrderState = job.state ?? job.status ?? next.currentOrderState;
        if (!next.accessNotes && job.special_instructions) {
          next.accessNotes = job.special_instructions;
        }
        next.parcelLines = (job.packages ?? []).map((pkg) => {
          const name = pkg.preset_label || "Parcel";
          return pkg.instructions ? `${name}: ${pkg.instructions}` : name;
        });
        next.deliveryAttempts = job.delivery_attempts ?? next.deliveryAttempts;
        next.maxDeliveryAttempts = job.max_delivery_attempts ?? next.maxDeliveryAttempts;
      }
      if (nav && !nav.idle) {
        const dest = next.nextStopType === "pickup" ? nav.pickup : (nav.dropoff ?? nav.pickup);
        next.navigationUrl = nav.navigation_url ?? null;
        next.destLat = coord(dest?.lat) ?? next.destLat;
        next.destLng = coord(dest?.lng) ?? next.destLng;
        next.etaLabel = nav.eta?.eta_label ?? null;
        next.distanceLabel = formatKm(nav.eta?.distance_meters ?? null);
      }
    }
  } catch (err) {
    next.auth = "down";
    next.error = err instanceof Error ? err.message : "handshake_failed";
  }
  return next;
}
