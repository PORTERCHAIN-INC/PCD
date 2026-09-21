"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { driverApi } from "@/lib/api";
import type {
  DriverDashboard,
  DriverIncident,
  DriverPerformance,
  DriverProfile,
  DriverRatings,
  DriverRoute,
  DriverVehicle,
  SupportTicket,
} from "@/lib/api";
import type { DriverNextStop } from "@/lib/jobs";
import type { DriverShiftSnapshot } from "@/lib/shift";
import {
  countOpenClaims,
  countUnreadNotifications,
  formatWorkingHours,
  shiftStatusLabel,
  splitQueues,
} from "@/lib/workspace";

const POLL_MS = 15_000;

export interface WorkspaceData {
  profile: DriverProfile | null;
  dashboard: DriverDashboard;
  performance: DriverPerformance;
  ratings: DriverRatings;
  route: DriverRoute | null;
  vehicle: DriverVehicle | null;
  shift: DriverShiftSnapshot | null;
  incidents: DriverIncident[];
  openTickets: SupportTicket[];
  nextStop: DriverNextStop | null;
  lastUpdated: Date;
  queues: ReturnType<typeof splitQueues>;
  shiftStatus: string;
  shiftActive: boolean;
  workingHours: string;
  mileageKm: string;
  unreadNotifications: number;
  openClaims: number;
  distanceKm: string;
  fuelEstimate: string;
}

async function fetchWorkspace(): Promise<Omit<WorkspaceData, "lastUpdated">> {
  const safe = async <T>(fn: () => Promise<T>, fallback: T): Promise<T> => {
    try {
      return await fn();
    } catch {
      return fallback;
    }
  };

  const emptyPerformance: DriverPerformance = {
    score: 0,
    on_time_percent: 0,
    completion_percent: 0,
    deliveries_total: 0,
    deliveries_today: 0,
    acceptance_rate: 0,
    rating: null,
  };
  const emptyRatings: DriverRatings = {
    rating: 0,
    total_reviews: 0,
    five_star_percent: 0,
  };

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
    safe(() => driverApi.me(), null),
    safe(() => driverApi.dashboard(), emptyDashboard),
    safe(() => driverApi.performance(), emptyPerformance),
    safe(() => driverApi.ratings(), emptyRatings),
    safe(() => driverApi.route(), null),
    safe(() => driverApi.vehicle(), { vehicle: null, vehicles: [] }),
    safe(() => driverApi.incidents(), { incidents: [] }),
    safe(() => driverApi.support(), { tickets: [] }),
    safe(() => driverApi.shift(), null),
    safe(() => driverApi.jobs(), null),
  ]);

  const stops = route?.stops ?? [];
  const queues = splitQueues(stops);
  const openTickets = (supportRes.tickets as SupportTicket[]).filter((t) => t.status === "open");

  const perfRecord = performance as DriverPerformance & {
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
  };
}

export function useDriverWorkspace() {
  const [data, setData] = useState<WorkspaceData | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [actionPending, setActionPending] = useState<string | null>(null);
  const mounted = useRef(true);

  const refresh = useCallback(async (silent = false) => {
    if (!silent) setRefreshing(true);
    try {
      const next = await fetchWorkspace();
      if (mounted.current) {
        setData({ ...next, lastUpdated: new Date() });
        setError("");
      }
    } catch (e) {
      if (mounted.current) setError(e instanceof Error ? e.message : "refresh_failed");
    } finally {
      if (mounted.current) {
        setLoading(false);
        setRefreshing(false);
      }
    }
  }, []);

  useEffect(() => {
    mounted.current = true;
    refresh();
    const interval = window.setInterval(() => {
      if (document.visibilityState === "visible") refresh(true);
    }, POLL_MS);
    return () => {
      mounted.current = false;
      window.clearInterval(interval);
    };
  }, [refresh]);

  const setOnline = useCallback(
    async (online: boolean) => {
      setActionPending(online ? "online" : "offline");
      try {
        await driverApi.setOnline(online);
        await refresh(true);
        if (mounted.current) setError("");
      } catch (e) {
        if (mounted.current) setError(e instanceof Error ? e.message : "availability_failed");
      } finally {
        if (mounted.current) setActionPending(null);
      }
    },
    [refresh]
  );

  const startShift = useCallback(
    async (pretrip?: Record<string, boolean>) => {
      const routeId = data?.route?.route_id ?? data?.dashboard.active_route_id ?? undefined;
      setActionPending("start");
      try {
        await driverApi.shiftStart(routeId, pretrip);
        await refresh(true);
        if (mounted.current) setError("");
      } catch (e) {
        if (mounted.current) setError(e instanceof Error ? e.message : "start_shift_failed");
      } finally {
        if (mounted.current) setActionPending(null);
      }
    },
    [data, refresh]
  );

  const endShift = useCallback(async () => {
    setActionPending("end");
    try {
      await driverApi.shiftEnd();
      await refresh(true);
      if (mounted.current) setError("");
    } catch (e) {
      if (mounted.current) setError(e instanceof Error ? e.message : "end_shift_failed");
    } finally {
      if (mounted.current) setActionPending(null);
    }
  }, [refresh]);

  const triggerEmergency = useCallback(async () => {
    setActionPending("emergency");
    try {
      const location = await new Promise<{ lat: number; lng: number } | undefined>((resolve) => {
        if (!navigator.geolocation) return resolve(undefined);
        navigator.geolocation.getCurrentPosition(
          (pos) => resolve({ lat: pos.coords.latitude, lng: pos.coords.longitude }),
          () => resolve(undefined),
          { timeout: 8000 }
        );
      });
      await driverApi.emergency(location);
      if (mounted.current) setError("");
    } catch (e) {
      if (mounted.current) setError(e instanceof Error ? e.message : "emergency_failed");
    } finally {
      if (mounted.current) setActionPending(null);
    }
  }, []);

  return {
    data,
    error,
    loading,
    refreshing,
    actionPending,
    refresh: () => refresh(true),
    setOnline,
    startShift,
    endShift,
    triggerEmergency,
  };
}
