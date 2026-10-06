import { auth } from "@clerk/nextjs/server";
import { cookies } from "next/headers";
import { clerkDevBypassEnabled } from "@porterchain/auth/devBypass";
import { PC_IMP_COOKIE, PC_IMP_FLAG } from "@porterchain/auth/impersonation";
import { DRIVER_DEV_COOKIE } from "@/lib/driver-dev-cookie";
import type { DriverDashboard, DriverIncident, DriverProfile, DriverVehicle } from "@/lib/api";
import type { DriverJobSummary, DriverJobsList } from "@/lib/jobs";
import type { DriverShiftSnapshot } from "@/lib/shift";
import type { DriverRoute } from "@/lib/workspace";
import {
  countOpenClaims,
  countUnreadNotifications,
  formatWorkingHours,
  shiftStatusLabel,
  splitQueues,
} from "@/lib/workspace";

function apiBase(): string {
  return (process.env.NEXT_PUBLIC_PORTERCHAIN_API_URL ?? "http://localhost:8001").replace(
    /\/$/,
    ""
  );
}

function devLoginEnabled(): boolean {
  if (process.env.NEXT_PUBLIC_DRIVER_DEV_LOGIN === "false") return false;
  if (process.env.NEXT_PUBLIC_DRIVER_DEV_LOGIN === "true") return true;
  const appEnv = (process.env.NEXT_PUBLIC_APP_ENV ?? process.env.NODE_ENV ?? "").trim();
  return appEnv === "local" || appEnv === "development";
}

async function driverHeaders(): Promise<Record<string, string> | null> {
  const jar = await cookies();
  if (jar.get(PC_IMP_FLAG)?.value === "1") {
    const imp = jar.get(PC_IMP_COOKIE)?.value?.trim();
    if (imp?.startsWith("pc_imp_")) return { Authorization: `Bearer ${imp}` };
    return null;
  }
  if (clerkDevBypassEnabled()) return { Authorization: "Bearer dev" };
  const { getToken, userId } = await auth();
  if (userId) {
    const token = await getToken();
    if (!token) return null;
    return { Authorization: `Bearer ${token}` };
  }
  if (devLoginEnabled()) {
    const driverId = jar.get(DRIVER_DEV_COOKIE)?.value?.trim();
    if (driverId) return { "X-Driver-Id": driverId };
  }
  return null;
}

async function driverGet<T>(path: string, headers: Record<string, string>): Promise<T> {
  const res = await fetch(`${apiBase()}/driver-api${path}`, {
    headers: { ...headers, Accept: "application/json" },
    cache: "no-store",
  });
  if (!res.ok) throw new Error(String(res.status));
  return (await res.json()) as T;
}

async function safe<T>(run: () => Promise<T>, fallback: T): Promise<T> {
  try {
    return await run();
  } catch {
    return fallback;
  }
}

/** Same shape as the driver dashboard query, without a client clock. */
export async function loadDriverWorkspace(): Promise<Record<string, unknown> | null> {
  const headers = await driverHeaders();
  if (!headers) return null;

  const emptyDashboard: DriverDashboard = {
    todays_earnings_cents: 0,
    todays_stops_total: 0,
    todays_stops_completed: 0,
    wallet_balance_cents: 0,
    is_online: false,
    availability: "offline",
    rating: null,
    active_route_id: null,
    bonuses_available: 0,
    performance_score: 0,
    pending_documents: 0,
  };
  const emptyPerformance = {
    deliveries_today: 0,
    on_time_percent: 0,
    acceptance_rate: 0,
    completion_rate: 0,
    rating: 0,
  };
  const emptyRatings = { rating: 0, total_reviews: 0, five_star_percent: 0 };

  const [
    profile,
    dashboard,
    performance,
    ratings,
    route,
    vehicleRes,
    incidentsRes,
    supportRes,
    shift,
    jobsRes,
  ] = await Promise.all([
    safe(() => driverGet<DriverProfile | null>("/v1/me", headers), null),
    safe(() => driverGet<DriverDashboard>("/v1/dashboard", headers), emptyDashboard),
    safe(() => driverGet<typeof emptyPerformance>("/v1/performance", headers), emptyPerformance),
    safe(() => driverGet<typeof emptyRatings>("/v1/ratings", headers), emptyRatings),
    safe(() => driverGet<DriverRoute | null>("/v1/routes/assigned", headers), null),
    safe(() => driverGet<{ vehicle: DriverVehicle | null }>("/v1/vehicle", headers), {
      vehicle: null,
    }),
    safe(() => driverGet<{ incidents: DriverIncident[] }>("/v1/incidents", headers), {
      incidents: [],
    }),
    safe(() => driverGet<{ tickets: Array<{ status: string }> }>("/v1/support", headers), {
      tickets: [],
    }),
    safe(() => driverGet<DriverShiftSnapshot | null>("/v1/shift", headers), null),
    safe(() => driverGet<DriverJobsList | null>("/v1/jobs", headers), null),
  ]);

  const stops = route?.stops ?? [];
  const queues = splitQueues(stops);
  const openTickets = supportRes.tickets.filter((ticket) => ticket.status === "open");
  const perfRecord = performance as typeof emptyPerformance & {
    distance_km_today?: number;
    fuel_estimate_cents?: number;
  };

  return {
    profile,
    dashboard,
    performance,
    ratings,
    route,
    vehicle: vehicleRes.vehicle,
    shift,
    incidents: incidentsRes.incidents,
    openTickets,
    nextStop: jobsRes?.next_stop ?? null,
    queues,
    shiftActive: Boolean(shift?.shift_active),
    shiftStatus: shiftStatusLabel({
      isOnline: dashboard.is_online,
      routeStatus: route?.status ?? null,
      availability: shift?.availability ?? dashboard.availability,
      shiftActive: shift?.shift_active,
    }),
    workingHours: shift?.working_hours_label ?? formatWorkingHours(route?.started_at ?? null),
    mileageKm: shift ? `${shift.mileage_km.toFixed(1)} km` : "—",
    unreadNotifications: countUnreadNotifications({
      pendingDocuments: dashboard.pending_documents,
      bonusesAvailable: dashboard.bonuses_available,
      openTickets: openTickets.length,
    }),
    openClaims: countOpenClaims(incidentsRes.incidents),
    distanceKm:
      perfRecord.distance_km_today != null
        ? `${Number(perfRecord.distance_km_today).toFixed(1)} km`
        : "—",
    fuelEstimate:
      perfRecord.fuel_estimate_cents != null
        ? new Intl.NumberFormat("en-CA", { style: "currency", currency: "CAD" }).format(
            perfRecord.fuel_estimate_cents / 100
          )
        : "—",
    lastUpdated: new Date().toISOString(),
  };
}

export async function driverServerGet<T>(path: string): Promise<T | null> {
  const headers = await driverHeaders();
  if (!headers) return null;
  try {
    return await driverGet<T>(path, headers);
  } catch {
    return null;
  }
}

export async function loadDriverJobs() {
  const headers = await driverHeaders();
  if (!headers) return null;
  try {
    const jobs = await driverGet<DriverJobsList>("/v1/jobs", headers);
    return { jobs, at: new Date().toISOString() };
  } catch {
    return null;
  }
}

export async function loadDriverJobsHistory() {
  const headers = await driverHeaders();
  if (!headers) return null;
  try {
    const payload = await driverGet<{ history: DriverJobSummary[] }>("/v1/jobs/history", headers);
    return payload.history ?? [];
  } catch {
    return null;
  }
}
