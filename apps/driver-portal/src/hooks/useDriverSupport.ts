"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { driverApi } from "@/lib/api";
import type { DriverSupportSnapshot } from "@/lib/support";

const POLL_MS = 20_000;

export function useDriverSupport() {
  const [data, setData] = useState<DriverSupportSnapshot | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [actionPending, setActionPending] = useState<string | null>(null);
  const mounted = useRef(true);

  const refresh = useCallback(async (silent = false) => {
    if (!silent) setRefreshing(true);
    try {
      const snap = await driverApi.supportHub();
      if (mounted.current) {
        setData(snap);
        setError("");
      }
    } catch (e) {
      if (mounted.current) setError(e instanceof Error ? e.message : "support_refresh_failed");
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

  const run = useCallback(
    async (id: string, fn: () => Promise<unknown>) => {
      setActionPending(id);
      try {
        await fn();
        await refresh(true);
      } finally {
        if (mounted.current) setActionPending(null);
      }
    },
    [refresh]
  );

  return {
    data,
    error,
    loading,
    refreshing,
    actionPending,
    refresh: () => refresh(true),
    createTicket: (body: {
      subject: string;
      description?: string;
      order_id?: string;
      priority?: string;
    }) => run("ticket", () => driverApi.createSupportTicket(body)),
    reportIncident: (body: {
      incident_type: string;
      description: string;
      order_id?: string;
      location?: { lat: number; lng: number };
    }) => run("incident", () => driverApi.reportIncident(body)),
    openClaim: (body: { order_id: string; claim_type: string; description?: string }) =>
      run("claim", () => driverApi.openClaim(body)),
    updateEmergencyContact: (body: { name: string; phone: string; relationship?: string }) =>
      run("contact", () => driverApi.updateEmergencyContact(body)),
    triggerSos: (location?: { lat: number; lng: number }) =>
      run("sos", () => driverApi.emergency(location)),
  };
}
