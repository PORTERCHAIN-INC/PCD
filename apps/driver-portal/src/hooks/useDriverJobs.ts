"use client";

import { useCallback, useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { driverApi } from "@/lib/api";
import type { DriverJobsList, DriverJobsOptimizeResult } from "@/lib/jobs";
import { formatLastUpdated } from "@/lib/workspace";
import { optimizeEngineNote } from "@/lib/telemetryLabels";

const OPTIMIZE_POLL_MS = 1_000;
const OPTIMIZE_POLL_MAX = 45;

function formatDeltaMessage(result: DriverJobsOptimizeResult, applied: boolean): string {
  if (result.status === "error") {
    return result.message || "Could not update stop order";
  }
  const engineRaw = typeof result.metrics.engine === "string" ? result.metrics.engine : null;
  if (engineRaw === "haversine") {
    return "Stop order not updated — routing engine unavailable.";
  }
  const engine = optimizeEngineNote(engineRaw);
  const parts: string[] = [
    applied
      ? engine
        ? `Stop order applied (${engine})`
        : "Stop order applied"
      : engine
        ? `Preview ready (${engine})`
        : "Preview ready",
  ];
  const fuelDelta = result.metrics.fuel_delta_cents;
  const kmDelta = result.metrics.distance_delta_km;
  if (typeof fuelDelta === "number" && fuelDelta !== 0) {
    const dollars = (Math.abs(fuelDelta) / 100).toFixed(2);
    parts.push(fuelDelta > 0 ? `saves ~$${dollars} fuel` : `~$${dollars} more fuel estimate`);
  }
  if (typeof kmDelta === "number" && kmDelta !== 0) {
    parts.push(kmDelta > 0 ? `${kmDelta} km shorter` : `${Math.abs(kmDelta)} km longer`);
  } else if (
    typeof result.metrics.estimated_fuel_cents === "number" &&
    typeof fuelDelta !== "number"
  ) {
    parts.push(`est. fuel $${(result.metrics.estimated_fuel_cents / 100).toFixed(2)}`);
  }
  if (typeof result.metrics.after_distance_km === "number") {
    parts.push(`${result.metrics.after_distance_km} km proposed`);
  }
  return parts.join(" · ");
}

export function useDriverJobs() {
  const qc = useQueryClient();
  const mounted = useRef(true);
  const [optimizing, setOptimizing] = useState(false);
  const [optimizeMessage, setOptimizeMessage] = useState("");
  const [preview, setPreview] = useState<DriverJobsOptimizeResult | null>(null);
  const [canUndo, setCanUndo] = useState(false);
  const [actionError, setActionError] = useState("");

  const jobsQuery = useQuery({
    queryKey: ["driver-jobs"],
    queryFn: async () => {
      const jobs = await driverApi.jobs();
      return { jobs, at: new Date() };
    },
    refetchInterval: false,
  });

  const historyQuery = useQuery({
    queryKey: ["driver-jobs-history"],
    staleTime: 60_000,
    queryFn: async () => {
      const hist = await driverApi.jobsHistory();
      return hist.history;
    },
    refetchInterval: false,
  });

  const refresh = useCallback(async () => {
    await Promise.all([
      qc.invalidateQueries({ queryKey: ["driver-jobs"] }),
      qc.invalidateQueries({ queryKey: ["driver-jobs-history"] }),
    ]);
  }, [qc]);

  const setJobsData = useCallback(
    (jobs: DriverJobsList) => {
      qc.setQueryData(["driver-jobs"], { jobs, at: new Date() });
    },
    [qc]
  );

  const optimize = useCallback(async () => {
    mounted.current = true;
    setOptimizing(true);
    setOptimizeMessage("Building stop order preview…");
    setPreview(null);
    setActionError("");
    try {
      let result = await driverApi.optimizeJobs();
      const runId = result.run_id;
      if (result.status === "pending" && runId) {
        for (let i = 0; i < OPTIMIZE_POLL_MAX; i += 1) {
          await new Promise((r) => setTimeout(r, OPTIMIZE_POLL_MS));
          if (!mounted.current) return;
          result = await driverApi.optimizeRunStatus(runId);
          if (result.status !== "pending") break;
        }
      }
      if (!mounted.current) return;
      if (result.status === "pending") {
        setOptimizeMessage("Still building preview… refresh shortly.");
        return;
      }
      if (result.status === "error") {
        setOptimizeMessage(result.message || "Preview failed");
        setPreview(null);
        return;
      }
      setPreview(result);
      setOptimizeMessage(formatDeltaMessage(result, false));
    } catch (e) {
      const msg = e instanceof Error ? e.message : "optimize_failed";
      setActionError(
        msg.includes("sequence_version_conflict") || msg.includes("Sequence conflict")
          ? "Stop order conflict — refresh and try again."
          : msg
      );
      setOptimizeMessage("");
      setPreview(null);
    } finally {
      setOptimizing(false);
    }
  }, []);

  const acceptPreview = useCallback(async () => {
    if (!preview?.run_id) return;
    setOptimizing(true);
    setActionError("");
    try {
      const result = await driverApi.optimizeAccept(preview.run_id, preview.sequence_version);
      setJobsData(result.jobs);
      setPreview(null);
      setCanUndo(true);
      setOptimizeMessage(formatDeltaMessage(result, true));
      try {
        window.dispatchEvent(new CustomEvent("pc:sequence-applied"));
      } catch {
        /* SSR */
      }
    } catch (e) {
      const msg = e instanceof Error ? e.message : "accept_failed";
      setActionError(
        msg.includes("sequence_version_conflict") || msg.includes("Sequence conflict")
          ? "Stop order conflict — refresh and request a new preview."
          : msg
      );
    } finally {
      setOptimizing(false);
    }
  }, [preview, setJobsData]);

  const discardPreview = useCallback(() => {
    setPreview(null);
    setOptimizeMessage("Kept current stop order.");
  }, []);

  const undoOptimize = useCallback(async () => {
    setOptimizing(true);
    setActionError("");
    try {
      const result = await driverApi.optimizeUndo();
      if (result.error === "nothing_to_undo" || result.ok === false) {
        setOptimizeMessage(result.message || "Nothing to undo");
        setCanUndo(false);
        return;
      }
      setJobsData(result.jobs);
      setCanUndo(false);
      setPreview(null);
      setOptimizeMessage(result.message || "Previous stop order restored.");
      try {
        window.dispatchEvent(new CustomEvent("pc:sequence-applied"));
      } catch {
        /* SSR */
      }
    } catch (e) {
      setActionError(e instanceof Error ? e.message : "undo_failed");
    } finally {
      setOptimizing(false);
    }
  }, [setJobsData]);

  const lastUpdated = jobsQuery.data?.at ?? null;
  const jobsError =
    actionError ||
    (jobsQuery.error instanceof Error
      ? jobsQuery.error.message
      : jobsQuery.error
        ? String(jobsQuery.error)
        : "");
  const historyError =
    historyQuery.error instanceof Error
      ? historyQuery.error.message
      : historyQuery.error
        ? String(historyQuery.error)
        : "";

  return {
    data: jobsQuery.data?.jobs ?? null,
    history: historyQuery.data ?? [],
    error: jobsError,
    historyError,
    loading: jobsQuery.isLoading,
    optimizing,
    optimizeMessage,
    preview,
    canUndo,
    lastUpdated,
    lastUpdatedLabel: lastUpdated ? formatLastUpdated(lastUpdated) : null,
    refresh,
    optimize,
    acceptPreview,
    discardPreview,
    undoOptimize,
  };
}
