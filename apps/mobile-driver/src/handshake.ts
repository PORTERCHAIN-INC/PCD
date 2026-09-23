import {
  fetchDashboard,
  fetchJob,
  fetchJobs,
  fetchMe,
  fetchNavigationRoute,
  fetchNavigationSession,
  fetchPublicHealth,
  probeApi,
} from "./api";
import { collectPush } from "./push";
import { formatKm, formatAccessLine } from "./format";
import { idleLocation } from "./location";
import type { Handshake, LocationState, NavigationSession, PushState } from "./types";

const PUSH_IDLE: PushState = {
  kind: "unavailable",
  permission: "idle",
  tokenPreview: null,
  registered: false,
  detail: "Not probed",
};

function coord(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function navBits(nav: NavigationSession | null, stopType: string | null) {
  if (!nav || nav.idle) {
    return {
      navigationUrl: null as string | null,
      destLat: null as number | null,
      destLng: null as number | null,
      etaLabel: null as string | null,
      distanceLabel: null as string | null,
    };
  }
  const dest = stopType === "pickup" ? nav.pickup : (nav.dropoff ?? nav.pickup);
  return {
    navigationUrl: nav.navigation_url ?? null,
    destLat: coord(dest?.lat),
    destLng: coord(dest?.lng),
    etaLabel: nav.eta?.eta_label ?? null,
    distanceLabel: formatKm(nav.eta?.distance_meters ?? null),
  };
}

export function isOnboardingBlocked(message: string | null | undefined): boolean {
  return Boolean(message?.startsWith("driver_onboarding_blocked:"));
}

export const idleHandshake = (): Handshake => ({
  api: "idle",
  auth: "idle",
  driverName: null,
  availability: null,
  online: null,
  nextStop: null,
  nextStopType: null,
  etaMinutes: null,
  stopsDone: null,
  stopsTotal: null,
  routeId: null,
  stopId: null,
  stopStatus: null,
  currentOrderId: null,
  currentOrderNumber: null,
  accessNotes: null,
  parcelLines: [],
  bookingMode: null,
  vehicleClass: null,
  deliveryAttempts: null,
  maxDeliveryAttempts: null,
  walletCents: null,
  todayEarningsCents: null,
  pendingDocuments: null,
  performanceScore: null,
  navigationUrl: null,
  destLat: null,
  destLng: null,
  etaLabel: null,
  distanceLabel: null,
  otpRequired: false,
  scanPickup: null,
  scanDelivery: null,
  codAmountCents: null,
  codStatus: null,
  push: PUSH_IDLE,
  location: idleLocation(),
  platformStatus: "unknown",
  platformDetail: null,
  routePolyline: null,
  navStopCount: null,
  error: null,
});

export async function runHandshake(location: LocationState = idleLocation()): Promise<Handshake> {
  const next = idleHandshake();
  next.location = location;
  const apiUp = await probeApi();
  next.api = apiUp ? "up" : "down";
  if (!apiUp) {
    next.error = "API unreachable — start Porterchain API on :8001";
    next.push = await collectPush().catch(() => PUSH_IDLE);
    return next;
  }

  try {
    const health = await fetchPublicHealth().catch(() => null);
    if (health) {
      next.platformStatus = health.status === "ok" ? "ok" : "degraded";
      if (next.platformStatus === "degraded") {
        const bad = Object.entries(health.components ?? {})
          .filter(([, v]) => v !== "operational")
          .map(([k]) => k);
        next.platformDetail = bad.length
          ? `Platform degraded: ${bad.join(", ")}`
          : "Platform degraded — some services may be slow";
      }
    }

    const [me, push] = await Promise.all([fetchMe(), collectPush()]);
    next.auth = "up";
    next.driverName = me.full_name;
    next.walletCents = me.wallet_balance_cents ?? null;
    next.push = push;

    const dash = await fetchDashboard().catch((err: unknown) => {
      const message = err instanceof Error ? err.message : "dashboard_failed";
      next.error = message;
      return null;
    });
    const jobs = await fetchJobs().catch(() => ({
      next_stop: null,
      current: null,
      route_id: null,
    }));
    if (!dash) {
      return next;
    }
    next.availability = dash.availability;
    next.online = dash.is_online;
    next.stopsDone = dash.todays_stops_completed;
    next.stopsTotal = dash.todays_stops_total;
    next.walletCents = dash.wallet_balance_cents ?? me.wallet_balance_cents ?? null;
    next.todayEarningsCents = dash.todays_earnings_cents ?? null;
    next.pendingDocuments = dash.pending_documents ?? null;
    next.performanceScore = dash.performance_score ?? null;
    next.routeId = jobs.route_id ?? dash.active_route_id ?? null;
    next.stopId = jobs.next_stop?.stop_id ?? null;
    next.stopStatus = jobs.next_stop?.status ?? null;
    next.nextStop = jobs.next_stop?.formatted_address ?? null;
    next.nextStopType = jobs.next_stop?.stop_type ?? null;
    next.etaMinutes = jobs.next_stop?.eta_minutes ?? null;
    next.currentOrderId = jobs.current?.order_id ?? jobs.next_stop?.order_id ?? null;
    next.currentOrderNumber = jobs.current?.order_number ?? null;
    next.accessNotes = jobs.next_stop
      ? formatAccessLine({
          special_instructions: jobs.next_stop.special_instructions,
          access_unit: jobs.next_stop.access_unit,
          access_buzzer: jobs.next_stop.access_buzzer,
          access_dock: jobs.next_stop.access_dock,
          call_on_arrival: jobs.next_stop.call_on_arrival,
          contact_phone_masked: jobs.next_stop.contact_phone_masked,
        })
      : null;
    next.deliveryAttempts = jobs.next_stop?.delivery_attempts ?? null;
    next.maxDeliveryAttempts = jobs.next_stop?.max_delivery_attempts ?? null;
    next.push = push;

    if (next.currentOrderId) {
      try {
        const job = await fetchJob(next.currentOrderId);
        next.otpRequired = Boolean(job.otp_required);
        next.scanPickup = job.scan_pickup ?? null;
        next.scanDelivery = job.scan_delivery ?? null;
        next.codAmountCents = job.cod_amount_cents ?? null;
        next.codStatus = job.cod_status ?? null;
        if (!next.currentOrderNumber) next.currentOrderNumber = job.order_number;
        if (!next.accessNotes && job.special_instructions) {
          next.accessNotes = formatAccessLine({ special_instructions: job.special_instructions });
        }
        next.bookingMode = job.booking_mode ?? null;
        next.vehicleClass = job.vehicle_class ?? null;
        next.parcelLines = (job.packages ?? [])
          .map((pkg) => {
            const name = pkg.preset_label || "Parcel";
            return pkg.instructions ? `${name}: ${pkg.instructions}` : name;
          })
          .filter(Boolean);
        if (job.delivery_attempts != null) next.deliveryAttempts = job.delivery_attempts;
        if (job.max_delivery_attempts != null) next.maxDeliveryAttempts = job.max_delivery_attempts;
      } catch {
        /* FieldOps can still fetch */
      }
    }

    const nav = await fetchNavigationSession(next.currentOrderId).catch(() => null);
    Object.assign(next, navBits(nav, next.nextStopType));
    if (next.destLat == null) {
      next.destLat = coord(jobs.next_stop?.address?.lat);
      next.destLng = coord(jobs.next_stop?.address?.lng);
    }
    if (nav?.optimized_route?.polyline) {
      next.routePolyline = nav.optimized_route.polyline;
    }

    if (next.routeId) {
      try {
        const routeNav = await fetchNavigationRoute(next.routeId);
        next.navStopCount = routeNav.stops?.length ?? null;
        if (routeNav.route_polyline) next.routePolyline = routeNav.route_polyline;
        if (!next.etaLabel && routeNav.eta?.eta_label) next.etaLabel = routeNav.eta.eta_label;
      } catch {
        /* optional geometry */
      }
    }
  } catch (err) {
    next.auth = "down";
    next.error = err instanceof Error ? err.message : "handshake_failed";
    next.push = await collectPush().catch(() => PUSH_IDLE);
  }
  return next;
}
