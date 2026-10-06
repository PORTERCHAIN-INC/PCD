"use client";

import { useCallback, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { driverApi } from "@/lib/api";

export function useDriverSupport() {
  const qc = useQueryClient();
  const [actionPending, setActionPending] = useState<string | null>(null);
  const supportQuery = useQuery({
    queryKey: ["driver-support-hub"],
    queryFn: () => driverApi.supportHub(),
  });
  const refresh = useCallback(async () => {
    await qc.invalidateQueries({ queryKey: ["driver-support-hub"] });
  }, [qc]);
  const data = supportQuery.data ?? null;
  const error =
    supportQuery.error instanceof Error
      ? supportQuery.error.message
      : supportQuery.error
        ? "support_refresh_failed"
        : "";
  const loading = supportQuery.isLoading && !data;
  const refreshing = supportQuery.isFetching && Boolean(data);

  const run = useCallback(
    async (id: string, fn: () => Promise<unknown>) => {
      setActionPending(id);
      try {
        await fn();
        await refresh();
      } finally {
        setActionPending(null);
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
    refresh,
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
